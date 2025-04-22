from textual.screen import ModalScreen
from textual.widgets import Label, Button, TextArea, RichLog
from textual.containers import Vertical, Horizontal
from typing import Any, Generator, List, Optional, Tuple
import json

explainer = """ 
These steps have been generated as a task list for your prompt. 
- Press continue to proceed with generating code for each step
- Edit the steps and press "Save Edits" to manually alter the steps. Ensure that you retain the current JSON format.
- Use Re-Prompt to add additional prompt information and send it back to have new steps generated.
- Press cancel to exit the current /code command.
"""

class StepsScreen(ModalScreen):
    """Modal screen for editing steps JSON"""
    
    def __init__(self, steps: List[dict]) -> None:
        super().__init__()
        self.steps = steps
        self.future = None
        self.label_reprompt = Label("Additional Instructions", id="reprompt-label")
        self.textarea_reprompt = TextArea("", id="reprompt-input", language="text")
        self.button_continue = Button("Continue", id="continue-button")
        self.button_save = Button("Save Edits", id="save-button", variant="success")
        self.button_reprompt = Button("Re-Prompt", id="reprompt-button")
        self.button_cancel = Button("Cancel", id="cancel-button", variant="error")
        self.richlog_description = RichLog(id="steps-dialog")
        self.steps_display = TextArea(
                json.dumps(self.steps, indent=2),
                id="steps-editor",
                language="json"
            )
        self.button_layout = Horizontal(id="button-row")
    
    def compose(self) -> Generator[Any, None, None]:
        with Vertical(id="steps-dialog"):
            yield self.richlog_description
            yield self.steps_display
            
            # Additional instructions input, hidden by default
            yield self.label_reprompt
            yield self.textarea_reprompt
            
            with self.button_layout:
                yield self.button_continue
                yield self.button_save
                yield self.button_reprompt
                yield self.button_cancel
    
    def on_mount(self) -> None:
        """Setup the screen on mount"""
        #self.query_one("#steps-editor").can_focus = False
        self.label_reprompt.display = False
        self.textarea_reprompt.display = False
        self.richlog_description.write(explainer)
        self.richlog_description.wrap = True
        self.richlog_description.styles.height = "30%"
        self.steps_display.styles.height = "auto"
        self.button_layout.styles.height = 1

    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        if button_id == "continue-button":
            self._continue()
        elif button_id == "save-button":
            self._process_steps()
        elif button_id == "reprompt-button":
            # Show or submit additional instructions
            if self.textarea_reprompt.visible and self.textarea_reprompt.text.strip():
                # User has entered instructions, proceed to reprompt
                self._reprompt(self.textarea_reprompt.text)
            else:
                # Reveal the input field for additional instructions
                self.label_reprompt.display = True
                self.textarea_reprompt.display = True
                self.textarea_reprompt.focus()
                self.button_save.display = False
                self.button_continue.display = False
                self.button_reprompt.label = "Send"
                self.button_cancel.label = "Cancel Re-Prompt"
        elif button_id == "cancel-button":
            if self.label_reprompt.display:
                # in reprompt mode, this is cancelling reprompt, so return items to "normal"
                self.label_reprompt.display = False
                self.textarea_reprompt.display = False
                self.button_save.display = True
                self.button_continue.display = True
                self.button_reprompt.label = "Re-Prompt"
                self.button_cancel.label = "Cancel"
            else:
                self._cancel()
    
    def _process_steps(self) -> None:
        """Process and validate steps before returning"""
        steps_text = self.query_one("#steps-editor").text
        try:
            edited_steps = json.loads(steps_text)
            if "steps" not in edited_steps:
                raise ValueError("Failed to parse steps object")
            if not isinstance(edited_steps["steps"], list):
                raise ValueError("Steps must be a list of dictionaries")
            for step in edited_steps["steps"]:
                if "operation_type" not in step:
                    raise ValueError("Missing operation_type")
                if "filename" not in step:
                    raise ValueError("Missing filename")
                if "target_location" not in step:
                    raise ValueError("Missing target_location")
                if "description" not in step:
                    raise ValueError("Missing description")

            ret = {"choice": "edit", "steps": edited_steps}
            if self.future:
                self.future.set_result(ret)
            self.dismiss()
        except json.JSONDecodeError:
            # Could add a popup or error display in future
            self.notify("Invalid JSON format", severity="error")
        except ValueError as e:
            self.notify(str(e), severity="error")
    
    def _cancel(self) -> None:
        """Send cancel result"""
        ret = {"choice": "cancel"}
        if self.future:
            self.future.set_result(ret)
        self.dismiss()

    def _continue(self) -> None:
        """Continue with existing steps with no changes"""
        ret = {"choice": "accept", "steps": self.steps}
        if self.future:
            self.future.set_result(ret)
        self.dismiss()

    def _reprompt(self, user_text) -> None:
        """Send an additional prompt back to regenerate new steps"""
        ret = {"choice": "reprompt", "prompt": user_text}
        if self.future:
            self.future.set_result(ret)
        self.dismiss()

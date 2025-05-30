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

    DEFAULT_CSS = """
    StepsScreen {
        align: center middle;
    }

    #steps-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: round $accent;
        padding: 1;
        layout: vertical;
    }

    #header {
        height: 3;
        padding: 0 1;
        border-bottom: solid $accent;
    }

    #header-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #content-area {
        height: 1fr; /* Take remaining space */
        padding: 1; /* Changed */
        overflow-y: auto;
    }

    #steps-description {
        height: auto;
        margin-bottom: 1;
        border: round $panel;
        padding: 0 1; /* Reduced vertical padding */
    }

    #steps-editor {
        height: 1fr; /* Take remaining space in content area */
        margin-bottom: 1;
        border: round $panel;
    }

    #reprompt-label {
        margin-top: 1;
        text-style: bold;
    }

    #reprompt-input {
        height: 5;
        border: round $panel;
    }

    #footer {
        height: 3;
        padding: 0 1; /* Changed */
        border-top: solid $accent;
        align: left middle; /* Align buttons to the left */
    }

    #footer Button {
        margin-left: 1;
    }
    """
    
    def __init__(self, steps: List[dict]) -> None:
        super().__init__()
        self.steps = steps
        self.future = None
        self.label_title = Label("Generated Steps", id="header-title")
        self.label_reprompt = Label("Additional Instructions", id="reprompt-label")
        self.textarea_reprompt = TextArea("", id="reprompt-input", language="markdown")
        self.button_continue = Button("Continue", id="continue-button", tooltip="Proceed with the suggested steps")
        self.button_accept_all = Button("Auto Accept", id="accept-all-button", variant="success", tooltip="Automatically accepts all prompts for this code task") # New Button
        self.button_save = Button("Save Edits", id="save-button", variant="success", tooltip="Save the edited steps and proceed")
        self.button_reprompt = Button("Re-Prompt", id="reprompt-button", tooltip="Send an additional prompt that gives more guidance to the AI model")
        self.button_cancel = Button("Cancel", id="cancel-button", variant="error", tooltip="Stop the current coding operation")
        self.richlog_description = RichLog(id="steps-description")
        self.steps_display = TextArea(
                json.dumps(self.steps, indent=2),
                id="steps-editor",
                language="json"
            )
    
    def compose(self) -> Generator[Any, None, None]:
        with Vertical(id="steps-container"):
            with Horizontal(id="header"):
                yield self.label_title
            
            with Vertical(id="content-area"):
                yield self.richlog_description
                yield self.steps_display
                
                # Additional instructions input, hidden by default
                yield self.label_reprompt
                yield self.textarea_reprompt
            
            with Horizontal(id="footer"):
                yield self.button_continue
                yield self.button_accept_all # Yield new button
                yield self.button_save
                yield self.button_reprompt
                yield self.button_cancel
    
    def on_mount(self) -> None:
        """Setup the screen on mount"""
        self.label_reprompt.display = False
        self.textarea_reprompt.display = False
        self.richlog_description.write(explainer)
        self.richlog_description.wrap = True
    
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
                self.button_accept_all.display = False
                self.button_reprompt.label = "Send"
                self.button_cancel.label = "Cancel Re-Prompt"
        elif button_id == "accept-all-button": # Handle Accept All
            self._accept_all()
        elif button_id == "cancel-button":
            if self.label_reprompt.display:
                # in reprompt mode, this is cancelling reprompt, so return items to "normal"
                self.label_reprompt.display = False
                self.textarea_reprompt.display = False
                self.button_save.display = True
                self.button_continue.display = True
                self.button_accept_all.display = True
                self.button_reprompt.label = "Re-Prompt"
                self.button_cancel.label = "Cancel"
            else:
                self._cancel()
    
    def _process_steps(self) -> None:
        """Process and validate steps before returning"""
        steps_text = self.query_one("#steps-editor").text
        try:
            edited_steps = json.loads(steps_text)
            # Basic validation of steps
            self.validate_steps(edited_steps)

            ret = {"choice": "edit", "steps": edited_steps}
            if self.future:
                self.future.set_result(ret)
            self.dismiss()
        except json.JSONDecodeError:
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
        # Re-parse the potentially edited steps before continuing
        steps_text = self.query_one("#steps-editor").text
        try:
            current_steps = json.loads(steps_text)
            self.validate_steps(current_steps)
            ret = {"choice": "accept", "steps": current_steps}
            if self.future:
                self.future.set_result(ret)
            self.dismiss()
        except json.JSONDecodeError:
            self.notify("Invalid JSON format. Cannot continue.", severity="error")
        except ValueError as e:
             self.notify(f"Invalid steps format: {e}. Cannot continue.", severity="error")

    def _accept_all(self) -> None:
        """Accept all steps and set accept_all flag"""
        steps_text = self.query_one("#steps-editor").text
        try:
            current_steps = json.loads(steps_text)
            self.validate_steps(current_steps)
            ret = {"choice": "accept_all", "steps": current_steps}
            if self.future:
                self.future.set_result(ret)
            self.dismiss()
        except json.JSONDecodeError:
            self.notify("Invalid JSON format. Cannot accept all.", severity="error")
        except ValueError as e:
            self.notify(f"Invalid steps format: {e}. Cannot accept all.", severity="error")

    def validate_steps(self, current_steps):
        if "steps" not in current_steps:
            raise ValueError("Failed to parse steps object: missing 'steps' key.")
        # Perform the same validation as _process_steps
        if not isinstance(current_steps["steps"], list):
            raise ValueError("Steps must be a list of dictionaries")
        for step in current_steps["steps"]:
            if not all(k in step for k in ["operation_type", "filename", "description"]):
                raise ValueError("Each step must contain 'operation_type', 'filename', and 'description'")

    def _reprompt(self, user_text) -> None:
        """Send an additional prompt back to regenerate new steps"""
        ret = {"choice": "reprompt", "prompt": user_text}
        if self.future:
            self.future.set_result(ret)
        self.dismiss()

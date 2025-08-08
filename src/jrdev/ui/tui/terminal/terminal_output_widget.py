from jrdev.messages.message_builder import MessageBuilder
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.ui.tui.terminal.command_confirmation_widget import CommandConfirmationWidget
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.model_listview import ModelListView
from textual import events, on
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Horizontal, Vertical, Container
from textual.widget import Widget
from textual.widgets import Button, Label
from typing import Optional
import logging
import pyperclip
import asyncio
import tiktoken

from jrdev.ui.tui.terminal.input_widget import CommandTextArea
from jrdev.ui.tui.terminal.terminal_text_area import TerminalTextArea

logger = logging.getLogger("jrdev")

class TerminalOutputWidget(Widget):
    # Default compose stacks vertically, which is fine.
    # Using Vertical explicitly offers more control if needed later.
    DEFAULT_CSS = """
    TerminalOutputWidget {
        /* Layout for children: Text Area grows, Button stays at bottom */
        layout: vertical;
        layers: bottom top;
        layer: bottom;
    }
    #terminal_output {
        height: 1fr; /* Ensure text area takes available vertical space */
        width: 100%;
        border: none; /* Confirm no border */
    }
    #copy_btn_term {
        height: 1;
        margin-left: 1;
        width: 10;
    } 
    
    #model_btn_term {
        height: 1;
        margin-left: 1;
        width: auto;
    }
    #model-listview-term {
        border: round #63f554;
        layer: top;
        width: auto;
        height: 10;
    }
    #button-layout {
        layer: bottom;
        height: 1;
        width: auto;
        margin: 0;
    }
    #vlayout_output {
        layer: bottom;
        border: none;
        padding: 0;
        margin: 0;
    }
    #terminal_output, #cmd_input {
        layer: bottom;
    }
    #confirmation-container {
        layer: bottom;
        border: round red;
        height: 1fr;
        max-height: 7;
        width: 100%;
        overflow-y: auto;
    }
    CommandConfirmationWidget {
        layer: bottom;
        height: auto;
        width: auto;
    }
    #context-label {
        margin-left: 1;
        color: #7a7a7a;
        align-horizontal: right;
    }
    #compact-btn, #clear-btn {
        width: 3;
        max-width: 3;
        margin-left: 1;
        height: 1;
    }
    """

    def __init__(self, id: Optional[str] = None, output_widget_mode=False, core_app=None) -> None:
        super().__init__(id=id)
        # output_widget_mode provides the output widget, without the input widget
        self.output_widget_mode = output_widget_mode
        self.terminal_output = TerminalTextArea(_id="terminal_output")
        self.copy_button = Button(label="Copy Selection", id="copy_btn_term")
        if self.output_widget_mode:
            self.copy_button.styles.layer = "bottom"
        else:
            self.model_button = Button(label="Model", id="model_btn_term")
            self.context_label = Label("Context Use 0%", id="context-label")
            self.compact_button = Button(label="🗜️", id="compact-btn", tooltip="Compact conversation. Condenses conversation thread, keeping a summary, but not all details. Reduces Context Use.")
            self.clear_button = Button(label="🗑️", id="clear-btn", tooltip="Clear the entire conversation with the router agent. Sets Context Use to 0.")
            if not core_app:
                raise Exception("core app reference missing from terminal output widget")
            self.core_app = core_app
            self.model_listview = ModelListView(
                id="model-listview-term",
                core_app=core_app,
                model_button=self.model_button,
                above_button=True
            )
            self.model_listview.set_visible(False)
            self.terminal_input = CommandTextArea(placeholder="Enter Command", id="cmd_input")
        self.layout_output = Vertical(id="vlayout_output")
        self.confirmation_container = Container(id="confirmation-container")
        self.confirmation_container.display = False
        self.command_confirmation_future = None
        self._model_list_was_visible = False

    def compose(self) -> ComposeResult:
        with self.layout_output:
            yield self.terminal_output
            if self.output_widget_mode:
                yield self.copy_button
            else:
                yield self.model_listview
                with Horizontal(id="button-layout"):
                    yield self.copy_button
                    yield self.model_button
                    yield self.compact_button
                    yield self.clear_button
                    yield self.context_label
        
        yield self.confirmation_container

        if not self.output_widget_mode:
            yield self.terminal_input

    async def on_mount(self) -> None:
        self.can_focus = False
        self.terminal_output.can_focus = True
        self.copy_button.can_focus = True
        self.terminal_output.soft_wrap = True
        self.terminal_output.read_only = True
        self.terminal_output.show_line_numbers = False

        if self.output_widget_mode:
            self.styles.height = "1fr"
        else:
            self.terminal_input.focus()
            self.terminal_input.border_title = "Command Input"
            self.terminal_input.styles.border = ("round", Color.parse("#5e5e5e"))
            self.terminal_input.styles.border_title_color = "#fabd2f"
            self.terminal_input.styles.height = 6
            self.layout_output.border_title = "JrDev Terminal"
            self.layout_output.styles.border = ("round", Color.parse("#5e5e5e"))
            self.layout_output.styles.border_title_color = "#fabd2f"

    @on(Button.Pressed, "#copy_btn_term")
    def handle_copy(self):
        self.copy_to_clipboard()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """
        Capture the visibility state of the model list view before other events are processed.
        This helps prevent a race condition between the button press and blur events.
        """
        if not self.output_widget_mode:
            self._model_list_was_visible = self.model_listview.visible

    @on(Button.Pressed, "#model_btn_term")
    def handle_model_pressed(self):
        self.model_listview.set_visible(not self._model_list_was_visible)

    @on(Button.Pressed, "#clear-btn")
    def handle_clear_pressed(self):
        self.post_message(CommandRequest("/routeragent clear"))
        self.context_label.update(f"Context Use: 0%")

    @on(Button.Pressed, "#compact-btn")
    def handle_compact_pressed(self):
        self.post_message(CommandRequest("/compact"))

    @on(ModelListView.ModelSelected, "#model-listview-term")
    async def handle_model_selection(self, event: ModelListView.ModelSelected):
        model_name = event.model
        # terminal interacts with intent_router
        self.post_message(CommandRequest(f"/modelprofile set intent_router {model_name}"))
        self.model_listview.set_visible(False)
        self.model_button.styles.max_width = len(model_name) + 2
        await self.update_token_progress()

    def update_models(self):
        model = self.core_app.profile_manager().get_model("intent_router")
        self.model_button.label = model

    async def _get_current_token_usage(self):
        if not self.core_app:
            return 0, 100  # Default values if core_app is not available

        model_name = self.core_app.profile_manager().get_model("intent_router")
        if not model_name:
            return 0, 100

        # Get the context window for the model
        models = self.core_app.get_models()
        context_window = 27000  # Default
        for model in models:
            if model["name"] == model_name:
                context_window = model.get("context_tokens", 27000)
                break

        # Get current token usage from the thread
        thread = self.core_app.get_router_thread()
        if not thread:
            return 0, context_window

        builder = MessageBuilder(self.core_app)
        # Use the agent's private message history
        if thread.messages:
            builder.add_historical_messages(thread.messages)

        # Build the prompt for the LLM
        select_action_prompt = PromptManager().load("router/select_command")
        if self.core_app.router_agent:
            select_action_prompt = select_action_prompt.replace("tools_list", self.core_app.router_agent.get_formatted_tools())
            select_action_prompt = select_action_prompt.replace("commands_list", self.core_app.router_agent.get_formatted_commands())
        else:
            select_action_prompt = select_action_prompt.replace("tools_list", "")
            select_action_prompt = select_action_prompt.replace("commands_list", "")
        builder.add_system_message(select_action_prompt)
        builder.add_project_summary()

        messages = builder.build()

        # Use tiktoken's cl100k_base encoding for accurate token counting
        token_encoder = tiktoken.get_encoding("cl100k_base")
        input_tokens = 0
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                input_tokens += len(token_encoder.encode(content))
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        input_tokens += len(token_encoder.encode(item.get("text", "")))

        return input_tokens, context_window

    async def update_token_progress(self):
        input_tokens, context_window = await self._get_current_token_usage()
        if context_window and input_tokens:
            use = float(input_tokens) / float(context_window)
            self.context_label.update(f"Context Use: {round(use, 2)}% ({input_tokens} tokens)")

    def copy_to_clipboard(self) -> None:
        # Logic to copy the selected text of the TextArea to the clipboard
        if not self.terminal_output.text:
            return

        if self.terminal_output.selected_text:
            content = self.terminal_output.selected_text
        else:
            content = self.terminal_output.text
        # Use pyperclip to copy to clipboard
        pyperclip.copy(content)
        # Provide visual feedback
        self.notify("Text copied to clipboard", timeout=2)
        
    def append_text(self, text: str) -> None:
        """Append text to the end of the terminal output regardless of cursor position.
        
        This method preserves the current selection and scrolls to the bottom after appending,
        but only if the user is already at or near the bottom. If the user has scrolled away
        from the bottom, the scroll position is preserved.
        
        Args:
            text: The text to append to the terminal output.
        """
        self.terminal_output.append_text(text)
        if not self.output_widget_mode:
            self.call_later(self.update_token_progress)

    def clear_input(self):
        self.terminal_input.value = ""

    async def show_confirmation(self, command: str, future: asyncio.Future) -> None:
        """Shows a command confirmation widget in the terminal."""
        await self.confirmation_container.remove_children()
        self.command_confirmation_future = future

        widget = CommandConfirmationWidget(command=command)
        self.confirmation_container.display = True
        await self.confirmation_container.mount(widget)
        widget.focus()

    @on(CommandConfirmationWidget.Result)
    async def confirmation_callback(self, result: CommandConfirmationWidget.Result) -> None:
        """Callback to handle the user's choice."""
        if self.command_confirmation_future:
            if not self.command_confirmation_future.done():
                self.command_confirmation_future.set_result(result.allow)

        # cleanup
        await self.confirmation_container.remove_children()
        self.confirmation_container.display = False
        if not self.output_widget_mode:
            self.terminal_input.focus()
        self.command_confirmation_future = None
from textual.widgets import Button, Label, RichLog
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual import on
from typing import Any, Dict, List, Optional
from jrdev.models.model_profiles import ModelProfileManager
from jrdev.ui.ui import PrintType, terminal_print
from jrdev.ui.tui.model_selection_widget import ModelSelectionWidget
import logging

logger = logging.getLogger("jrdev")

class ModelSelectionModal(ModalScreen[str]):
    """Modal screen for selecting a model"""

    DEFAULT_CSS = """
    ModelSelectionModal {
        align: center middle;
    }

    #modal-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: round $accent;
        padding: 1;
        layout: vertical;
    }

    #modal-header {
        height: 3;
        padding: 0 1;
        border-bottom: solid $accent;
    }

    #modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #modal-footer {
        height: auto;
        min-height: 3;
        padding: 1;
        border-top: solid $accent;
        layout: horizontal;
        align: center middle;
        width: 100%;
    }

    #save-btn {
        background: $success;
        margin-right: 1;
    }
    
    #cancel-btn {
        background: $error;
    }
    
    ModelSelectionWidget {
        scrollbar-background: #1e1e1e;
        scrollbar-background-hover: #1e1e1e;
        scrollbar-background-active: #1e1e1e;
        scrollbar-color: #63f554 30%;
        scrollbar-color-active: #63f554;
        scrollbar-color-hover: #63f554 50%;
        height: 1fr;
    }
    """

    def __init__(self, profile_name: str, current_model: str, models: List[Dict[str, Any]]) -> None:
        super().__init__()
        self.profile_name = profile_name
        self.current_model = current_model
        self.models = models
        self.model_selection_widget: ModelSelectionWidget = None
        self.selected_model: Optional[str] = None
        self.button_save = Button("Save", variant="success", id="save-btn")
        self.button_cancel = Button("Cancel", variant="default", id="cancel-btn")

    def compose(self) -> Any:
        with Vertical(id="modal-container"):
            with Horizontal(id="modal-header"):
                yield Label(f"Select Model for {self.profile_name}", id="modal-title")

            with Horizontal(id="modal-content"):
                self.model_selection_widget = ModelSelectionWidget(id="model-selection")
                yield self.model_selection_widget

            with Horizontal(id="modal-footer"):
                yield self.button_save
                yield self.button_cancel

    async def on_mount(self) -> None:
        await self.model_selection_widget.setup_models(self.models)
        self.model_selection_widget.set_model_selected(self.current_model)
        self.model_selection_widget.styles.border = "none"
        self.model_selection_widget.styles.height = "90%"
        self.button_save.styles.border = "none"
        self.button_cancel.styles.border = "none"


    @on(Button.Pressed, "#save-btn")
    def handle_save(self) -> None:
        selected_button = self.model_selection_widget.pressed_button
        if selected_button:
            self.selected_model = str(selected_button.label)
            self.dismiss(self.selected_model)
        else:
            self.dismiss(None)

    @on(Button.Pressed, "#cancel-btn")
    def handle_cancel(self) -> None:
        self.dismiss(None)


class ModelProfileScreen(ModalScreen):
    """Modal screen for managing model profiles"""

    DEFAULT_CSS = """
    ModelProfileScreen {
        align: center middle;
    }

    #profile-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: round $accent;
        padding: 1;
        layout: horizontal;
    }

    #header {
        dock: top;
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

    #sidebar {
        width: 20%;
        height: 100%;
        border-right: solid $panel;
    }

    #sidebar-title {
        height: 3;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
        color: $text;
        border-bottom: solid $panel;
    }

    .profile-button {
        width: 100%;
        height: 3;
        margin: 0 0 1 0;
        border: none;
    }

    .profile-button:hover {
        background: $primary-darken-1;
    }

    .profile-button.selected {
        background: $primary;
        text-style: bold;
    }

    #content-area {
        width: 80%;
        height: 100%;
        padding: 1;
    }

    #profile-info {
        height: 1fr;
        margin-bottom: 1;
        overflow-y: auto;
    }

    #model-info {
        height: auto;
        margin-top: 1;
        border: solid $panel;
        padding: 1;
    }

    #model-info-title {
        text-style: bold;
        color: $text;
    }

    #current-model {
        margin-top: 1;
        color: $text-muted;
    }

    #change-model-btn {
        margin-top: 1;
        background: $primary;
        width: 20;
    }

    #footer {
        dock: bottom;
        height: 3;
        padding: 0 1;
        border-top: solid $accent;
    }
    """

    def __init__(self, core_app: Any) -> None:
        super().__init__()
        self.core_app = core_app
        self.manager: ModelProfileManager = core_app.profile_manager()
        self.profiles: Dict[str, str] = {}
        self.selected_profile: Optional[str] = None
        self.profile_richlog = RichLog(id="profile-info")

    def compose(self) -> Any:
        with Vertical(id="profile-container"):
            with Horizontal(id="header"):
                yield Label("Model Profile Management", id="header-title")

            # Sidebar with profile buttons
            with Vertical(id="sidebar"):
                yield Label("Profiles", id="sidebar-title")
                # Profile buttons will be added dynamically

            # Content area
            with Vertical(id="content-area"):
                yield self.profile_richlog
                
                with Vertical(id="model-info"):
                    yield Label("Current Model", id="model-info-title")
                    yield Label("", id="current-model")
                    yield Button("Change Model", id="change-model-btn")

            with Horizontal(id="footer"):
                yield Button("Close", variant="default", id="close-btn")

    async def on_mount(self) -> None:
        """Load profiles and set up the UI when the screen is mounted"""
        self.load_profiles()
        
        # Initially hide the change button until a profile is selected
        self.query_one("#change-model-btn", Button).disabled = True

        self.profile_richlog.wrap = True
        self.profile_richlog.markup = True
        self.profile_richlog.can_focus = False

    def load_profiles(self) -> None:
        """Load current profiles from the manager and populate the sidebar"""
        self.profiles = self.manager.list_available_profiles()
        self.default_profile = self.manager.get_default_profile()

        # Get the sidebar and clear it (except the title)
        sidebar = self.query_one("#sidebar", Vertical)
        for child in list(sidebar.children):
            if child.id != "sidebar-title":
                sidebar.remove(child)

        # Add profile buttons to the sidebar
        for profile in sorted(self.profiles.keys()):
            button = Button(profile, classes="profile-button")
            button.profile_name = profile  # type: ignore
            sidebar.mount(button)
            
        # Select the default profile if no profile is selected
        if not self.selected_profile and self.profiles:
            self.selected_profile = self.default_profile
            self.update_content_area(self.default_profile)
            
            # Find and select the default button
            for button in self.query(".profile-button"):
                if button.profile_name == self.default_profile:  # type: ignore
                    button.add_class("selected")
                    break

    def update_content_area(self, profile_name: str) -> None:
        """Update the content area with the selected profile's information"""
        if profile_name not in self.profiles:
            return
            
        model = self.profiles[profile_name]
        
        # Get profile string info from the ModelProfileManager
        description = self.manager.get_profile_description(profile_name)
        purpose = self.manager.get_profile_purpose(profile_name)
        usage = self.manager.get_profile_usage(profile_name)
        usage_str = ", ".join(usage) if usage else "None"
        
        # Update the rich log with profile information
        profile_info = self.query_one("#profile-info", RichLog)
        profile_info.clear()
        profile_info.write(f"[bold]Profile:[/bold] {profile_name}\n")
        profile_info.write(f"[bold]Description:[/bold] {description}\n")
        profile_info.write(f"[bold]Purpose:[/bold] {purpose}\n")
        profile_info.write(f"[bold]Used in:[/bold] {usage_str}\n")
        
        # Update the current model
        current_model = self.query_one("#current-model", Label)
        current_model.update(f"Currently using: {model}")
        
        # Enable the change button
        self.query_one("#change-model-btn", Button).disabled = False

    @on(Button.Pressed, ".profile-button")
    def handle_profile_button(self, event: Button.Pressed) -> None:
        """Handle clicking a profile button in the sidebar"""
        button = event.button
        profile = button.profile_name  # type: ignore
        
        # Remove selected class from all buttons
        for btn in self.query(".profile-button"):
            btn.remove_class("selected")
            
        # Add selected class to the clicked button
        button.add_class("selected")
        
        # Update the selected profile
        self.selected_profile = profile
        
        # Update the content area
        self.update_content_area(profile)

    @on(Button.Pressed, "#change-model-btn")
    def handle_change_model(self) -> None:
        """Handle clicking the Change Model button"""
        if not self.selected_profile:
            return
            
        # Get the current model for the selected profile
        current_model = self.profiles[self.selected_profile]
        
        # Show the model selection modal
        models = self.core_app.get_models()
        modal = ModelSelectionModal(self.selected_profile, current_model, models)

        def save_profile_model(selected_model):
            if selected_model:
                success = self.manager.update_profile(
                    str(self.selected_profile),
                    str(selected_model),
                    self.core_app.state.model_list
                )

                if success:
                    # Update the profiles dictionary
                    self.profiles[self.selected_profile] = selected_model

                    # Update the content area
                    self.update_content_area(self.selected_profile)

                    # Show success message
                    terminal_print(
                        f"Updated profile '{self.selected_profile}' to use model '{selected_model}'",
                        PrintType.SUCCESS
                    )
                else:
                    terminal_print(
                        f"Failed to update profile '{self.selected_profile}'",
                        PrintType.ERROR
                    )

        # push model screen with callback to save profile
        self.app.push_screen(ModelSelectionModal(self.selected_profile, current_model, models), save_profile_model)

    @on(Button.Pressed, "#close-btn")
    def close_screen(self) -> None:
        """Close the screen"""
        self.dismiss()

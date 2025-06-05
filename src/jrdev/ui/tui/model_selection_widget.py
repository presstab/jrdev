from textual.widgets import RadioButton, RadioSet, Label
from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional
import logging
from textual.color import Color

logger = logging.getLogger("jrdev")

class ModelSelectionWidget(RadioSet):
    def __init__(self, id) -> None:
        super().__init__(id=id)
        self.border_title = "Model"
        self.styles.border = ("round", Color.parse("#5e5e5e"))
        self.styles.border_title_color = "#fabd2f"
        self.styles.width = "100%"
        self.can_focus = False
        self._model_buttons = {}  # Dictionary to track model name to button mapping
        self.block_signals = False # block Changed signal

    @property
    def pressed_button(self) -> Optional[RadioButton]:
        """Get the currently pressed button"""
        for button in self._model_buttons.values():
            if button.value:
                return button
        return None

    async def setup_models(self, models: List[Dict[str, Any]]) -> None:
        """Set up the model list with grouping by provider
        
        Args:
            models: List of models to display
        """
        models_by_provider = defaultdict(list)
        self._model_buttons = {}  # Reset button tracking

        for model in models:
            models_by_provider[model["provider"]].append(model)

        # Reorder to put 'venice' first
        ordered_providers = OrderedDict()

        # Add 'venice' group first if it exists
        if "venice" in models_by_provider:
            ordered_providers["venice"] = models_by_provider.pop("venice")

        # Add remaining providers in sorted order
        for provider in sorted(models_by_provider):
            ordered_providers[provider] = models_by_provider[provider]

        # Mount grouped UI
        for provider, model_group in ordered_providers.items():
            await self.mount(Label(f"{provider}", classes="provider-label"))
            for model in model_group:
                button = RadioButton(model["name"], classes="model-btn")
                button.can_focus = False
                button.BUTTON_RIGHT = ""
                button.BUTTON_LEFT = ""
                button.BUTTON_INNER = "\u2794" #arrow
                await self.mount(button)
                # Store reference to button for selection later
                self._model_buttons[model["name"]] = button

    async def update_models(self, models: List[Dict[str, Any]]) -> None:
        """Replace the current list of provider/model buttons with a new one."""
        # 1) remove all existing UI children (labels & buttons)
        await self.remove_children(".provider-label")
        await self.remove_children(".model-btn")

        # 2) reset our internal mapping
        self._model_buttons.clear()
        await self.setup_models(models)

    def set_model_selected(self, model_name: str) -> bool:
        """Set the model with the given name as selected, Change signal is blocked
        
        Args:
            model_name: Name of the model to select
            
        Returns:
            True if the model was found and selected, False otherwise
        """
        if model_name in self._model_buttons:
            self.block_signals = True
            self._model_buttons[model_name].value = True
            return True
        return False

    def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if self.block_signals:
            event.stop()
            self.block_signals = False
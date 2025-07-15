import typing
from typing import Any

from textual.geometry import Offset
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView


class ModelListView(ListView):
    def __init__(self, id: str, core_app: Any, model_button: Button, above_button: bool):
        super().__init__(id=id)
        self.core_app = core_app
        self.model_button = model_button
        self.above_button = above_button
        self.models_text_width = 1
        self.height = 10
        self.models = []

    def update_models(self) -> None:
        available_models = self.core_app.get_available_models()
        self.models_text_width = 1
        for model_name in available_models:
            if model_name not in self.models:
                self.models.append(model_name)
                self.append(ListItem(Label(model_name), name=model_name))
            self.models_text_width = max(self.models_text_width, len(model_name))

    def set_visible(self, is_visible: bool) -> None:
        self.visible = is_visible
        if is_visible:
            self.update_models()
            self.compute_offset()
            self.styles.min_width = self.model_button.content_size.width
            self.styles.max_width = self.models_text_width + 2

    @typing.no_type_check
    def compute_offset(self):
        offset_x = self.model_button.content_region.x - self.parent.content_region.x
        offset_y = self.model_button.content_region.y - self.parent.content_region.y + 1
        if self.above_button:
            offset_y -= self.height + 1
        self.styles.offset = Offset(x=offset_x, y=offset_y)

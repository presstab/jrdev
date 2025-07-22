import typing
from typing import Any

from textual import on
from textual.geometry import Offset
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView, Input


class ModelListView(Widget):
    DEFAULT_CSS = """
    #model-search-input {
        border: none;
        height: 2;
        border-bottom: solid;
        padding: 0;
        margin: 0;
    }
    """

    class ModelSelected(Message):
        def __init__(self, model_list_view: Widget, model: str):
            self.model = model
            self.model_list_view = model_list_view
            super().__init__()

        @property
        def control(self) -> Widget:
            """An alias for [Pressed.button][textual.widgets.Button.Pressed.button].

            This will be the same value as [Pressed.button][textual.widgets.Button.Pressed.button].
            """
            return self.model_list_view

    def __init__(self, id: str, core_app: Any, model_button: Button, above_button: bool):
        super().__init__(id=id)
        self.core_app = core_app
        self.model_button = model_button
        self.above_button = above_button
        self.models_text_width = 1
        self.height = 10
        self.models = []
        self.search_input = Input(placeholder="Search models...", id="model-search-input")
        self.list_view = ListView(id="_listview")

    def compose(self):
        yield self.search_input
        yield self.list_view

    def update_models(self) -> None:
        available_models = self.core_app.get_available_models()
        self.models_text_width = 1
        self.models = available_models
        self.list_view.clear()
        for model_name in available_models:
            self.models_text_width = max(self.models_text_width, len(model_name))
            self.list_view.append(ListItem(Label(model_name), name=model_name))

    def set_visible(self, is_visible: bool) -> None:
        self.visible = is_visible
        if is_visible:
            self.update_models()
            self.set_dimensions()

            self.search_input.focus()

    @typing.no_type_check
    def set_dimensions(self):
        offset_x = self.model_button.content_region.x - self.parent.content_region.x
        offset_y = self.model_button.content_region.y - self.parent.content_region.y + 1

        if self.above_button:
            self.styles.max_height = offset_y - 1
            self.styles.height = offset_y - 1
            offset_y -= offset_y
        else:
            # Set height based on container bottom
            bottom_margin = 5
            self.styles.max_height = self.parent.container_size.height - bottom_margin
            self.styles.height = self.parent.container_size.height - bottom_margin

        self.styles.offset = Offset(x=offset_x, y=offset_y)

        # Set width - don't overrun container boundaries
        self.styles.min_width = self.model_button.content_size.width
        max_width = self.models_text_width + 2
        container_available_width = self.parent.content_region.width - offset_x
        self.styles.max_width = min(max_width, container_available_width)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "model-search-input":
            return
        query = event.value.lower()
        self.list_view.clear()
        for model_name in self.models:
            if query in model_name.lower():
                self.list_view.append(ListItem(Label(model_name), name=model_name))

    @on(ListView.Selected, "#_listview")
    def selection_updated(self, selected: ListView.Selected) -> None:
        self.post_message(self.ModelSelected(self, selected.item.name))

import typing
from typing import Any

from textual import on, events
from textual.color import Color
from textual.geometry import Offset
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView, Input
from textual.events import Key

import logging
logger = logging.getLogger("jrdev")

class SearchInput(Input):
    # Change tab key to a submit signal
    async def _on_key(self, event: events.Key) -> None:
        if event.key == "tab":
            self.post_message(self.Submitted(self, self.value))
        else:
            await super()._on_key(event)

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
        self.search_input = SearchInput(placeholder="Search models...", id="model-search-input")
        self.list_view = ListView(id="_listview")
        self.input_query = None

    def compose(self):
        yield self.search_input
        yield self.list_view

    def update_models(self, query_filter: str = "") -> None:
        models_list = self.core_app.get_models()
        sorted_models = sorted(models_list, key=lambda model: (model["provider"], model["name"]))

        self.models_text_width = 1
        self.models = sorted_models
        self.list_view.clear()

        # Group models into provider sections with provider headers
        grouped_models = {}
        for model in sorted_models:
            provider = model["provider"]
            if provider not in grouped_models:
                grouped_models[provider] = []
            if query_filter:
                if query_filter in model["name"].lower():
                    grouped_models[provider].append(model)
            else:
                grouped_models[provider].append(model)

        # Colorize provider headers
        star_color: Color = Color.parse("white")
        if len(self.styles.border) > 1:
            star_color = self.styles.border.top[1]

        for provider, provider_models in grouped_models.items():
            provider_item = ListItem(Label(f"[{star_color.rich_color.name}][bold white]✨{provider}✨[/bold white][/{star_color.rich_color.name}]", markup=True), name=provider, disabled=True)
            self.list_view.append(provider_item)
            for model in provider_models:
                model_name = model["name"]
                self.models_text_width = max(self.models_text_width, len(model_name))
                self.list_view.append(ListItem(Label(model_name), name=model_name))

    def set_visible(self, is_visible: bool) -> None:
        self.visible = is_visible
        if is_visible:
            self.search_input.clear()
            self.input_query = None
            self.update_models()
            self.set_dimensions()

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

    def _set_list_view_index(self, index: int) -> None:
        """Helper method to set the list view index."""
        self.list_view.index = index

    def on_input_changed(self, event: Input.Changed) -> None:
        """Search filter changed"""
        if event.input.id != "model-search-input":
            return

        # Update models with filter
        query = event.value.lower()
        self.update_models(query_filter=query)

        if len(self.list_view.children):
            for i, item in enumerate(self.list_view.children):
                if not item.disabled:
                    self.list_view.index = i
                    self.list_view.children[i].highlighted = True
                    break

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter pressed on search input -> results in highlighted item being selected"""
        if self.list_view.index is not None:
            selected_item = self.list_view.children[self.list_view.index]
            if not selected_item.disabled:
                self.post_message(self.ModelSelected(self, selected_item.name))
        event.stop()

    def on_key(self, event: Key) -> None:
        if not self.visible:
            return
            
        if event.key == "up":
            if self.list_view.index is not None:
                new_index = self.list_view.index - 1
                while new_index >= 0 and self.list_view.children[new_index].disabled:
                    new_index -= 1
                if new_index >= 0:
                    self.list_view.index = new_index
            event.stop()
        elif event.key == "down":
            if self.list_view.index is not None:
                new_index = self.list_view.index + 1
                while new_index < len(self.list_view.children) and self.list_view.children[new_index].disabled:
                    new_index += 1
                if new_index < len(self.list_view.children):
                    self.list_view.index = new_index
            event.stop()
        elif event.key == "enter":
            if self.list_view.index is not None:
                selected_item = self.list_view.children[self.list_view.index]
                if not selected_item.disabled:
                    self.post_message(self.ModelSelected(self, selected_item.name))
            event.stop()

    @on(ListView.Selected, "#_listview")
    def selection_updated(self, selected: ListView.Selected) -> None:
        if not selected.item.disabled:
            self.post_message(self.ModelSelected(self, selected.item.name))

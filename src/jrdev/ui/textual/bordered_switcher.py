from textual.widgets import ContentSwitcher


class BorderedSwitcher(ContentSwitcher):
    def watch_current(self, old: str|None, new: str|None) -> None:
        # first let the stock logic hide/show children
        super().watch_current(old, new)

        # now tell the App that we flipped panels
        # we assume the App implements _on_panel_switched(old, new)
        if hasattr(self.app, "_on_panel_switched"):
            self.app._on_panel_switched(old, new)
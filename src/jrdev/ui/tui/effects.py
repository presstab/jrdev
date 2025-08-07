from textual.widgets import Button
from jrdev.ui.tui.confetti import ConfettiWidget

def show_confetti(button: Button):
    """
    Show a confetti animation originating from the button's position.
    """
    if not button.screen:
        return

    # Get the button's position relative to the screen
    button_region = button.region
    x = button_region.x + button_region.width // 2
    y = button_region.y

    # Create and mount the confetti widget
    confetti_widget = ConfettiWidget(x=x, y=y)
    button.screen.mount(confetti_widget)

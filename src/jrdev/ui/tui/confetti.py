import random
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.timer import Timer
from textual.color import Color

class ConfettiWidget(Widget):
    """A widget to display a confetti animation."""

    def __init__(self, x: int, y: int, num_particles: int = 50, duration: float = 2.0):
        super().__init__()
        self.x = x
        self.y = y
        self.num_particles = num_particles
        self.duration = duration
        self.particles = []

    def on_mount(self) -> None:
        """Create the confetti particles."""
        self.styles.background = "transparent"
        self.styles.border = ("none", "transparent")
        self.styles.layout = "absolute"
        self.styles.width = "100%"
        self.styles.height = "100%"
        for _ in range(self.num_particles):
            particle = self._create_particle()
            self.particles.append(particle)
            self.mount(particle["widget"])

    def _create_particle(self):
        """Creates a single confetti particle with random properties."""
        colors = [
            "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff",
            "#ff4500", "#da70d6", "#1e90ff", "#32cd32", "#ffd700", "#ff69b4"
        ]
        symbols = ["*", "•", "▪", "▲", "▼"]

        start_x = self.x
        start_y = self.y

        # Give it a random velocity
        velocity_x = random.uniform(-15, 15)
        velocity_y = random.uniform(-7, -2) # Start by moving up

        particle_widget = Static(random.choice(symbols))
        particle_widget.styles.color = random.choice(colors)
        particle_widget.styles.offset = (round(start_x), round(start_y))

        return {
            "widget": particle_widget,
            "x": start_x,
            "y": start_y,
            "vx": velocity_x,
            "vy": velocity_y,
            "gravity": 0.3
        }

    def on_show(self) -> None:
        """Start the animation when the widget is shown."""
        self.animation_timer = self.set_interval(1 / 24, self.update_animation)
        self.self_destruct_timer = self.set_timer(self.duration, self.remove_widget)

    def update_animation(self) -> None:
        """Update the position of each particle."""
        for p in self.particles:
            p["vx"] *= 0.99  # Air resistance
            p["vy"] += p["gravity"]
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["widget"].styles.offset = (round(p["x"]), round(p["y"]))

    def remove_widget(self) -> None:
        """Stop the timers and remove the widget."""
        self.animation_timer.stop()
        self.remove()

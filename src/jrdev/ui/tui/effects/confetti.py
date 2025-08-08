import asyncio
import random
from textual.app import ComposeResult
from textual.widget import Widget
from textual.color import Color
from textual.geometry import Offset

class ConfettiWidget(Widget):
    """A widget to display a confetti animation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.particles = []
        self.animation_task = None

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.styles.layer = "confetti"
        self.styles.background = "transparent"
        self.styles.width = "100%"
        self.styles.height = "100%"
        self.styles.visibility = "hidden"

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield from []

    def start(self, duration: float = 2.0):
        """Start the confetti animation."""
        if self.animation_task:
            self.animation_task.cancel()

        self.styles.visibility = "visible"
        self.particles = self._create_particles()
        self.animation_task = self.app.create_background_task(self._animate(duration))

    async def _animate(self, duration: float):
        """Animate the particles."""
        start_time = self.app.get_time()

        while self.app.get_time() - start_time < duration:
            self._update_particles()
            self.refresh()
            await asyncio.sleep(0.05)

        self._stop()

    def _stop(self):
        """Stop the confetti animation."""
        self.particles.clear()
        self.styles.visibility = "hidden"
        self.refresh()

    def _create_particles(self) -> list:
        """Create a list of particles."""
        particles = []
        for _ in range(100):
            x = random.uniform(0, self.size.width)
            y = random.uniform(0, self.size.height)
            vx = random.uniform(-2, 2)
            vy = random.uniform(-2, 2)
            color = Color.from_hsl(random.random(), 1.0, 0.5)
            particles.append([x, y, vx, vy, color])
        return particles

    def _update_particles(self):
        """Update the position of the particles."""
        for particle in self.particles:
            particle[0] += particle[2]
            particle[1] += particle[3]
            particle[3] += 0.1  # Gravity

    def render(self) -> str:
        """Render the widget."""
        if not self.particles:
            return ""

        lines = []
        for x, y, _, _, color in self.particles:
            if 0 <= x < self.size.width and 0 <= y < self.size.height:
                lines.append(f"\x1b[38;2;{color.r};{color.g};{color.b}m\x1b[{int(y)};{int(x)}H*")

        return "".join(lines)

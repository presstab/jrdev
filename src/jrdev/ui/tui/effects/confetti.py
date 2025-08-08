import random
import asyncio
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual import work

class ConfettiWidget(Widget):
    """A widget to display a confetti animation."""

    DEFAULT_CSS = """
    ConfettiWidget {
        width: 100%;
        height: 100%;
        background: transparent;
        overflow: hidden;
    }
    .confetti-particle {
        position: absolute;
        width: 1;
        height: 1;
    }
    """

    PRIMARY_COLORS = [
        "red",
        "yellow",
        "blue",
    ]

    def __init__(self, particle_count: int = 50):
        super().__init__()
        self.particle_count = particle_count
        self.particles: list[Static] = []
        self.particle_physics: list[tuple[float, float, float, float]] = []

    def on_mount(self) -> None:
        """Set up the initial state of the particles."""
        width = self.size.width
        # Start particles near the top-center
        start_x = width / 2
        for particle in self.particles:
            x = start_x
            y = 1.0  # Start just below the top edge
            # Give each particle a random initial velocity
            vx = random.uniform(-15, 15)  # Horizontal velocity
            vy = random.uniform(-5, -2)   # Initial upward velocity
            self.particle_physics.append((x, y, vx, vy))
            particle.styles.offset = (int(x), int(y))

    def compose(self) -> ComposeResult:
        """Create confetti particles."""
        for _ in range(self.particle_count):
            particle = Static("*", classes="confetti-particle")
            particle.styles.color = random.choice(self.PRIMARY_COLORS)
            self.particles.append(particle)
            yield particle

    def start(self):
        """Start the confetti animation."""
        self.run_worker(self.animate_confetti, exclusive=True)

    @work
    async def animate_confetti(self) -> None:
        """The worker that animates the confetti."""
        gravity = 0.2  # A gentle pull downwards
        friction = 0.98  # Slow down horizontal movement over time
        end_time = asyncio.get_running_loop().time() + 3.0

        while asyncio.get_running_loop().time() < end_time:
            new_physics = []
            for i, (x, y, vx, vy) in enumerate(self.particle_physics):
                # Apply gravity
                vy += gravity
                # Apply friction
                vx *= friction

                # Update position based on velocity
                x += vx * 0.2  # Adjust multiplier for speed
                y += vy * 0.2

                new_physics.append((x, y, vx, vy))

                # Update widget style
                self.particles[i].styles.offset = (int(x), int(y))

            self.particle_physics = new_physics
            await asyncio.sleep(1 / 60) # Aim for 60fps

        # Animation finished, remove the widget
        self.remove()

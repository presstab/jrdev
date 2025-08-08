import random
from textual.widget import Widget
from textual.widgets import Static
from textual.color import Color
from textual.geometry import Offset


class Particle(Static):
    """A single confetti particle."""

    def __init__(self, position: Offset, velocity: Offset, color: Color) -> None:
        super().__init__("*")
        self.styles.color = color
        self.styles.offset = position
        self.velocity = velocity
        self.lifespan = random.uniform(1.5, 4)
        self.age = 0

    async def update(self, dt: float) -> bool:
        """Update the particle's position and age."""
        self.age += dt
        if self.age > self.lifespan:
            return False

        offset = self.styles.offset
        new_x = offset.x + self.velocity.x * dt
        new_y = offset.y + self.velocity.y * dt
        self.styles.offset = Offset(round(new_x), round(new_y))

        self.velocity = Offset(self.velocity.x, self.velocity.y + 40 * dt)  # Gravity
        return True


class ConfettiWidget(Widget):
    """A widget to display a confetti animation."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.particles: list[Particle] = []
        self.timer = None
        self.styles.display = "none"

    async def start(self) -> None:
        """Start the confetti animation."""
        self.styles.display = "block"
        await self.remove_children()
        self.particles = []

        for _ in range(100):
            position = Offset(random.randint(0, self.size.width), random.randint(-10, 0))
            velocity = Offset(random.uniform(-25, 25), random.uniform(-10, 10))
            color = Color(
                random.randint(50, 255),
                random.randint(50, 255),
                random.randint(50, 255),
            )
            particle = Particle(position, velocity, color)
            self.particles.append(particle)
            self.mount(particle)

        if self.timer:
            self.timer.stop()
        self.timer = self.set_interval(1 / 30, self.update_particles)

        # Stop after a while
        self.set_timer(3, self.stop)

    async def stop(self) -> None:
        """Stop the confetti animation."""
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.styles.display = "none"
        await self.remove_children()
        self.particles = []

    async def update_particles(self) -> None:
        """Update all particles."""
        dt = 1 / 30
        to_remove = []
        for particle in self.particles:
            if not await particle.update(dt):
                to_remove.append(particle)

        for particle in to_remove:
            await particle.remove()
            if particle in self.particles:
                self.particles.remove(particle)

        if not self.particles and self.timer:
            await self.stop()

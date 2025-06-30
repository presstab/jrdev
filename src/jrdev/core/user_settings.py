from dataclasses import dataclass


@dataclass
class UserSettings:
    max_router_iterations: int = 10

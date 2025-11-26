from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Coord = Tuple[int, int]


@dataclass
class Orc:
    id: int
    position: Coord
    kind: int
    strength: float
    agility: float
    resilience: float
    energy: float
    age: int = 0
    infected: bool = False
    infection_timer: int = 0

    def tick(self, energy_decay: float) -> None:
        self.age += 1
        self.energy -= energy_decay

    def adjust_energy(self, delta: float) -> None:
        self.energy += delta

    def fitness(self) -> float:
        return (self.strength * 1.1) + (self.agility * 0.9) + (self.resilience * 0.8)

    def clone_with_mutation(
        self,
        rng,
        mutation_rate: float,
        mutation_scale: float,
        next_id: int,
    ) -> "Orc":
        def mutate(value: float) -> float:
            if rng.random() < mutation_rate:
                return max(0.1, value + rng.uniform(-mutation_scale, mutation_scale))
            return value

        return Orc(
            id=next_id,
            position=self.position,
            kind=self.kind,
            strength=mutate(self.strength),
            agility=mutate(self.agility),
            resilience=mutate(self.resilience),
            energy=self.energy * 0.6,
            age=0,
            infected=False,
            infection_timer=0,
        )

    def infect(self, duration: int) -> None:
        self.infected = True
        self.infection_timer = max(duration, 1)

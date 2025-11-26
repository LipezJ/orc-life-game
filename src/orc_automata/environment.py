from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Tuple

from .orc import Orc


Coord = Tuple[int, int]


@dataclass
class Cell:
    x: int
    y: int
    orc: Optional[Orc] = None


class Environment:
    def __init__(self, width: int, height: int, rng: Optional[random.Random] = None) -> None:
        self.width = width
        self.height = height
        self.rng = rng or random.Random()
        self._grid: list[list[Optional[Orc]]] = [
            [None for _ in range(width)] for _ in range(height)
        ]
        self._humidity = self._generate_layer(bias=0.55, variation=0.22, vertical_pull=-0.2, smooth_passes=4)
        self._fertility = self._generate_layer(bias=0.5, variation=0.24, vertical_pull=0.16, smooth_passes=4)
        self._biome = self._generate_biomes()

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> Optional[Orc]:
        return self._grid[y][x]

    def place(self, orc: Orc, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            raise ValueError("Position out of bounds")
        if self._grid[y][x] is not None:
            raise ValueError("Cell already occupied")
        self._grid[y][x] = orc
        orc.position = (x, y)

    def move(self, orc: Orc, dest: Coord) -> None:
        dx, dy = dest
        if not self.in_bounds(dx, dy):
            return
        sx, sy = orc.position
        if self._grid[dy][dx] is None:
            self._grid[sy][sx] = None
            self._grid[dy][dx] = orc
            orc.position = (dx, dy)

    def remove(self, orc: Orc) -> None:
        x, y = orc.position
        if self._grid[y][x] is orc:
            self._grid[y][x] = None

    def neighbors(self, x: int, y: int) -> Iterator[Coord]:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield nx, ny

    def empty_neighbors(self, x: int, y: int) -> list[Coord]:
        return [coord for coord in self.neighbors(x, y) if self.get(*coord) is None]

    def occupied_neighbors(self, x: int, y: int) -> list[Coord]:
        return [coord for coord in self.neighbors(x, y) if self.get(*coord)]

    def iter_orcs(self) -> Iterable[Orc]:
        for row in self._grid:
            for maybe_orc in row:
                if maybe_orc:
                    yield maybe_orc

    def humidity_at(self, x: int, y: int) -> float:
        return self._humidity[y][x]

    def fertility_at(self, x: int, y: int) -> float:
        return self._fertility[y][x]

    def biome_at(self, x: int, y: int) -> int:
        return self._biome[y][x]

    def _generate_layer(
        self,
        bias: float,
        variation: float,
        vertical_pull: float,
        smooth_passes: int = 3,
    ) -> list[list[float]]:
        # Start with noisy values plus a vertical gradient and then smooth to get organic patches.
        layer: list[list[float]] = []
        denom = max(1, self.height - 1)
        for y in range(self.height):
            row: list[float] = []
            gradient = y / denom
            for _x in range(self.width):
                base = bias + vertical_pull * (gradient - 0.5)
                noise = self.rng.uniform(-variation, variation)
                row.append(base + noise)
            layer.append(row)
        for _ in range(max(0, smooth_passes)):
            layer = self._smooth(layer)
        return [[max(0.0, min(1.0, v)) for v in row] for row in layer]

    def _smooth(self, layer: list[list[float]]) -> list[list[float]]:
        smoothed: list[list[float]] = []
        for y in range(self.height):
            row: list[float] = []
            for x in range(self.width):
                cell_weight = 0.5
                count = 0
                neighbor_weight = 0.5
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            count += 1
                weight_per_neighbor = neighbor_weight / max(1, count)
                acc = layer[y][x] * cell_weight
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            acc += layer[ny][nx] * weight_per_neighbor
                row.append(acc if count else layer[y][x])
            smoothed.append(row)
        return smoothed

    def _generate_biomes(self) -> list[list[int]]:
        noise = self._generate_layer(bias=0.5, variation=0.35, vertical_pull=0.0, smooth_passes=3)
        # Flatten to compute thresholds for 3 roughly equal areas.
        flat = [v for row in noise for v in row]
        sorted_vals = sorted(flat)
        third = len(sorted_vals) // 3
        t1 = sorted_vals[third]
        t2 = sorted_vals[2 * third]
        biomes: list[list[int]] = []
        for row in noise:
            bio_row: list[int] = []
            for v in row:
                if v < t1:
                    bio_row.append(0)
                elif v < t2:
                    bio_row.append(1)
                else:
                    bio_row.append(2)
            biomes.append(bio_row)
        return biomes

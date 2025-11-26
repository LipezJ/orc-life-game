from __future__ import annotations

from typing import Tuple

from ..orc import Orc


Color = Tuple[int, int, int]

DEEP_BG: Color = (14, 20, 28)
GRID: Color = (34, 46, 56)
HUD: Color = (230, 235, 238)
BIOME_TINTS: list[Color] = [
    (30, 10, 0),   # biome 0 slight reddish
    (0, 25, 5),    # biome 1 slight green
    (0, 5, 30),    # biome 2 slight blue
]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _lerp(a: Color, b: Color, t: float) -> Color:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def color_for_orc(orc: Orc) -> Color:
    # Blend colors based on dominant traits to make clusters visible.
    trait_total = orc.strength + orc.agility + orc.resilience
    if trait_total <= 0:
        return (120, 120, 120)
    strength_ratio = _clamp(orc.strength / trait_total, 0.0, 1.0)
    agility_ratio = _clamp(orc.agility / trait_total, 0.0, 1.0)
    resilience_ratio = _clamp(orc.resilience / trait_total, 0.0, 1.0)
    base = (
        int(120 + 80 * strength_ratio),
        int(120 + 80 * agility_ratio),
        int(120 + 80 * resilience_ratio),
    )
    energy_factor = _clamp(orc.energy / 15.0, 0.2, 1.0)
    healthy = _lerp((30, 40, 40), base, energy_factor)
    if orc.infected:
        # Tint toward purple when infected.
        return _lerp(healthy, (160, 80, 200), 0.55)
    return healthy


def color_for_humidity(value: float) -> Color:
    level = _clamp(value, 0.0, 1.0)
    dry = (94, 73, 52)
    mid = (70, 100, 110)
    wet = (40, 125, 150)
    if level < 0.5:
        return _lerp(dry, mid, level * 2)
    return _lerp(mid, wet, (level - 0.5) * 2)


def blend_biome(base: Color, biome: int, strength: float = 0.18) -> Color:
    tint = BIOME_TINTS[biome % len(BIOME_TINTS)]
    return _lerp(base, tint, strength)

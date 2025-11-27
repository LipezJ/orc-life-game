from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationSettings:
    grid_width: int = 64
    grid_height: int = 40
    cell_size: int = 16
    tick_rate: int = 6
    classes: int = 3
    initial_orc_ratio: float = 0.08
    max_age: int = 220
    base_energy: float = 18.0
    energy_decay: float = 0.32
    move_cost: float = 0.55
    fight_reward: float = 2.6
    fight_cost: float = 0.8
    reproduction_threshold: float = 6.0
    reproduction_chance: float = 0.12
    reproduction_energy_share: float = 0.35
    reproduction_overpop_pop_threshold: int = 200
    reproduction_overpop_factor: float = 0.5
    mutation_rate: float = 0.15
    mutation_scale: float = 0.25
    humidity_penalty: float = 0.18
    humidity_bonus: float = 0.15
    forage_gain: float = 1.8
    forage_cost: float = 0.25
    rest_threshold: float = 5.5
    aggression_bias: float = 0.45
    herd_radius: int = 3
    herd_attraction: float = 0.55
    pair_seek_multiplier: float = 1.8
    escape_strength_threshold: float = 0.95
    escape_threat_radius: int = 2
    escape_threat_weight: float = 0.6
    biome_bonus: float = 0.16
    biome_penalty: float = 0.12
    peace_floor_count: int = 4
    skirmish_threshold: float = 0.9
    skirmish_cost_factor: float = 0.7
    group_support_bonus: float = 0.15
    group_support_radius: int = 2
    loner_grit_bonus: float = 0.35
    loner_grit_threshold: int = 3
    support_score_factor: float = 0.12
    virus_spawn_base: float = 0.0002
    virus_spawn_stressed: float = 0.0012
    virus_crowd_threshold: int = 6
    virus_crowd_pop_threshold: int = 150
    virus_crowd_multiplier: float = 5
    virus_spread_chance: float = 0.04
    virus_duration: int = 30
    virus_energy_penalty: float = 0.6
    virus_fight_penalty: float = 0.12
    max_population: int = 400
    overpop_base: float = 0.04
    overpop_scale: float = 0.18
    habitat_seek_radius: int = 4
    habitat_seek_bonus: float = 0.4
    habitat_bad_threshold: float = 0.48
    endangered_threshold: int = 15
    endangered_repro_bonus: float = 0.08
    endangered_repro_factor: float = 0.65
    kind_strength_mods: tuple[float, float, float] = (1.1, 0.9, 1.0)
    kind_agility_mods: tuple[float, float, float] = (0.95, 1.1, 1.0)
    kind_resilience_mods: tuple[float, float, float] = (1.0, 0.95, 1.1)
    seed: Optional[int] = None


DEFAULT_SETTINGS = SimulationSettings()

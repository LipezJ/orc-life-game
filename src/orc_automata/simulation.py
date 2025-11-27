from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from .config import DEFAULT_SETTINGS, SimulationSettings
from .environment import Environment
from .orc import Orc


@dataclass
class SimulationMetrics:
    tick: int
    population: int
    average_strength: float
    average_agility: float
    average_resilience: float


class Simulation:
    def __init__(
        self,
        settings: SimulationSettings = DEFAULT_SETTINGS,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.settings = settings
        self.rng = rng or random.Random(settings.seed)
        self.environment = Environment(settings.grid_width, settings.grid_height, rng=self.rng)
        self.population: Dict[int, Orc] = {}
        self.tick = 0
        self._next_id = 1
        self._seed_initial_population()

    def _seed_initial_population(self) -> None:
        capacity = self.settings.grid_width * self.settings.grid_height
        target = int(capacity * self.settings.initial_orc_ratio)
        coords = [
            (x, y)
            for x in range(self.settings.grid_width)
            for y in range(self.settings.grid_height)
        ]
        self.rng.shuffle(coords)
        for x, y in coords[:target]:
            self._spawn_orc((x, y))

    def _spawn_orc(self, position: tuple[int, int]) -> Orc:
        biome = self.environment.biome_at(*position)
        kind = self._kind_for_biome(biome)
        orc = Orc(
            id=self._next_id,
            position=position,
            kind=kind,
            strength=self.rng.uniform(0.5, 1.5),
            agility=self.rng.uniform(0.5, 1.5),
            resilience=self.rng.uniform(0.5, 1.5),
            energy=self.settings.base_energy,
        )
        self._next_id += 1
        self._apply_kind_modifiers(orc)
        self.population[orc.id] = orc
        self.environment.place(orc, *position)
        return orc

    def reset(self) -> None:
        self.environment = Environment(
            self.settings.grid_width,
            self.settings.grid_height,
            rng=self.rng,
        )
        self.population.clear()
        self.tick = 0
        self._next_id = 1
        self._seed_initial_population()

    def step(self) -> None:
        order = list(self.population.values())
        self.rng.shuffle(order)
        for orc in order:
            if orc.id not in self.population:
                continue
            orc.tick(self.settings.energy_decay)
            self._apply_environment_pressure(orc)
            self._apply_social_context(orc)
            self._apply_disease(orc)
            if self._overpop_kill_check(orc):
                continue
            if self._is_dead(orc):
                self._remove_orc(orc)
                continue
            reproduced = self._maybe_reproduce(orc)
            if reproduced:
                continue
            self._take_action(orc)
        self.tick += 1

    def _apply_environment_pressure(self, orc: Orc) -> None:
        humidity = self.environment.humidity_at(*orc.position)
        if humidity < 0.45:
            penalty = (0.45 - humidity) * self.settings.humidity_penalty
            orc.adjust_energy(-penalty)
        elif humidity > 0.65:
            bonus = (humidity - 0.65) * self.settings.humidity_bonus
            orc.adjust_energy(bonus)
        biome = self.environment.biome_at(*orc.position)
        bonus, penalty = self._biome_effect(orc.kind, biome)
        if bonus:
            orc.adjust_energy(bonus)
        if penalty:
            orc.adjust_energy(-penalty)

    def _apply_social_context(self, orc: Orc) -> None:
        friends, foes = self._social_counts(orc)
        if friends >= 2:
            boost = min(3, friends) * self.settings.group_support_bonus
            orc.adjust_energy(boost)
        if foes >= friends + self.settings.loner_grit_threshold:
            orc.adjust_energy(self.settings.loner_grit_bonus)

    def _apply_disease(self, orc: Orc) -> None:
        if not orc.infected and self.rng.random() < self._virus_spawn_chance(orc):
            orc.infect(self.settings.virus_duration)
        if not orc.infected:
            return
        orc.infection_timer -= 1
        orc.adjust_energy(-self.settings.virus_energy_penalty)
        # Spread with low chance to adjacent occupied cells.
        for coord in self.environment.occupied_neighbors(*orc.position):
            target = self.environment.get(*coord)
            if target and not target.infected and self.rng.random() < self.settings.virus_spread_chance:
                target.infect(self.settings.virus_duration)
        if orc.infection_timer <= 0:
            orc.infected = False
            orc.infection_timer = 0

    def _overpop_kill_check(self, orc: Orc) -> bool:
        limit = self.settings.max_population
        if limit <= 0:
            return False
        current = len(self.population)
        if current <= limit:
            return False
        overload = (current - limit) / limit
        chance = min(0.75, self.settings.overpop_base + overload * self.settings.overpop_scale)
        if self.rng.random() < chance:
            self._remove_orc(orc)
            return True
        return False

    def _is_dead(self, orc: Orc) -> bool:
        return orc.energy <= 0 or orc.age > self.settings.max_age

    def _remove_orc(self, orc: Orc) -> None:
        self.environment.remove(orc)
        self.population.pop(orc.id, None)

    def _maybe_reproduce(self, orc: Orc) -> bool:
        pop_kind = self._kind_count(orc.kind)
        endangered = pop_kind <= self.settings.endangered_threshold
        threshold = self.settings.reproduction_threshold
        chance = self.settings.reproduction_chance
        if endangered:
            threshold *= self.settings.endangered_repro_factor
            chance = min(1.0, chance + self.settings.endangered_repro_bonus)
        # Si la poblacion total es alta, baja la probabilidad.
        if len(self.population) >= self.settings.reproduction_overpop_pop_threshold:
            chance *= self.settings.reproduction_overpop_factor

        if (orc.energy < threshold) or (self.rng.random() > chance):
            return False
        # Requiere al menos un aliado adyacente para reproducirse.
        ally_adjacent = any(
            (neighbor := self.environment.get(*coord)) and neighbor.kind == orc.kind
            for coord in self.environment.occupied_neighbors(*orc.position)
        )
        if not ally_adjacent:
            return False
        empties = self.environment.empty_neighbors(*orc.position)
        if not empties:
            return False
        dest = self.rng.choice(empties)
        energy_for_child = max(
            2.0,
            min(self.settings.base_energy, orc.energy * self.settings.reproduction_energy_share),
        )
        child = orc.clone_with_mutation(
            rng=self.rng,
            mutation_rate=self.settings.mutation_rate,
            mutation_scale=self.settings.mutation_scale,
            next_id=self._next_id,
        )
        self._next_id += 1
        child.energy = energy_for_child
        self.population[child.id] = child
        self.environment.place(child, *dest)
        orc.adjust_energy(-energy_for_child)
        return True

    def _take_action(self, orc: Orc) -> None:
        occupied = self.environment.occupied_neighbors(*orc.position)
        empties = self.environment.empty_neighbors(*orc.position)
        fertility_here = self.environment.fertility_at(*orc.position)
        low_energy = orc.energy < self.settings.rest_threshold

        if low_energy and self.rng.random() < 0.55:
            self._forage(orc, fertility_here)
            return

        target_coord = self._pick_target(orc, occupied)
        if target_coord:
            target = self.environment.get(*target_coord)
            if target and self._should_attack(orc, target):
                self._resolve_fight(orc, target)
                return

        if empties:
            dest = self._choose_move_target(orc, empties)
            self.environment.move(orc, dest)
            orc.adjust_energy(-self.settings.move_cost)
            if orc.energy < self.settings.rest_threshold and self.rng.random() < 0.35:
                fertility_moved = self.environment.fertility_at(*dest)
                self._forage(orc, fertility_moved)
            return

        if self.rng.random() < 0.4:
            self._forage(orc, fertility_here)

    def _resolve_fight(self, challenger: Orc, defender: Orc) -> None:
        if defender.id not in self.population or challenger.id not in self.population:
            return
        # Both lose a bit of energy just by engaging.
        challenger.adjust_energy(-self.settings.fight_cost * 0.5)
        defender.adjust_energy(-self.settings.fight_cost * 0.5)
        if challenger.energy <= 0:
            self._remove_orc(challenger)
            return
        if defender.energy <= 0:
            self._remove_orc(defender)
            return

        support_challenger = self._local_support_score(challenger)
        support_defender = self._local_support_score(defender)
        challenge_score = self._effective_fitness(challenger) + self.rng.uniform(-0.4, 0.4) + support_challenger
        defense_score = self._effective_fitness(defender) + self.rng.uniform(-0.4, 0.4) + support_defender
        diff = abs(challenge_score - defense_score)
        winner, loser = (challenger, defender) if challenge_score >= defense_score else (defender, challenger)

        if diff < self.settings.skirmish_threshold:
            # Skirmish: both retreat hurt, no death unless they were already exhausted.
            challenger.adjust_energy(-self.settings.fight_cost * self.settings.skirmish_cost_factor)
            defender.adjust_energy(-self.settings.fight_cost * self.settings.skirmish_cost_factor)
            winner.adjust_energy(self.settings.fight_reward * 0.4)
            if challenger.energy <= 0:
                self._remove_orc(challenger)
            if defender.energy <= 0:
                self._remove_orc(defender)
            return

        self._remove_orc(loser)
        winner.adjust_energy(self.settings.fight_reward - self.settings.fight_cost * 0.5)
        winner.strength += 0.05
        winner.resilience += 0.03
        if winner.energy <= 0:
            self._remove_orc(winner)

    def _forage(self, orc: Orc, fertility: float) -> None:
        gain = self.settings.forage_gain * (0.4 + fertility)
        gain *= self.rng.uniform(0.6, 1.2)
        orc.adjust_energy(gain - self.settings.forage_cost)

    def _pick_target(self, orc: Orc, occupied_neighbors) -> Optional[tuple[int, int]]:
        candidates: list[tuple[float, tuple[int, int]]] = []
        for coord in occupied_neighbors:
            target = self.environment.get(*coord)
            if not target:
                continue
            if target.kind == orc.kind:
                continue
            advantage = orc.fitness() - target.fitness()
            energy_gap = (orc.energy - target.energy) * 0.1
            score = advantage + energy_gap
            candidates.append((score, coord))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        best_score, best_coord = candidates[0]
        return best_coord if best_score > -0.3 else None

    def _choose_move_target(self, orc: Orc, empties: list[tuple[int, int]]) -> tuple[int, int]:
        current_score = self._env_score(orc.kind, orc.position)
        target_vec = self._seek_habitat_direction(orc, current_score)
        friends_adjacent = any(
            (neighbor := self.environment.get(*coord)) and neighbor.kind == orc.kind
            for coord in self.environment.occupied_neighbors(*orc.position)
        )
        low_pop = self._kind_count(orc.kind) <= self.settings.endangered_threshold
        low_strength = orc.strength <= self.settings.escape_strength_threshold
        weighted: list[tuple[float, tuple[int, int]]] = []
        for coord in empties:
            base = self._env_score(orc.kind, coord)
            herd_bonus = self._herd_bonus(orc, coord)
            if not friends_adjacent:
                herd_bonus *= self.settings.pair_seek_multiplier
            threat_penalty = 0.0
            if low_pop and low_strength:
                threat_penalty = self._threat_penalty(orc, coord)
            desirability = base + herd_bonus - threat_penalty
            if target_vec:
                vx, vy = target_vec
                dx, dy = coord[0] - orc.position[0], coord[1] - orc.position[1]
                dot = dx * vx + dy * vy
                norm = max(1e-3, (dx * dx + dy * dy) ** 0.5 * (vx * vx + vy * vy) ** 0.5)
                align = max(0.0, dot / norm)
                desirability += self.settings.habitat_seek_bonus * align
            if current_score < self.settings.habitat_bad_threshold:
                desirability += (base - current_score) * 0.8
            desirability += self.rng.uniform(-0.1, 0.1)
            weighted.append((desirability, coord))
        weighted.sort(key=lambda item: item[0], reverse=True)
        top = weighted[: min(3, len(weighted))]
        return self.rng.choice(top)[1]

    def _should_attack(self, challenger: Orc, defender: Orc) -> bool:
        advantage = challenger.fitness() - defender.fitness()
        if challenger.kind == defender.kind:
            return False
        if advantage < -0.6:
            return False
        # Avoid exterminating endangered populations.
        if self._kind_count(defender.kind) <= self.settings.endangered_threshold:
            return False
        # Protect small populations: if attacker group is small, avoid risky fights.
        if self._kind_count(challenger.kind) <= self.settings.peace_floor_count:
            return False
        aggression = self.settings.aggression_bias + advantage * 0.1
        energy_edge = challenger.energy - defender.energy
        if energy_edge > 2:
            aggression += 0.1
        return self.rng.random() < aggression

    def _herd_bonus(self, orc: Orc, coord: tuple[int, int]) -> float:
        radius = self.settings.herd_radius
        if radius <= 0:
            return 0.0
        ox, oy = coord
        total = 0
        for y in range(max(0, oy - radius), min(self.environment.height, oy + radius + 1)):
            for x in range(max(0, ox - radius), min(self.environment.width, ox + radius + 1)):
                neighbor = self.environment.get(x, y)
                if neighbor and neighbor.kind == orc.kind:
                    total += 1
        return total * (self.settings.herd_attraction / max(1, radius * radius))

    def _biome_effect(self, kind: int, biome: int) -> tuple[float, float]:
        # Simple cycle: biome 0 favorece clase 0, penaliza 1; biome 1 favorece 1, penaliza 2; biome 2 favorece 2, penaliza 0.
        if biome == kind:
            return (self.settings.biome_bonus, 0.0)
        if (biome + 1) % 3 == kind:
            return (0.0, 0.0)  # neutral
        return (0.0, self.settings.biome_penalty)

    def _biome_move_bonus(self, kind: int, biome: int) -> float:
        bonus, penalty = self._biome_effect(kind, biome)
        return bonus * 1.0 - penalty * 0.7

    def _virus_spawn_chance(self, orc: Orc) -> float:
        # Mayor probabilidad cuando esta en un bioma que lo penaliza.
        biome = self.environment.biome_at(*orc.position)
        _bonus, penalty = self._biome_effect(orc.kind, biome)
        base = self.settings.virus_spawn_stressed if penalty > 0 else self.settings.virus_spawn_base
        # Si hay mucha poblacion y esta rodeado de su clase, aumenta el riesgo.
        if len(self.population) >= self.settings.virus_crowd_pop_threshold:
            friends, _ = self._social_counts(orc)
            if friends >= self.settings.virus_crowd_threshold:
                base *= self.settings.virus_crowd_multiplier
        return base

    def _env_score(self, kind: int, coord: tuple[int, int]) -> float:
        humidity = self.environment.humidity_at(*coord)
        fertility = self.environment.fertility_at(*coord)
        biome = self.environment.biome_at(*coord)
        score = humidity * 0.35 + fertility * 0.5
        score += self._biome_move_bonus(kind, biome)
        return score

    def _seek_habitat_direction(self, orc: Orc, current_score: float) -> Optional[tuple[float, float]]:
        radius = self.settings.habitat_seek_radius
        if radius <= 0:
            return None
        best_score = current_score
        best_coord: Optional[tuple[int, int]] = None
        ox, oy = orc.position
        for y in range(max(0, oy - radius), min(self.environment.height, oy + radius + 1)):
            for x in range(max(0, ox - radius), min(self.environment.width, ox + radius + 1)):
                score = self._env_score(orc.kind, (x, y))
                if score > best_score + 0.05:
                    best_score = score
                    best_coord = (x, y)
        if best_coord is None:
            return None
        dx = best_coord[0] - ox
        dy = best_coord[1] - oy
        return (dx, dy)

    def _kind_count(self, kind: int) -> int:
        return sum(1 for o in self.population.values() if o.kind == kind)

    def _social_counts(self, orc: Orc) -> tuple[int, int]:
        radius = self.settings.group_support_radius
        x0, y0 = orc.position
        friends = 0
        foes = 0
        for y in range(max(0, y0 - radius), min(self.environment.height, y0 + radius + 1)):
            for x in range(max(0, x0 - radius), min(self.environment.width, x0 + radius + 1)):
                if x == x0 and y == y0:
                    continue
                other = self.environment.get(x, y)
                if not other:
                    continue
                if other.kind == orc.kind:
                    friends += 1
                else:
                    foes += 1
        return friends, foes

    def _local_support_score(self, orc: Orc) -> float:
        friends, foes = self._social_counts(orc)
        net = friends - foes * 0.6
        return net * self.settings.support_score_factor

    def _threat_penalty(self, orc: Orc, coord: tuple[int, int]) -> float:
        radius = self.settings.escape_threat_radius
        if radius <= 0:
            return 0.0
        ox, oy = coord
        enemies = 0
        for y in range(max(0, oy - radius), min(self.environment.height, oy + radius + 1)):
            for x in range(max(0, ox - radius), min(self.environment.width, ox + radius + 1)):
                if x == ox and y == oy:
                    continue
                other = self.environment.get(x, y)
                if other and other.kind != orc.kind:
                    enemies += 1
        return enemies * self.settings.escape_threat_weight

    def _effective_fitness(self, orc: Orc) -> float:
        fitness = orc.fitness()
        if orc.infected:
            fitness *= max(0.2, 1.0 - self.settings.virus_fight_penalty)
        return fitness

    def _apply_kind_modifiers(self, orc: Orc) -> None:
        idx = orc.kind % max(1, len(self.settings.kind_strength_mods))
        strength_mod = self.settings.kind_strength_mods[idx]
        agility_mod = self.settings.kind_agility_mods[idx]
        resilience_mod = self.settings.kind_resilience_mods[idx]
        orc.strength *= strength_mod
        orc.agility *= agility_mod
        orc.resilience *= resilience_mod

    def _kind_for_biome(self, biome: int) -> int:
        return biome % max(1, self.settings.classes)

    def metrics(self) -> SimulationMetrics:
        pop = list(self.population.values())
        count = len(pop)
        if count == 0:
            return SimulationMetrics(
                tick=self.tick,
                population=0,
                average_strength=0.0,
                average_agility=0.0,
                average_resilience=0.0,
            )
        return SimulationMetrics(
            tick=self.tick,
            population=count,
            average_strength=sum(o.strength for o in pop) / count,
            average_agility=sum(o.agility for o in pop) / count,
            average_resilience=sum(o.resilience for o in pop) / count,
        )

    def orcs(self) -> Iterable[Orc]:
        return self.population.values()

    def counts_by_kind(self) -> list[int]:
        counts = [0 for _ in range(max(1, self.settings.classes))]
        for orc in self.population.values():
            idx = orc.kind % len(counts)
            counts[idx] += 1
        return counts

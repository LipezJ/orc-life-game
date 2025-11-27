from __future__ import annotations

import random
from importlib import resources
from pathlib import Path
from typing import List, Optional

import pygame

from ..config import SimulationSettings
from ..simulation import Simulation
from .colors import DEEP_BG, GRID, HUD, blend_biome, color_for_cell, color_for_humidity, color_for_orc

INFECTION_GLOW = (170, 90, 210, 80)


class PygameRenderer:
    def __init__(self, settings: SimulationSettings) -> None:
        pygame.init()
        pygame.font.init()
        self.settings = settings
        self.cell_size = settings.cell_size
        self.width_px = settings.grid_width * self.cell_size
        self.height_px = settings.grid_height * self.cell_size
        self.screen = pygame.display.set_mode((self.width_px, self.height_px))
        pygame.display.set_caption("Orcos - Automata Celular")
        self.font = pygame.font.SysFont("consolas", 16)
        self.running = True
        self._noise_rng = random.Random(42)
        self.sprites = self._load_sprites()

    def handle_events(self) -> dict:
        events: dict = {"quit": False, "toggle_pause": False, "reset": False}
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                events["quit"] = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    events["quit"] = True
                if event.key == pygame.K_SPACE:
                    events["toggle_pause"] = True
                if event.key == pygame.K_r:
                    events["reset"] = True
        return events

    def draw(self, simulation: Simulation, paused: bool) -> None:
        self.screen.fill(DEEP_BG)
        self._draw_environment(simulation)
        self._draw_grid()
        self._draw_orcs(simulation)
        self._draw_hud(simulation, paused)
        pygame.display.flip()

    def _load_sprites(self) -> List[pygame.Surface]:
        names = ("orc1.png", "orc2.png", "orc3.png")
        sprites: list[pygame.Surface] = []
        for name in names:
            surface = self._load_resource_sprite(name)
            if surface is None:
                surface = self._load_fs_sprite(name)
            if surface is not None:
                sprites.append(surface)
        if not sprites:
            fallback = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            fallback.fill((200, 80, 80))
            sprites.append(fallback)
        if len(sprites) >= 2:
            sprites[1] = self._tint_sprite(sprites[1], (255, 240, 150))
        return sprites

    def _load_resource_sprite(self, filename: str) -> Optional[pygame.Surface]:
        try:
            data_ref = resources.files("orc_automata.assets") / filename
        except (FileNotFoundError, ModuleNotFoundError):
            return None
        if not data_ref.is_file():
            return None
        with resources.as_file(data_ref) as path:
            return self._scaled_sprite(Path(path))

    def _load_fs_sprite(self, filename: str) -> Optional[pygame.Surface]:
        root = Path(__file__).resolve().parents[3]
        path = root / "assets" / filename
        if not path.exists():
            return None
        return self._scaled_sprite(path)

    def _scaled_sprite(self, path: Path) -> pygame.Surface:
        sprite = pygame.image.load(str(path)).convert_alpha()
        # The provided files are sprite sheets with 5 frames in a row; take only the first frame.
        frames = 5
        frame_width = max(1, sprite.get_width() // frames)
        frame_rect = pygame.Rect(0, 0, frame_width, sprite.get_height())
        first_frame = sprite.subsurface(frame_rect).copy()
        size = max(1, int(self.cell_size * 1.3))
        scaled = pygame.transform.smoothscale(first_frame, (size, size))
        return scaled

    def _draw_environment(self, simulation: Simulation) -> None:
        for y in range(self.settings.grid_height):
            for x in range(self.settings.grid_width):
                humidity = simulation.environment.humidity_at(x, y)
                biome = simulation.environment.biome_at(x, y)
                color = blend_biome(color_for_cell(biome, humidity), biome, strength=0.08)
                rect = pygame.Rect(
                    x * self.cell_size,
                    y * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                self.screen.fill(color, rect)
                self._draw_cell_noise(x, y, biome)

    def _draw_grid(self) -> None:
        for x in range(0, self.width_px, self.cell_size):
            pygame.draw.line(self.screen, GRID, (x, 0), (x, self.height_px), 1)
        for y in range(0, self.height_px, self.cell_size):
            pygame.draw.line(self.screen, GRID, (0, y), (self.width_px, y), 1)

    def _draw_orcs(self, simulation: Simulation) -> None:
        for orc in simulation.orcs():
            x, y = orc.position
            cell_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            if orc.infected:
                self._draw_infection_overlay(cell_surface)
            sprite = self._sprite_for_orc(orc)
            if sprite is not None:
                rect = sprite.get_rect()
                rect.center = (self.cell_size // 2, self.cell_size // 2)
                cell_surface.blit(sprite, rect)
            else:
                rect = pygame.Rect(0, 0, self.cell_size, self.cell_size)
                pygame.draw.rect(cell_surface, color_for_orc(orc), rect)
            self.screen.blit(cell_surface, (x * self.cell_size, y * self.cell_size))

    def _draw_hud(self, simulation: Simulation, paused: bool) -> None:
        metrics = simulation.metrics()
        counts = simulation.counts_by_kind()
        counts_text = " | ".join(f"C{idx}:{c}" for idx, c in enumerate(counts))
        lines = [
            f"Tick: {metrics.tick} {'(pausa)' if paused else ''}",
            f"Poblacion: {metrics.population}",
            f"Razas: {counts_text}",
            f"Fuerza promedio: {metrics.average_strength:.2f}",
            f"Agilidad promedio: {metrics.average_agility:.2f}",
            f"Resistencia promedio: {metrics.average_resilience:.2f}",
            "Teclas: Space pausa | R reinicia | Esc salir",
        ]
        padding = 6
        for idx, text in enumerate(lines):
            surface = self.font.render(text, True, HUD)
            self.screen.blit(surface, (padding, padding + idx * 18))

    def _sprite_for_orc(self, orc) -> Optional[pygame.Surface]:
        if not self.sprites:
            return None
        return self.sprites[orc.kind % len(self.sprites)]

    def _draw_cell_noise(self, x: int, y: int, biome: int) -> None:
        rng = random.Random((x * 73856093) ^ (y * 19349663) ^ (biome * 83492791))
        overlay = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        blotches = rng.randint(3, 6)
        for _ in range(blotches):
            r = max(2, self.cell_size // 6 + rng.randint(-1, 1))
            cx = rng.randint(r, self.cell_size - r)
            cy = rng.randint(r, self.cell_size - r)
            alpha = rng.randint(40, 70)
            # Subtle darker blotches per biome.
            blot_color = blend_biome(color_for_humidity(0.5), biome, strength=0.25)
            color = (blot_color[0], blot_color[1], blot_color[2], alpha)
            pygame.draw.circle(overlay, color, (cx, cy), r)
        self.screen.blit(overlay, (x * self.cell_size, y * self.cell_size))

    def _tint_sprite(self, sprite: pygame.Surface, rgb: tuple[int, int, int]) -> pygame.Surface:
        tinted = sprite.copy()
        tinted.fill(rgb + (0,), special_flags=pygame.BLEND_RGB_MULT)
        tinted.fill((15, 12, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return tinted

    def _draw_infection_overlay(self, surface: pygame.Surface) -> None:
        radius = max(3, self.cell_size // 2)
        center = (self.cell_size // 2, self.cell_size // 2)
        halo = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(halo, INFECTION_GLOW, center, radius)
        # Halo se queda debajo porque luego se dibuja el sprite encima en la misma surface.
        surface.blit(halo, (0, 0))

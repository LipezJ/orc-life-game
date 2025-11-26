from __future__ import annotations

import pygame

from .config import DEFAULT_SETTINGS, SimulationSettings
from .rendering.pygame_renderer import PygameRenderer
from .simulation import Simulation


def run_loop(settings: SimulationSettings) -> None:
    simulation = Simulation(settings=settings)
    renderer = PygameRenderer(settings=settings)
    clock = pygame.time.Clock()
    paused = False
    while renderer.running:
        actions = renderer.handle_events()
        if actions["quit"]:
            break
        if actions["toggle_pause"]:
            paused = not paused
        if actions["reset"]:
            simulation.reset()
        if not paused:
            simulation.step()
        renderer.draw(simulation, paused)
        clock.tick(settings.tick_rate)
    pygame.quit()


def main() -> None:
    run_loop(DEFAULT_SETTINGS)


if __name__ == "__main__":
    main()

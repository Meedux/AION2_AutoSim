"""main.py
Simple runner for the AION autoplay simulation (boilerplate).
"""
from __future__ import annotations
import time
from logger import configure_logging, get_logger
from player import sample_player
from map import sample_map
from autoplay import AutoPlayController, AIState


logger = get_logger(__name__)


def run_simulation(ticks: int = 10, tick_delay: float = 0.5) -> None:
    configure_logging()
    player = sample_player()
    grid = sample_map()
    autoplay = AutoPlayController(player, grid)

    logger.info("Starting simulation for %d ticks", ticks)
    for t in range(ticks):
        logger.debug("Tick %d", t)
        autoplay.tick()
        time.sleep(tick_delay)

    logger.info("Simulation complete. Inventory: %s", player.inventory)


if __name__ == "__main__":
    run_simulation()

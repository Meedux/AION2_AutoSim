"""pathfinding.py
Simple A* implementation for grid movement between integer coordinates.

This pathfinder assumes an open grid (no obstacles). It's easy to extend
by adding an `is_walkable(pos)` callback if you add obstacles later.
"""
from __future__ import annotations
from typing import Tuple, List, Set, Dict, Optional
import heapq

Position = Tuple[int, int]


def manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors(pos: Position) -> List[Position]:
    x, y = pos
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def astar(width: int, height: int, start: Position, goal: Position) -> Optional[List[Position]]:
    """Compute path from start to goal on an empty grid of given size.

    Returns a list of positions including start and goal, or None if goal out of bounds.
    """
    if not (0 <= goal[0] < width and 0 <= goal[1] < height):
        return None

    open_set: List[Tuple[int, Position]] = []
    heapq.heappush(open_set, (0, start))
    came_from: Dict[Position, Optional[Position]] = {start: None}
    g_score: Dict[Position, int] = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            # reconstruct path
            path: List[Position] = []
            p = current
            while p is not None:
                path.append(p)
                p = came_from.get(p)
            return list(reversed(path))

        for n in neighbors(current):
            x, y = n
            if not (0 <= x < width and 0 <= y < height):
                continue
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(n, 1_000_000):
                came_from[n] = current
                g_score[n] = tentative_g
                f = tentative_g + manhattan(n, goal)
                heapq.heappush(open_set, (f, n))

    return None

"""Tetromino shapes, SRS kick tables, rotation math and the Piece class."""

from py_tetris.constants import COLS
from py_tetris.constants import Color

SHAPES: dict[str, list[tuple[int, int]]] = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}

BOX: dict[str, int] = {"I": 4, "O": 2, "T": 3, "S": 3, "Z": 3, "J": 3, "L": 3}

COLORS: dict[str, Color] = {
    "I": (0, 190, 255),
    "O": (250, 200, 0),
    "T": (170, 60, 255),
    "S": (60, 210, 60),
    "Z": (240, 60, 60),
    "J": (70, 100, 255),
    "L": (255, 130, 30),
}

# SRS wall kicks: (from_state, to_state) -> candidate (dx, dy) offsets.
# +dy is down, matching board coordinates.
JLSTZ_KICKS: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {
    (0, 1): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (1, 0): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (1, 2): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (2, 1): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (2, 3): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (3, 2): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (3, 0): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (0, 3): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
}

I_KICKS: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {
    (0, 1): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (1, 0): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (1, 2): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
    (2, 1): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (2, 3): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (3, 2): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (3, 0): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (0, 3): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
}


def rotate_cells(
    cells: frozenset[tuple[int, int]], direction: int, size: int
) -> frozenset[tuple[int, int]]:
    if direction >= 0:
        return frozenset((size - 1 - y, x) for x, y in cells)
    return frozenset((y, size - 1 - x) for x, y in cells)


class Piece:
    def __init__(self, kind: str) -> None:
        self.kind: str = kind
        self.cells: frozenset[tuple[int, int]] = frozenset(SHAPES[kind])
        self.x: int = (COLS - BOX[kind]) // 2
        self.y: int = 0
        self.state: int = 0  # SRS rotation state: 0 spawn, 1 R, 2 180, 3 L

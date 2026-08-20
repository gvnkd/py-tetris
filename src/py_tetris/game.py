"""Game state: board, 7-bag, SRS rotation, lock delay, hold, scoring."""

import random

from py_tetris.constants import (
    BOT_THINK_INTERVAL,
    COLS,
    LOCK_DELAY,
    MAX_LOCK_RESETS,
    ROWS,
    SCORE_TABLE,
)
from py_tetris.constants import Color
from py_tetris.highscore import load_highscore
from py_tetris.pieces import BOX, COLORS, I_KICKS, JLSTZ_KICKS, Piece, SHAPES, rotate_cells


class Game:
    board: list[list[Color | None]]
    bag: list[str]
    score: int
    lines: int
    level: int
    over: bool
    paused: bool
    mode: str  # "demo" (bot plays) or "human"
    next_kind: str
    piece: Piece | None
    drop_timer: float
    lock_timer: float
    lock_resets: int
    last_cleared: int
    held_kind: str | None
    can_hold: bool
    highscore: int

    def __init__(self, mode: str = "human", highscore: int | None = None) -> None:
        self.mode = mode
        self.highscore = load_highscore() if highscore is None else highscore
        self.reset()

    def reset(self) -> None:
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.score = 0
        self.lines = 0
        self.level = 1
        self.over = False
        self.paused = False
        self.held_kind = None
        self.can_hold = True
        self.next_kind = self._draw_kind()
        self.piece = None
        self.drop_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        self.last_cleared = 0
        self.spawn()

    def _draw_kind(self) -> str:
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    @property
    def drop_delay(self) -> float:
        return max(0.08, 0.60 - (self.level - 1) * 0.05)

    def grounded(self) -> bool:
        p = self.piece
        return p is not None and self.collides(p.cells, p.x, p.y + 1)

    def collides(self, cells: frozenset[tuple[int, int]], ox: int, oy: int) -> bool:
        for cx, cy in cells:
            x, y = ox + cx, oy + cy
            if x < 0 or x >= COLS or y >= ROWS:
                return True
            if y >= 0 and self.board[y][x] is not None:
                return True
        return False

    def spawn(self, allow_hold: bool = True) -> None:
        self.piece = Piece(self.next_kind)
        self.next_kind = self._draw_kind()
        self.can_hold = allow_hold
        self.drop_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        if self.collides(self.piece.cells, self.piece.x, self.piece.y):
            self.over = True

    def spawn_held(self, kind: str) -> None:
        self.piece = Piece(kind)
        self.can_hold = False
        self.drop_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        if self.collides(self.piece.cells, self.piece.x, self.piece.y):
            self.over = True

    def move(self, dx: int, dy: int) -> bool:
        p = self.piece
        if p is not None and not self.collides(p.cells, p.x + dx, p.y + dy):
            p.x += dx
            p.y += dy
            if dy == 1:
                self.can_hold = True
            if self.grounded() and self.lock_resets < MAX_LOCK_RESETS:
                self.lock_resets += 1
                self.lock_timer = 0.0
            return True
        return False

    def rotate(self, direction: int = 1) -> bool:
        p = self.piece
        if p is None:
            return False
        new_cells = rotate_cells(p.cells, direction, BOX[p.kind])
        kicks = ((0, 0),) if p.kind == "O" else self._srs_kicks(direction)
        for kx, ky in kicks:
            if not self.collides(new_cells, p.x + kx, p.y + ky):
                p.cells = new_cells
                p.x += kx
                p.y += ky
                if p.kind != "O":
                    p.state = (p.state + direction) % 4
                if self.grounded() and self.lock_resets < MAX_LOCK_RESETS:
                    self.lock_resets += 1
                    self.lock_timer = 0.0
                return True
        return False

    def _srs_kicks(self, direction: int) -> tuple[tuple[int, int], ...]:
        p = self.piece
        assert p is not None
        table = I_KICKS if p.kind == "I" else JLSTZ_KICKS
        return table[(p.state, (p.state + direction) % 4)]

    def hold(self) -> None:
        p = self.piece
        if p is None or not self.can_hold or self.over:
            return
        if self.held_kind is None:
            self.held_kind = p.kind
            self.spawn(allow_hold=False)
        else:
            saved = self.held_kind
            self.held_kind = p.kind
            self.spawn_held(saved)

    def drop_distance(self) -> int:
        p = self.piece
        if p is None:
            return 0
        d = 0
        while not self.collides(p.cells, p.x, p.y + d + 1):
            d += 1
        return d

    def soft_drop(self) -> None:
        if self.move(0, 1):
            self.score += 1
            self.can_hold = True
        else:
            self.lock()

    def hard_drop(self) -> None:
        p = self.piece
        if p is None:
            return
        d = self.drop_distance()
        p.y += d
        self.score += 2 * d
        self.lock()

    def lock(self) -> int:
        p = self.piece
        if p is None:
            return 0
        color = COLORS[p.kind]
        for cx, cy in p.cells:
            x, y = p.x + cx, p.y + cy
            if 0 <= x < COLS and 0 <= y < ROWS:
                self.board[y][x] = color
        cleared = self._clear_lines()
        self.last_cleared = cleared
        if self.score > self.highscore:
            self.highscore = self.score
        self.spawn()
        return cleared

    def _clear_lines(self) -> int:
        kept = [row for row in self.board if any(c is None for c in row)]
        cleared = ROWS - len(kept)
        if cleared:
            fresh: list[list[Color | None]] = [[None] * COLS for _ in range(cleared)]
            self.board = fresh + kept
            self.lines += cleared
            self.level = self.lines // 10 + 1
            self.score += SCORE_TABLE[cleared] * self.level
        return cleared

    def update(self, dt: float) -> None:
        if self.over or self.paused or self.piece is None:
            return
        if self.grounded():
            self.drop_timer = 0.0
            self.lock_timer += dt / 1000.0
            if self.lock_timer >= LOCK_DELAY:
                self.lock()
                if self.over:
                    return
        else:
            self.lock_timer = 0.0
            self.drop_timer += dt / 1000.0
            while self.drop_timer >= self.drop_delay:
                self.drop_timer -= self.drop_delay
                if not self.move(0, 1):
                    break


def evaluate_placement(
    board: list[list[Color | None]], cells: frozenset[tuple[int, int]], x: int, y: int
) -> int:
    """Score a placement (higher is better) after locking and clearing lines."""
    placed = [row[:] for row in board]
    for cx, cy in cells:
        bx, by = x + cx, y + cy
        if 0 <= bx < COLS and 0 <= by < ROWS:
            placed[by][bx] = (0, 0, 0)
    kept = [row for row in placed if any(c is None for c in row)]
    cleared = ROWS - len(kept)
    fresh: list[list[Color | None]] = [[None] * COLS for _ in range(cleared)]
    final = fresh + kept
    heights = [0] * COLS
    holes = 0
    for col in range(COLS):
        seen = False
        for row in range(ROWS):
            if final[row][col] is None:
                if seen:
                    holes += 1
            else:
                if not seen:
                    heights[col] = ROWS - row
                seen = True
    bumpiness = sum(abs(heights[i] - heights[i + 1]) for i in range(COLS - 1))
    return cleared * 1000 - holes * 30 - sum(heights) * 2 - bumpiness


class Bot:
    """Plays demo mode: picks the best legal placement, then executes it."""

    def __init__(self) -> None:
        self.think_timer: float = 0.0

    def step(self, game: Game, dt: float) -> None:
        if game.mode != "demo" or game.over or game.paused:
            self.think_timer = 0.0
            return
        self.think_timer += dt / 1000.0
        if self.think_timer < BOT_THINK_INTERVAL:
            return
        self.think_timer = 0.0
        self.play(game)

    def play(self, game: Game) -> None:
        p = game.piece
        if p is None or game.over:
            return
        best: tuple[int, int, int] | None = None  # (score, rotation, x)
        for rot in range(4):
            cells = frozenset(SHAPES[p.kind])
            for _ in range(rot):
                cells = rotate_cells(cells, 1, BOX[p.kind])
            for x in range(-BOX[p.kind] + 1, COLS):
                if game.collides(cells, x, p.y):
                    continue
                y = p.y
                while not game.collides(cells, x, y + 1):
                    y += 1
                s = evaluate_placement(game.board, cells, x, y)
                if best is None or s > best[0]:
                    best = (s, rot, x)
        if best is None:
            game.hard_drop()
            return
        turns = (best[1] - p.state) % 4
        for _ in range(turns):
            if not game.rotate(1):
                game.hard_drop()
                return
        dx = best[2] - p.x
        for _ in range(abs(dx)):
            if not game.move(1 if dx > 0 else -1, 0):
                game.hard_drop()
                return
        game.hard_drop()

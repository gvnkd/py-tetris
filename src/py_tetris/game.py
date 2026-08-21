"""Game state: board, 7-bag, SRS rotation, lock delay, hold, scoring."""

import random

from py_tetris.constants import (
    B2B_MULTIPLIER,
    BOT_THINK_INTERVAL,
    CLEAR_FLASH_DURATION,
    COMBO_BONUS,
    COLS,
    LOCK_DELAY,
    MAX_LOCK_RESETS,
    ROWS,
    SCORE_TABLE,
    SPRINT_TARGET,
    TSPIN_SCORES,
    ULTRA_LEVEL,
    ULTRA_TIME,
)
from py_tetris.constants import Color
from py_tetris.highscore import load_highscore
from py_tetris.pieces import BOX, COLORS, I_KICKS, JLSTZ_KICKS, Piece, SHAPES, rotate_cells


def collides(board: list[list[Color | None]], cells: frozenset[tuple[int, int]], ox: int, oy: int) -> bool:
    for cx, cy in cells:
        x, y = ox + cx, oy + cy
        if x < 0 or x >= COLS or y >= ROWS:
            return True
        if y >= 0 and board[y][x] is not None:
            return True
    return False


def place_piece(
    board: list[list[Color | None]], cells: frozenset[tuple[int, int]], x: int, y: int
) -> tuple[list[list[Color | None]], int]:
    """Lock cells into the board, clear full rows; return (new board, cleared)."""
    placed = [row[:] for row in board]
    for cx, cy in cells:
        bx, by = x + cx, y + cy
        if 0 <= bx < COLS and 0 <= by < ROWS:
            placed[by][bx] = (0, 0, 0)
    kept = [row for row in placed if any(c is None for c in row)]
    cleared = ROWS - len(kept)
    if cleared:
        fresh: list[list[Color | None]] = [[None] * COLS for _ in range(cleared)]
        return fresh + kept, cleared
    return placed, 0


def evaluate_board(board: list[list[Color | None]]) -> int:
    """Static board score (higher is better), no placement involved."""
    heights = [0] * COLS
    holes = 0
    for col in range(COLS):
        seen = False
        for row in range(ROWS):
            if board[row][col] is None:
                if seen:
                    holes += 1
            else:
                if not seen:
                    heights[col] = ROWS - row
                seen = True
    bumpiness = sum(abs(heights[i] - heights[i + 1]) for i in range(COLS - 1))
    return -holes * 30 - sum(heights) * 2 - bumpiness


def rest_y(board: list[list[Color | None]], cells: frozenset[tuple[int, int]], x: int, y0: int) -> int:
    y = y0
    while not collides(board, cells, x, y + 1):
        y += 1
    return y


class Game:
    board: list[list[Color | None]]
    bag: list[str]
    score: int
    lines: int
    level: int
    over: bool
    paused: bool
    mode: str  # "demo" (bot plays) or "human"
    game_mode: str  # "marathon" | "sprint" | "ultra"
    won: bool
    time_left: float  # seconds remaining (ultra only, 0 otherwise)
    next_kind: str
    piece: Piece | None
    drop_timer: float
    lock_timer: float
    lock_resets: int
    last_cleared: int
    clear_flash: float
    last_tspin: str  # "" | "mini" | "full", consumed by the app for SFX
    combo: int  # consecutive line clears
    b2b_active: bool
    last_action: str  # "" | "move" | "rotate" | "drop"
    held_kind: str | None
    can_hold: bool
    highscore: int

    def __init__(
        self, mode: str = "human", game_mode: str = "marathon", highscore: int | None = None
    ) -> None:
        self.mode = mode
        self.game_mode = game_mode
        self.highscore = load_highscore() if highscore is None else highscore
        self.reset()

    def reset(self) -> None:
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.score = 0
        self.lines = 0
        self.level = ULTRA_LEVEL if self.game_mode == "ultra" else 1
        self.over = False
        self.paused = False
        self.won = False
        self.time_left = ULTRA_TIME if self.game_mode == "ultra" else 0.0
        self.held_kind = None
        self.can_hold = True
        self.next_kind = self._draw_kind()
        self.piece = None
        self.drop_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        self.last_cleared = 0
        self.clear_flash = 0.0
        self.last_tspin = ""
        self.combo = 0
        self.b2b_active = False
        self.last_action = ""
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
        return collides(self.board, cells, ox, oy)

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
            self.last_action = "drop" if dy == 1 else "move"
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
                self.last_action = "rotate"
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
        self.last_action = "drop"
        self.score += 2 * d
        self.lock()

    def _detect_tspin(self, p: Piece) -> str:
        """3-corner rule: T locked by a rotation with 3+ diagonal corners
        blocked; full if both corners on the piece's facing side are blocked."""
        if p.kind != "T" or self.last_action != "rotate":
            return ""
        cx, cy = p.x + 1, p.y + 1  # center of the 3x3 box

        def blocked(x: int, y: int) -> bool:
            if x < 0 or x >= COLS or y >= ROWS:
                return True
            return y >= 0 and self.board[y][x] is not None

        corners = ((cx - 1, cy - 1), (cx + 1, cy - 1), (cx - 1, cy + 1), (cx + 1, cy + 1))
        if sum(blocked(x, y) for x, y in corners) < 3:
            return ""
        front = {
            0: (corners[0], corners[1]),  # facing up
            1: (corners[1], corners[3]),  # facing right
            2: (corners[2], corners[3]),  # facing down
            3: (corners[0], corners[2]),  # facing left
        }[p.state]
        return "full" if all(blocked(x, y) for x, y in front) else "mini"

    def lock(self) -> int:
        p = self.piece
        if p is None:
            return 0
        color = COLORS[p.kind]
        for cx, cy in p.cells:
            x, y = p.x + cx, p.y + cy
            if 0 <= x < COLS and 0 <= y < ROWS:
                self.board[y][x] = color
        tspin = self._detect_tspin(p)
        cleared = self._clear_lines()
        self.last_cleared = cleared
        self.last_tspin = tspin
        self._score_clear(cleared, tspin)
        if cleared:
            self.clear_flash = CLEAR_FLASH_DURATION
        if self.score > self.highscore:
            self.highscore = self.score
        self.spawn()
        return cleared

    def _score_clear(self, cleared: int, tspin: str) -> None:
        if cleared == 0:
            if tspin:  # T-spin with no lines still scores
                self.score += TSPIN_SCORES[tspin][0] * self.level
            else:
                self.combo = 0
            return
        difficult = cleared >= 4 or (tspin != "" and cleared >= 2)
        base = TSPIN_SCORES[tspin][min(cleared, 3)] if tspin else SCORE_TABLE[min(cleared, 4)]
        if difficult and self.b2b_active:
            base = int(base * B2B_MULTIPLIER)
        self.score += base * self.level
        self.b2b_active = difficult
        self.combo += 1
        if self.combo > 1:
            self.score += COMBO_BONUS * (self.combo - 1) * self.level

    def _clear_lines(self) -> int:
        kept = [row for row in self.board if any(c is None for c in row)]
        cleared = ROWS - len(kept)
        if cleared:
            fresh: list[list[Color | None]] = [[None] * COLS for _ in range(cleared)]
            self.board = fresh + kept
            self.lines += cleared
            if self.game_mode == "marathon":
                self.level = self.lines // 10 + 1
            if self.game_mode == "sprint" and self.lines >= SPRINT_TARGET:
                self.over = True
                self.won = True
        return cleared

    def update(self, dt: float) -> None:
        if self.over or self.paused or self.piece is None:
            return
        if self.clear_flash > 0:
            self.clear_flash = max(0.0, self.clear_flash - dt / 1000.0)
        if self.game_mode == "ultra":
            self.time_left = max(0.0, self.time_left - dt / 1000.0)
            if self.time_left == 0.0:
                self.over = True
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
    final, cleared = place_piece(board, cells, x, y)
    return cleared * 1000 + evaluate_board(final)


class Bot:
    """Plays demo mode: depth-2 lookahead over the top-K placements of each
    candidate piece (including hold), then executes the best plan."""

    TOP_K = 8

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

    def _next_kinds(self, game: Game) -> tuple[str, str]:
        """The next two queued kinds without mutating the game."""
        bag = list(game.bag)
        if not bag:
            bag = list(SHAPES)
            random.shuffle(bag)
        return game.next_kind, bag.pop()

    def _candidates(
        self, board: list[list[Color | None]], kind: str, y0: int, limit: int | None
    ) -> list[tuple[int, int, int, int, frozenset[tuple[int, int]]]]:
        """(score, rot, x, rest_y, cells) for every legal placement, best first."""
        n = BOX[kind]
        out: list[tuple[int, int, int, int, frozenset[tuple[int, int]]]] = []
        for rot in range(4):
            cells = frozenset(SHAPES[kind])
            for _ in range(rot):
                cells = rotate_cells(cells, 1, n)
            for x in range(-n + 1, COLS):
                if collides(board, cells, x, y0):
                    continue
                y = rest_y(board, cells, x, y0)
                out.append((evaluate_placement(board, cells, x, y), rot, x, y, cells))
        out.sort(key=lambda t: t[0], reverse=True)
        return out[:limit] if limit else out

    def _best_score(self, board: list[list[Color | None]], kind: str) -> int:
        best = -10**9
        for s, _rot, _x, _y, _cells in self._candidates(board, kind, 0, None):
            best = max(best, s)
        return best

    def play(self, game: Game) -> None:
        p = game.piece
        if p is None or game.over:
            return
        n1, n2 = self._next_kinds(game)
        best_total: int | None = None
        best_plan: tuple[str, int, int] | None = None  # (action, rot, x)

        for s, rot, x, _y, cells in self._candidates(game.board, p.kind, p.y, self.TOP_K):
            sim, _cleared = place_piece(game.board, cells, x, _y)
            total = s + self._best_score(sim, n1)
            if best_total is None or total > best_total:
                best_total, best_plan = total, ("drop", rot, x)

        if game.can_hold:
            hand, after = (n1, n2) if game.held_kind is None else (game.held_kind, n1)
            for s, rot, x, _y, cells in self._candidates(game.board, hand, p.y, self.TOP_K):
                sim, _cleared = place_piece(game.board, cells, x, _y)
                total = s + self._best_score(sim, after)
                if best_total is not None and total > best_total:
                    best_total, best_plan = total, ("hold", rot, x)

        if best_plan is None:
            game.hard_drop()
            return
        if best_plan[0] == "hold":
            game.hold()
        self._execute(game, best_plan[1], best_plan[2])

    def _execute(self, game: Game, rot: int, x: int) -> None:
        p = game.piece
        if p is None or game.over:
            return
        for _ in range((rot - p.state) % 4):
            if not game.rotate(1):
                game.hard_drop()
                return
        dx = x - p.x
        for _ in range(abs(dx)):
            if not game.move(1 if dx > 0 else -1, 0):
                game.hard_drop()
                return
        game.hard_drop()

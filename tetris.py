"""Tetris in a single file, powered by pygame.

Controls:
    Left / Right      move
    Down              soft drop
    Up / X            rotate clockwise
    Z                 rotate counter-clockwise
    Space             hard drop
    C                 hold piece
    M                 mute / unmute sounds
    P                 pause
    R                 restart (after game over)
    Q                 quit
"""

import math
import os
import random
import struct
import sys
from dataclasses import dataclass

import pygame

Color = tuple[int, int, int]

COLS = 10
ROWS = 20
CELL = 30
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
SIDEBAR_W = 210
WIDTH = BOARD_W + SIDEBAR_W
HEIGHT = BOARD_H
FPS = 60
LOCK_DELAY = 0.5  # seconds a grounded piece may slide/rotate before locking
MAX_LOCK_RESETS = 15  # move/rotate resets per grounded spell (stops infinite spin)
BOT_THINK_INTERVAL = 0.3  # seconds between bot decisions
DEMO_RESTART_DELAY = 2.0  # seconds the demo shows game over before restarting

SIDEBAR_X = BOARD_W + 15
SIDEBAR_INNER_W = SIDEBAR_W - 30
NEW_GAME_RECT = pygame.Rect(SIDEBAR_X, 548, SIDEBAR_INNER_W, 42)

BG: Color = (16, 16, 22)
PANEL: Color = (24, 24, 34)
GRID: Color = (36, 36, 50)
BORDER: Color = (80, 80, 105)
WHITE: Color = (235, 235, 240)
DIM: Color = (140, 140, 160)
GHOST: Color = (95, 95, 120)

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

SCORE_TABLE: dict[int, int] = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}

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


def shade(color: Color, amount: int) -> Color:
    r, g, b = color
    return (
        max(0, min(255, r + amount)),
        max(0, min(255, g + amount)),
        max(0, min(255, b + amount)),
    )


def highscore_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME", "")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "py-tetris", "highscore")


def load_highscore() -> int:
    try:
        with open(highscore_path(), encoding="utf-8") as f:
            return max(0, int(f.read().strip() or 0))
    except (OSError, ValueError):
        return 0


def save_highscore(score: int) -> None:
    if score <= 0:
        return
    path = highscore_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{score}\n")
    except OSError:
        pass


def _tone(freq: float, ms: int, vol: float, rate: int = 22050) -> bytes:
    """Render a simple sine tone (with linear fade-out) to 16-bit mono PCM."""
    n = max(1, int(rate * ms / 1000))
    out = bytearray()
    amp = 32767.0 * vol
    for i in range(n):
        v = math.sin(2.0 * math.pi * freq * i / rate)
        v *= (n - i) / n
        out += struct.pack("<h", int(amp * v))
    return bytes(out)


class Piece:
    def __init__(self, kind: str) -> None:
        self.kind: str = kind
        self.cells: frozenset[tuple[int, int]] = frozenset(SHAPES[kind])
        self.x: int = (COLS - BOX[kind]) // 2
        self.y: int = 0
        self.state: int = 0  # SRS rotation state: 0 spawn, 1 R, 2 180, 3 L


@dataclass
class Sounds:
    enabled: bool = True
    move: pygame.mixer.Sound | None = None
    rotate: pygame.mixer.Sound | None = None
    drop: pygame.mixer.Sound | None = None
    hard: pygame.mixer.Sound | None = None
    clear: pygame.mixer.Sound | None = None
    tetris: pygame.mixer.Sound | None = None
    over: pygame.mixer.Sound | None = None

    @classmethod
    def build(cls) -> "Sounds":
        s = cls()
        if not pygame.mixer.get_init():
            return s
        try:
            fmt = pygame.mixer.get_init()
            rate = fmt[0] if fmt and fmt[0] else 22050
            s.move = pygame.mixer.Sound(buffer=_tone(240, 45, 0.3, rate))
            s.rotate = pygame.mixer.Sound(buffer=_tone(440, 60, 0.35, rate))
            s.drop = pygame.mixer.Sound(buffer=_tone(180, 50, 0.35, rate))
            s.hard = pygame.mixer.Sound(buffer=_tone(90, 120, 0.5, rate))
            s.clear = pygame.mixer.Sound(buffer=_tone(660, 130, 0.5, rate))
            s.tetris = pygame.mixer.Sound(buffer=_tone(880, 220, 0.55, rate))
            s.over = pygame.mixer.Sound(buffer=_tone(110, 700, 0.5, rate))
        except pygame.error:
            pass
        return s

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        snd = getattr(self, name, None)
        if snd is not None:
            snd.play()


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


def draw_cell(
    surf: pygame.Surface, x: int, y: int, color: Color, size: int = CELL
) -> None:
    rect = pygame.Rect(x * size, y * size, size, size)
    pygame.draw.rect(surf, color, rect)
    hi = shade(color, 55)
    lo = shade(color, -55)
    pygame.draw.line(surf, hi, (rect.x + 2, rect.y + 2), (rect.right - 3, rect.y + 2))
    pygame.draw.line(surf, hi, (rect.x + 2, rect.y + 2), (rect.x + 2, rect.bottom - 3))
    pygame.draw.line(surf, lo, (rect.x + 2, rect.bottom - 3), (rect.right - 3, rect.bottom - 3))
    pygame.draw.line(surf, lo, (rect.right - 3, rect.y + 2), (rect.right - 3, rect.bottom - 3))
    pygame.draw.rect(surf, shade(color, -90), rect, 1)


def draw_text(
    surf: pygame.Surface,
    text: str,
    x: int,
    y: int,
    font: pygame.font.Font,
    color: Color = WHITE,
) -> None:
    surf.blit(font.render(text, True, color), (x, y))


def draw_preview(surf: pygame.Surface, kind: str, rect: pygame.Rect, cell: int = 22) -> None:
    cells = SHAPES[kind]
    min_x = min(cx for cx, _ in cells)
    max_x = max(cx for cx, _ in cells)
    min_y = min(cy for _, cy in cells)
    max_y = max(cy for _, cy in cells)
    w = (max_x - min_x + 1) * cell
    h = (max_y - min_y + 1) * cell
    ox = rect.x + (rect.w - w) // 2
    oy = rect.y + 34 + (rect.h - 34 - h) // 2
    for cx, cy in cells:
        r = pygame.Rect(ox + (cx - min_x) * cell, oy + (cy - min_y) * cell, cell, cell)
        pygame.draw.rect(surf, COLORS[kind], r)
        pygame.draw.rect(surf, shade(COLORS[kind], -70), r, 1)


def draw_panel(
    surf: pygame.Surface,
    rect: pygame.Rect,
    title: str,
    f_small: pygame.font.Font,
) -> None:
    pygame.draw.rect(surf, PANEL, rect, border_radius=6)
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=6)
    draw_text(surf, title, rect.x + 10, rect.y + 8, f_small, DIM)


def draw(screen: pygame.Surface, game: Game, fonts: dict[str, pygame.font.Font]) -> None:
    screen.fill(BG)
    board_rect = pygame.Rect(0, 0, BOARD_W, BOARD_H)
    pygame.draw.rect(screen, PANEL, board_rect)

    for y in range(ROWS):
        for x in range(COLS):
            color = game.board[y][x]
            if color is not None:
                draw_cell(screen, x, y, color)

    p = game.piece
    if p is not None and not game.over:
        d = game.drop_distance()
        for cx, cy in p.cells:
            gx, gy = p.x + cx, p.y + cy + d
            if gy >= 0:
                pygame.draw.rect(
                    screen, GHOST, pygame.Rect(gx * CELL, gy * CELL, CELL, CELL), 2
                )
        color = COLORS[p.kind]
        for cx, cy in p.cells:
            px, py = p.x + cx, p.y + cy
            if py >= 0:
                draw_cell(screen, px, py, color)

    for x in range(COLS + 1):
        pygame.draw.line(screen, GRID, (x * CELL, 0), (x * CELL, BOARD_H))
    for y in range(ROWS + 1):
        pygame.draw.line(screen, GRID, (0, y * CELL), (BOARD_W, y * CELL))
    pygame.draw.rect(screen, BORDER, board_rect, 2)

    sx = SIDEBAR_X
    pw = SIDEBAR_INNER_W
    f_tiny, f_small, f_med, f_big = (
        fonts["tiny"], fonts["small"], fonts["med"], fonts["big"]
    )

    hold_rect = pygame.Rect(sx, 10, pw, 104)
    draw_panel(screen, hold_rect, "HOLD", f_small)
    if game.held_kind is not None:
        draw_preview(screen, game.held_kind, hold_rect)
        if not game.can_hold:
            dim = pygame.Surface((hold_rect.w, hold_rect.h - 28), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 130))
            screen.blit(dim, (hold_rect.x, hold_rect.y + 28))

    next_rect = pygame.Rect(sx, 122, pw, 104)
    draw_panel(screen, next_rect, "NEXT", f_small)
    draw_preview(screen, game.next_kind, next_rect)

    info_rect = pygame.Rect(sx, 234, pw, 168)
    draw_panel(screen, info_rect, "INFO", f_small)
    draw_text(screen, "SCORE", sx + 10, info_rect.y + 30, f_small, DIM)
    draw_text(screen, str(game.score), sx + 10, info_rect.y + 48, f_big, WHITE)
    draw_text(screen, "BEST", sx + 10, info_rect.y + 86, f_small, DIM)
    draw_text(screen, str(game.highscore), sx + 10, info_rect.y + 102, f_med, (250, 200, 0))
    draw_text(screen, "LEVEL", sx + 112, info_rect.y + 30, f_small, DIM)
    draw_text(screen, str(game.level), sx + 112, info_rect.y + 48, f_big, WHITE)
    draw_text(screen, "LINES", sx + 112, info_rect.y + 86, f_small, DIM)
    draw_text(screen, str(game.lines), sx + 112, info_rect.y + 102, f_med, WHITE)

    help_rect = pygame.Rect(sx, 410, pw, 128)
    draw_panel(screen, help_rect, "CONTROLS", f_small)
    for i, line in enumerate(
        ["< >  move     v  soft drop",
         "^/X rotate    Z  rotate ccw",
         "space  hard drop    C  hold",
         "P  pause    M  mute",
         "Q  quit     R  restart"]
    ):
        draw_text(screen, line, sx + 10, help_rect.y + 30 + i * 18, f_tiny, DIM)

    hover = NEW_GAME_RECT.collidepoint(pygame.mouse.get_pos())
    fill = (60, 120, 200) if hover else (36, 62, 108)
    pygame.draw.rect(screen, fill, NEW_GAME_RECT, border_radius=6)
    pygame.draw.rect(screen, BORDER, NEW_GAME_RECT, 1, border_radius=6)
    label = f_med.render("NEW GAME", True, WHITE)
    screen.blit(
        label,
        (
            NEW_GAME_RECT.x + (NEW_GAME_RECT.w - label.get_width()) // 2,
            NEW_GAME_RECT.y + (NEW_GAME_RECT.h - label.get_height()) // 2,
        ),
    )

    if game.mode == "demo" and not game.over:
        banner = f_small.render("DEMO - click NEW GAME to play", True, DIM)
        screen.blit(banner, (BOARD_W // 2 - banner.get_width() // 2, 6))

    if game.paused and not game.over:
        overlay = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, board_rect)
        draw_text(screen, "PAUSED", BOARD_W // 2, BOARD_H // 2 - 40, fonts["huge"], WHITE)
    if game.over:
        overlay = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, board_rect)
        draw_text(screen, "GAME OVER", BOARD_W // 2, BOARD_H // 2 - 70, fonts["huge"], (240, 80, 80))
        draw_text(screen, f"Score: {game.score}", BOARD_W // 2, BOARD_H // 2 - 10, f_big, WHITE)
        draw_text(screen, "R - restart   Q - quit", BOARD_W // 2, BOARD_H // 2 + 30, f_med, DIM)


def main() -> None:
    random.seed()
    pygame.init()
    try:
        pygame.mixer.pre_init(22050, -16, 1, 512)
    except pygame.error:
        pass
    sounds = Sounds.build()
    pygame.key.set_repeat(170, 60)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()
    fonts: dict[str, pygame.font.Font] = {
        "tiny": pygame.font.SysFont(None, 16),
        "small": pygame.font.SysFont(None, 20),
        "med": pygame.font.SysFont(None, 30),
        "big": pygame.font.SysFont(None, 40),
        "huge": pygame.font.SysFont(None, 64),
    }
    game = Game(mode="demo")
    bot = Bot()
    demo_restart_timer = 0.0

    def start_human_game() -> None:
        game.mode = "human"
        game.reset()

    running = True
    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if NEW_GAME_RECT.collidepoint(event.pos):
                    start_human_game()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_m:
                    sounds.enabled = not sounds.enabled
                elif event.key == pygame.K_p and not game.over:
                    game.paused = not game.paused
                elif game.mode == "human":
                    if game.over:
                        if event.key in (pygame.K_r, pygame.K_RETURN):
                            game.reset()
                    elif not game.paused:
                        if event.key == pygame.K_LEFT:
                            if game.move(-1, 0):
                                sounds.play("move")
                        elif event.key == pygame.K_RIGHT:
                            if game.move(1, 0):
                                sounds.play("move")
                        elif event.key == pygame.K_DOWN:
                            before = game.piece.y if game.piece else -1
                            game.soft_drop()
                            if game.piece is not None and game.piece.y != before:
                                sounds.play("drop")
                        elif event.key in (pygame.K_UP, pygame.K_x):
                            if game.rotate(1):
                                sounds.play("rotate")
                        elif event.key == pygame.K_z:
                            if game.rotate(-1):
                                sounds.play("rotate")
                        elif event.key == pygame.K_SPACE:
                            if game.piece is not None:
                                sounds.play("hard")
                            game.hard_drop()
                        elif event.key == pygame.K_c:
                            piece0 = game.piece
                            game.hold()
                            if game.piece is not piece0:
                                sounds.play("rotate")
                elif event.key in (pygame.K_r, pygame.K_RETURN):
                    start_human_game()

        bot.step(game, dt)
        before = game.over
        game.update(dt)
        if game.last_cleared > 0:
            sounds.play("tetris" if game.last_cleared == 4 else "clear")
            game.last_cleared = 0
        if game.over and not before:
            sounds.play("over")
            save_highscore(game.highscore)
        if game.over and game.mode == "demo":
            demo_restart_timer += dt
            if demo_restart_timer >= DEMO_RESTART_DELAY * 1000:
                demo_restart_timer = 0.0
                game.reset()
        else:
            demo_restart_timer = 0.0

        draw(screen, game, fonts)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

"""Tetris in a single file, powered by pygame.

Controls:
    Left / Right      move
    Down              soft drop
    Up / X            rotate clockwise
    Z                 rotate counter-clockwise
    Space             hard drop
    P                 pause
    R                 restart (after game over)
    Q                 quit
"""

import random
import sys

import pygame

COLS = 10
ROWS = 20
CELL = 30
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
SIDEBAR_W = 210
WIDTH = BOARD_W + SIDEBAR_W
HEIGHT = BOARD_H
FPS = 60

BG = (16, 16, 22)
PANEL = (24, 24, 34)
GRID = (36, 36, 50)
BORDER = (80, 80, 105)
WHITE = (235, 235, 240)
DIM = (140, 140, 160)
GHOST = (95, 95, 120)

SHAPES = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}

BOX = {"I": 4, "O": 2, "T": 3, "S": 3, "Z": 3, "J": 3, "L": 3}

COLORS = {
    "I": (0, 190, 255),
    "O": (250, 200, 0),
    "T": (170, 60, 255),
    "S": (60, 210, 60),
    "Z": (240, 60, 60),
    "J": (70, 100, 255),
    "L": (255, 130, 30),
}

KICKS = ((0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0), (1, -1), (-1, -1))
SCORE_TABLE = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}


def rotate_cells(cells, direction, size):
    if direction >= 0:
        return frozenset((size - 1 - y, x) for x, y in cells)
    return frozenset((y, size - 1 - x) for x, y in cells)


def shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color)


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.cells = frozenset(SHAPES[kind])
        self.x = (COLS - BOX[kind]) // 2
        self.y = 0


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.score = 0
        self.lines = 0
        self.level = 1
        self.over = False
        self.paused = False
        self.next_kind = self._draw_kind()
        self.piece = None
        self.drop_timer = 0.0
        self.spawn()

    def _draw_kind(self):
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    @property
    def drop_delay(self):
        return max(0.08, 0.60 - (self.level - 1) * 0.05)

    def collides(self, cells, ox, oy):
        for cx, cy in cells:
            x, y = ox + cx, oy + cy
            if x < 0 or x >= COLS or y >= ROWS:
                return True
            if y >= 0 and self.board[y][x] is not None:
                return True
        return False

    def spawn(self):
        self.piece = Piece(self.next_kind)
        self.next_kind = self._draw_kind()
        if self.collides(self.piece.cells, self.piece.x, self.piece.y):
            self.over = True

    def move(self, dx, dy):
        p = self.piece
        if p is not None and not self.collides(p.cells, p.x + dx, p.y + dy):
            p.x += dx
            p.y += dy
            return True
        return False

    def rotate(self, direction=1):
        p = self.piece
        if p is None:
            return
        new_cells = rotate_cells(p.cells, direction, BOX[p.kind])
        for kx, ky in KICKS:
            if not self.collides(new_cells, p.x + kx, p.y + ky):
                p.cells = new_cells
                p.x += kx
                p.y += ky
                return

    def drop_distance(self):
        p = self.piece
        if p is None:
            return 0
        d = 0
        while not self.collides(p.cells, p.x, p.y + d + 1):
            d += 1
        return d

    def soft_drop(self):
        if self.move(0, 1):
            self.score += 1
        else:
            self.lock()

    def hard_drop(self):
        d = self.drop_distance()
        self.piece.y += d
        self.score += 2 * d
        self.lock()

    def lock(self):
        p = self.piece
        color = COLORS[p.kind]
        for cx, cy in p.cells:
            x, y = p.x + cx, p.y + cy
            if 0 <= x < COLS and 0 <= y < ROWS:
                self.board[y][x] = color
        self._clear_lines()
        self.spawn()

    def _clear_lines(self):
        kept = [row for row in self.board if any(c is None for c in row)]
        cleared = ROWS - len(kept)
        if cleared:
            self.board = [[None] * COLS for _ in range(cleared)] + kept
            self.lines += cleared
            self.level = self.lines // 10 + 1
            self.score += SCORE_TABLE[cleared] * self.level

    def update(self, dt):
        if self.over or self.paused or self.piece is None:
            return
        self.drop_timer += dt / 1000.0
        while self.drop_timer >= self.drop_delay:
            self.drop_timer -= self.drop_delay
            if not self.move(0, 1):
                self.lock()
                self.drop_timer = 0.0
                if self.over or self.piece is None:
                    return


def draw_cell(surf, x, y, color, size=CELL):
    rect = pygame.Rect(x * size, y * size, size, size)
    pygame.draw.rect(surf, color, rect)
    hi = shade(color, 55)
    lo = shade(color, -55)
    pygame.draw.line(surf, hi, (rect.x + 2, rect.y + 2), (rect.right - 3, rect.y + 2))
    pygame.draw.line(surf, hi, (rect.x + 2, rect.y + 2), (rect.x + 2, rect.bottom - 3))
    pygame.draw.line(surf, lo, (rect.x + 2, rect.bottom - 3), (rect.right - 3, rect.bottom - 3))
    pygame.draw.line(surf, lo, (rect.right - 3, rect.y + 2), (rect.right - 3, rect.bottom - 3))
    pygame.draw.rect(surf, shade(color, -90), rect, 1)


def draw_text(surf, text, x, y, font, color=WHITE):
    surf.blit(font.render(text, True, color), (x, y))


def draw_preview(surf, kind, rect, cell=22):
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


def draw_panel(surf, rect, title, font, f_small):
    pygame.draw.rect(surf, PANEL, rect, border_radius=6)
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=6)
    draw_text(surf, title, rect.x + 10, rect.y + 8, f_small, DIM)


def draw(screen, game, fonts):
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

    sx = BOARD_W + 15
    pw = SIDEBAR_W - 30
    f_small, f_med, f_big = fonts["small"], fonts["med"], fonts["big"]

    next_rect = pygame.Rect(sx, 12, pw, 150)
    draw_panel(screen, next_rect, "NEXT", f_small, f_small)
    draw_preview(screen, game.next_kind, next_rect)

    info_rect = pygame.Rect(sx, 176, pw, 168)
    draw_panel(screen, info_rect, "INFO", f_small, f_small)
    draw_text(screen, "SCORE", sx + 10, info_rect.y + 34, f_small, DIM)
    draw_text(screen, str(game.score), sx + 10, info_rect.y + 54, f_big, WHITE)
    draw_text(screen, "LEVEL", sx + 10, info_rect.y + 90, f_small, DIM)
    draw_text(screen, str(game.level), sx + 10, info_rect.y + 108, f_med, WHITE)
    draw_text(screen, "LINES", sx + 10, info_rect.y + 132, f_small, DIM)
    draw_text(screen, str(game.lines), sx + 10, info_rect.y + 148, f_med, WHITE)

    help_rect = pygame.Rect(sx, 358, pw, HEIGHT - 370)
    draw_panel(screen, help_rect, "CONTROLS", f_small, f_small)
    for i, line in enumerate(
        ["<  >  move", "v     soft drop", "^ / X rotate",
         "Z     rotate ccw", "space hard drop", "P     pause", "Q     quit"]
    ):
        draw_text(screen, line, sx + 10, help_rect.y + 34 + i * 18, f_small, DIM)

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


def main():
    random.seed()
    pygame.init()
    pygame.key.set_repeat(170, 60)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()
    fonts = {
        "small": pygame.font.SysFont(None, 20),
        "med": pygame.font.SysFont(None, 30),
        "big": pygame.font.SysFont(None, 40),
        "huge": pygame.font.SysFont(None, 64),
    }
    game = Game()

    running = True
    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif game.over:
                    if event.key in (pygame.K_r, pygame.K_RETURN):
                        game.reset()
                elif event.key == pygame.K_p:
                    game.paused = not game.paused
                elif not game.paused:
                    if event.key == pygame.K_LEFT:
                        game.move(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        game.move(1, 0)
                    elif event.key == pygame.K_DOWN:
                        game.soft_drop()
                    elif event.key in (pygame.K_UP, pygame.K_x):
                        game.rotate(1)
                    elif event.key == pygame.K_z:
                        game.rotate(-1)
                    elif event.key == pygame.K_SPACE:
                        game.hard_drop()

        game.update(dt)
        draw(screen, game, fonts)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

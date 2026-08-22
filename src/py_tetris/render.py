"""All pygame drawing: board, sidebar, previews and overlays."""

import pygame

from py_tetris.background import Background
from py_tetris.constants import (
    BOARD_H,
    BOARD_W,
    BG,
    BORDER,
    CELL,
    COLS,
    DIM,
    GHOST,
    GRID,
    MARATHON_RECT,
    PANEL,
    ROWS,
    SIDEBAR_INNER_W,
    SIDEBAR_X,
    SPRINT_RECT,
    SPRINT_TARGET,
    ULTRA_RECT,
    WHITE,
)
from py_tetris.constants import Color
from py_tetris.game import Game
from py_tetris.pieces import COLORS, SHAPES


def shade(color: Color, amount: int) -> Color:
    r, g, b = color
    return (
        max(0, min(255, r + amount)),
        max(0, min(255, g + amount)),
        max(0, min(255, b + amount)),
    )


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


_board_overlay: pygame.Surface | None = None


def _board_base() -> pygame.Surface:
    """Translucent board fill so the animated background glows through."""
    global _board_overlay
    if _board_overlay is None:
        _board_overlay = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        _board_overlay.fill((*PANEL, 150))
    return _board_overlay


def draw(
    screen: pygame.Surface,
    game: Game,
    fonts: dict[str, pygame.font.Font],
    bg: Background | None = None,
) -> None:
    screen.fill(BG)
    if bg is not None:
        bg.draw(screen)
    board_rect = pygame.Rect(0, 0, BOARD_W, BOARD_H)
    screen.blit(_board_base(), board_rect)

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

    f_tiny, f_small, f_med, f_big = (
        fonts["tiny"], fonts["small"], fonts["med"], fonts["big"]
    )

    if game.clear_flash > 0 and game.last_cleared > 0:
        n = min(game.last_cleared, ROWS)
        alpha = 110 if int(game.clear_flash * 20) % 2 == 0 else 30
        flash = pygame.Surface((BOARD_W, n * CELL), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        screen.blit(flash, (0, (ROWS - n) * CELL))
        if game.last_tspin:
            label = f_med.render("T-SPIN!" if game.last_tspin == "full" else "MINI T-SPIN", True, (250, 200, 0))
            screen.blit(label, (BOARD_W // 2 - label.get_width() // 2, BOARD_H // 2 - 80))
        if game.combo >= 2:
            label = f_med.render(f"COMBO x{game.combo}", True, (250, 200, 0))
            screen.blit(label, (BOARD_W // 2 - label.get_width() // 2, BOARD_H // 2 - 40))

    sx = SIDEBAR_X
    pw = SIDEBAR_INNER_W

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
    if game.game_mode == "ultra":
        t = int(game.time_left)
        draw_text(screen, "TIME", sx + 112, info_rect.y + 86, f_small, DIM)
        draw_text(screen, f"{t // 60}:{t % 60:02d}", sx + 112, info_rect.y + 102, f_med, WHITE)
    else:
        draw_text(screen, "LINES", sx + 112, info_rect.y + 86, f_small, DIM)
        shown = f"{game.lines}/{SPRINT_TARGET}" if game.game_mode == "sprint" else str(game.lines)
        draw_text(screen, shown, sx + 112, info_rect.y + 102, f_med, WHITE)

    mouse = pygame.mouse.get_pos()
    for mode_label, rect, gm in (
        ("MARATHON", MARATHON_RECT, "marathon"),
        ("SPRINT", SPRINT_RECT, "sprint"),
        ("ULTRA", ULTRA_RECT, "ultra"),
    ):
        active = game.mode == "human" and game.game_mode == gm
        hover = rect.collidepoint(mouse)
        fill = (60, 120, 200) if hover else ((48, 56, 100) if active else (30, 34, 58))
        pygame.draw.rect(screen, fill, rect, border_radius=5)
        pygame.draw.rect(screen, BORDER, rect, 1, border_radius=5)
        img = f_small.render(mode_label, True, WHITE if (hover or active) else DIM)
        screen.blit(img, (rect.x + (rect.w - img.get_width()) // 2, rect.y + (rect.h - img.get_height()) // 2))

    help_rect = pygame.Rect(sx, 522, pw, 70)
    draw_panel(screen, help_rect, "CONTROLS", f_small)
    for i, line in enumerate(
        ["< > move   v drop   space hard",
         "^/X/Z rotate   C hold",
         "P pause   M mute   Q quit"]
    ):
        draw_text(screen, line, sx + 10, help_rect.y + 28 + i * 14, f_tiny, DIM)

    if game.mode == "demo" and not game.over:
        banner = f_small.render("DEMO - pick a mode to play", True, DIM)
        screen.blit(banner, (BOARD_W // 2 - banner.get_width() // 2, 6))

    if game.paused and not game.over:
        overlay = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, board_rect)
        img = fonts["huge"].render("PAUSED", True, WHITE)
        screen.blit(img, (BOARD_W // 2 - img.get_width() // 2, BOARD_H // 2 - 40))
    if game.over:
        overlay = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, board_rect)
        if game.won:
            title, tcolor = "YOU WIN!", (250, 200, 0)
        elif game.game_mode == "ultra":
            title, tcolor = "TIME UP", (240, 80, 80)
        else:
            title, tcolor = "GAME OVER", (240, 80, 80)
        img = fonts["huge"].render(title, True, tcolor)
        screen.blit(img, (BOARD_W // 2 - img.get_width() // 2, BOARD_H // 2 - 70))
        score = f_big.render(f"Score: {game.score}", True, WHITE)
        screen.blit(score, (BOARD_W // 2 - score.get_width() // 2, BOARD_H // 2 - 10))
        hint = f_med.render("R - restart   Q - quit", True, DIM)
        screen.blit(hint, (BOARD_W // 2 - hint.get_width() // 2, BOARD_H // 2 + 30))

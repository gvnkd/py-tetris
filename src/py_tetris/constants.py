"""Board, window, timing and color constants."""

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

SCORE_TABLE: dict[int, int] = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}

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
CLEAR_FLASH_DURATION = 0.25  # seconds the cleared rows flash before collapsing
MAX_LOCK_RESETS = 15  # move/rotate resets per grounded spell (stops infinite spin)
BOT_THINK_INTERVAL = 0.6  # seconds a fresh piece falls before the bot acts
BOT_DROP_PAUSE = 0.3  # seconds the bot idles after each drop (demo rhythm)
DEMO_RESTART_DELAY = 2.0  # seconds the demo shows game over before restarting
DAS_DELAY = 0.17  # seconds before a held movement key starts repeating
ARR_INTERVAL = 0.05  # seconds between repeats once DAS has elapsed

SIDEBAR_X = BOARD_W + 15
SIDEBAR_INNER_W = SIDEBAR_W - 30
MARATHON_RECT = pygame.Rect(SIDEBAR_X, 416, SIDEBAR_INNER_W, 28)
SPRINT_RECT = pygame.Rect(SIDEBAR_X, 450, SIDEBAR_INNER_W, 28)
ULTRA_RECT = pygame.Rect(SIDEBAR_X, 484, SIDEBAR_INNER_W, 28)

SPRINT_TARGET = 20  # lines to win sprint
ULTRA_TIME = 120.0  # seconds for ultra
ULTRA_LEVEL = 5  # fixed gravity level for ultra

BG: Color = (16, 16, 22)
PANEL: Color = (24, 24, 34)
GRID: Color = (36, 36, 50)
BORDER: Color = (80, 80, 105)
WHITE: Color = (235, 235, 240)
DIM: Color = (140, 140, 160)
GHOST: Color = (95, 95, 120)

SCORE_TABLE: dict[int, int] = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}

# T-spin scores per lines cleared (guideline values, pre-level multiplier)
TSPIN_SCORES: dict[str, dict[int, int]] = {
    "mini": {0: 100, 1: 200, 2: 400, 3: 400},
    "full": {0: 400, 1: 800, 2: 1200, 3: 1600},
}
B2B_MULTIPLIER = 1.5  # back-to-back difficult clears (TETRIS, T-spin 2+)
COMBO_BONUS = 50  # per consecutive clear, times level

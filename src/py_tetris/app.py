"""Application entry point: pygame init, main loop and input handling.

Controls:
    Left / Right      move
    Down              soft drop
    Up / X            rotate clockwise
    Z                 rotate counter-clockwise
    Space             hard drop
    C                 hold piece
    M                 mute / unmute sounds and music
    P                 pause
    R                 restart (after game over)
    Q                 quit
"""

import random
import sys

import pygame

from py_tetris.audio import Music, Sounds
from py_tetris.constants import DEMO_RESTART_DELAY, FPS, HEIGHT, NEW_GAME_RECT, WIDTH
from py_tetris.game import Bot, Game
from py_tetris.highscore import save_highscore
from py_tetris.render import draw


def main() -> None:
    random.seed()
    try:
        pygame.mixer.pre_init(22050, -16, 1, 512)
    except pygame.error:
        pass
    pygame.init()
    sounds = Sounds.build()
    music = Music()
    music.start()
    music.play()
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
                    if sounds.enabled:
                        music.play()
                    else:
                        music.stop()
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

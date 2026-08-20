import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

import pytest

import tetris
from tetris import (
    BOX,
    COLS,
    COLORS,
    I_KICKS,
    JLSTZ_KICKS,
    LOCK_DELAY,
    MAX_LOCK_RESETS,
    ROWS,
    SHAPES,
    SCORE_TABLE,
    Game,
    Piece,
    rotate_cells,
    save_highscore,
)


def make_game(piece_kind: str = "O") -> Game:
    g = Game()
    g.piece = Piece(piece_kind)
    return g


def fill_rows(g: Game, bottom_n: int, color=(9, 9, 9)) -> None:
    for row in range(ROWS - bottom_n, ROWS):
        for x in range(COLS):
            g.board[row][x] = color


def fill_top_rows(g: Game, top_n: int, color=(9, 9, 9)) -> None:
    for row in range(top_n):
        for x in range(COLS):
            g.board[row][x] = color


# --- bag randomizer ---------------------------------------------------------


def test_first_bag_is_a_permutation():
    g = Game()
    g.bag = []
    first7 = [g._draw_kind() for _ in range(7)]
    assert sorted(first7) == sorted(SHAPES)


def test_bag_fairness_over_many_draws():
    g = Game()
    g.bag = []
    counts: dict[str, int] = {}
    for _ in range(700):
        k = g._draw_kind()
        counts[k] = counts.get(k, 0) + 1
    assert set(counts) == set(SHAPES)
    assert all(v == 100 for v in counts.values())


# --- rotation math ----------------------------------------------------------


def test_four_cw_rotations_are_identity():
    for kind, cells in SHAPES.items():
        r = frozenset(cells)
        for _ in range(4):
            r = rotate_cells(r, 1, BOX[kind])
        assert r == frozenset(cells), kind


def test_cw_then_ccw_is_identity():
    for kind, cells in SHAPES.items():
        r = rotate_cells(frozenset(cells), -1, BOX[kind])
        assert rotate_cells(r, 1, BOX[kind]) == frozenset(cells), kind


def test_rotation_changes_non_symmetric_pieces():
    for kind in ("I", "T", "S", "Z", "J", "L"):
        r = rotate_cells(frozenset(SHAPES[kind]), 1, BOX[kind])
        assert r != frozenset(SHAPES[kind]), kind


def test_rotated_cells_stay_in_box():
    for kind, cells in SHAPES.items():
        n = BOX[kind]
        for direction in (1, -1):
            for cx, cy in rotate_cells(frozenset(cells), direction, n):
                assert 0 <= cx < n and 0 <= cy < n, kind


# --- movement bounds --------------------------------------------------------


def test_cannot_pass_left_or_right_wall():
    g = make_game("O")
    g.piece.x = 0
    assert not g.move(-1, 0)
    assert g.piece.x == 0
    g.piece.x = COLS - 2
    assert not g.move(1, 0)
    assert g.piece.x == COLS - 2


def test_cannot_pass_floor():
    g = make_game("O")
    g.piece.y = ROWS - 2
    assert not g.move(0, 1)
    assert g.piece.y == ROWS - 2


def test_move_succeeds_inside_board():
    g = make_game("O")
    x0, y0 = g.piece.x, g.piece.y
    assert g.move(-1, 0)
    assert g.piece.x == x0 - 1
    assert g.move(0, 1)
    assert g.piece.y == y0 + 1


# --- wall kicks ---------------------------------------------------------------


def test_kick_when_rotating_at_floor():
    g = make_game("T")
    g.piece.y = ROWS - 2
    assert g.rotate(1)
    # base rotation reaches row ROWS; SRS kick (0, 2) pulls it up one
    assert g.piece.state == 1
    assert g.piece.y == ROWS - 3
    assert g.piece.cells == frozenset({(2, 1), (1, 0), (1, 1), (1, 2)})


def test_i_floor_rotation_uses_srs_kick():
    g = make_game("I")
    g.piece.x = 3
    g.piece.y = ROWS - 2  # horizontal I on the bottom row
    assert g.rotate(1)
    # vertical I sticks out of the floor; SRS I kick (1, -2) lifts and shifts it
    assert g.piece.state == 1
    assert g.piece.x == 4
    assert g.piece.y == ROWS - 4
    assert not g.collides(g.piece.cells, g.piece.x, g.piece.y)


def test_kick_when_rotating_at_left_wall():
    g = make_game("I")
    g.piece.cells = rotate_cells(g.piece.cells, -1, BOX["I"])  # vertical I, box col 1
    g.piece.state = 3
    g.piece.x = -1  # vertical column sits on board col 0
    assert not g.collides(g.piece.cells, g.piece.x, g.piece.y)
    assert g.rotate(1)
    # horizontal I would span board cols -1..2; SRS I kick (1, 0) slides it in
    assert g.piece.state == 0
    assert g.piece.x == 0
    assert not g.collides(g.piece.cells, g.piece.x, g.piece.y)


def test_impossible_rotation_leaves_piece_unchanged():
    g = make_game("I")
    g.piece.x = 0
    g.piece.y = ROWS - 2  # horizontal I on the bottom row
    for x in range(COLS):
        g.board[ROWS - 3][x] = (5, 5, 5)
    cells0, x0, y0, state0 = g.piece.cells, g.piece.x, g.piece.y, g.piece.state
    assert g.rotate(1) is False  # all five SRS kicks collide
    assert (g.piece.cells, g.piece.x, g.piece.y, g.piece.state) == (cells0, x0, y0, state0)


def test_srs_kick_tables_match_spec():
    # canonical SRS values in board coordinates (+dy = down)
    assert JLSTZ_KICKS[(0, 1)] == ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2))
    assert JLSTZ_KICKS[(3, 0)] == ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2))
    assert I_KICKS[(0, 1)] == ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2))
    assert I_KICKS[(1, 0)] == ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2))


def test_srs_tables_are_inverse_consistent():
    for table in (JLSTZ_KICKS, I_KICKS):
        for (a, b), kicks in table.items():
            assert kicks[0] == (0, 0)
            back = table[(b, a)]
            assert back[0] == (0, 0)
            assert set(kicks[1:]) == {(-dx, -dy) for (dx, dy) in back[1:]}


def test_o_rotation_never_kicks():
    g = make_game("O")
    cells0 = g.piece.cells
    assert g.rotate(1)
    assert g.piece.cells == cells0
    assert g.piece.state == 0


def test_rotation_state_tracks_srs():
    g = make_game("T")
    states = [g.piece.state]
    for _ in range(4):
        assert g.rotate(1)
        states.append(g.piece.state)
    assert states == [0, 1, 2, 3, 0]


def test_rotation_never_leaves_board():
    random.seed(1)
    for _ in range(200):
        g = Game()
        p = g.piece
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p.x = (COLS - BOX[p.kind]) // 2 + dx
                p.y = ROWS - 3 + dy
                if g.collides(p.cells, p.x, p.y):
                    continue
                g.rotate(1)
                for cx, cy in p.cells:
                    bx, by = p.x + cx, p.y + cy
                    assert 0 <= bx < COLS, (p.kind, p.x, p.y)
                    assert by < ROWS


# --- drops -------------------------------------------------------------------


def test_drop_distance_is_rest_position():
    random.seed(7)
    g = Game()
    for _ in range(3):
        p = g.piece
        d = g.drop_distance()
        assert not g.collides(p.cells, p.x, p.y + d)
        assert g.collides(p.cells, p.x, p.y + d + 1)
        g.hard_drop()


def test_hard_drop_locks_piece_and_scores():
    g = make_game("O")
    d = g.drop_distance()
    assert d == ROWS - 2
    score0 = g.score
    g.hard_drop()
    assert g.score - score0 == 2 * d
    color = COLORS["O"]
    assert sum(c == color for row in g.board for c in row) == 4
    assert all(c is None or c != color for row in g.board[: ROWS - 2] for c in row)


def test_soft_drop_moves_one_and_scores():
    g = make_game("O")
    y0 = g.piece.y
    g.soft_drop()
    assert g.piece.y == y0 + 1
    assert g.score == 1


def test_soft_drop_locks_on_floor():
    g = make_game("O")
    g.next_kind = "I"
    g.piece.y = ROWS - 2
    g.soft_drop()
    assert sum(c == COLORS["O"] for row in g.board for c in row) == 4
    assert g.piece.kind == "I"


def test_spawn_uses_announced_next_piece():
    g = Game()
    announced = g.next_kind
    g.hard_drop()
    assert g.piece.kind == announced


# --- lock delay --------------------------------------------------------------


def test_grounding_does_not_instantly_lock():
    g = make_game("O")
    g.piece.y = ROWS - 2
    g.update(400)  # less than LOCK_DELAY
    assert g.piece is not None
    assert g.piece.y == ROWS - 2
    assert sum(c == COLORS["O"] for row in g.board for c in row) == 0


def test_lock_delay_expires():
    g = make_game("O")
    g.piece.y = ROWS - 2
    g.update(int(LOCK_DELAY * 1000) + 1)
    assert sum(c == COLORS["O"] for row in g.board for c in row) == 4


def test_lock_delay_resets_on_move():
    g = make_game("O")
    g.piece.y = ROWS - 2
    g.update(300)
    assert g.lock_timer == pytest.approx(0.3)
    assert g.move(1, 0)
    assert g.lock_timer == 0
    g.update(400)  # 0.4 < LOCK_DELAY after the reset
    assert sum(c == COLORS["O"] for row in g.board for c in row) == 0


def test_lock_delay_resets_on_rotate():
    g = make_game("T")
    g.piece.y = ROWS - 2
    g.update(300)
    assert g.rotate(1)
    assert g.lock_timer == 0


def test_lock_resets_are_capped():
    g = make_game("O")
    g.piece.y = ROWS - 2
    for i in range(MAX_LOCK_RESETS + 5):
        if i % 2 == 0:
            g.move(1, 0)
        else:
            g.rotate(1)
        g.update(300)
        if g.piece is None or g.piece.y != ROWS - 2:
            break  # piece locked: resets ran out
    assert g.lock_resets <= MAX_LOCK_RESETS
    assert sum(c == COLORS["O"] for row in g.board for c in row) == 4


def test_lock_returns_cleared_lines():
    g = make_game("I")
    g.piece.x = 3
    g.piece.y = ROWS - 2
    for x in range(COLS):
        if not (3 <= x <= 6):
            g.board[ROWS - 1][x] = (5, 5, 5)
    assert g.lock() == 1
    assert g.lines == 1


# --- hold ----------------------------------------------------------------------


def test_hold_stores_and_swaps():
    g = make_game("T")
    g.held_kind = "S"
    g.hold()
    assert g.held_kind == "T"
    assert g.piece.kind == "S"
    assert not g.can_hold


def test_hold_first_time_spawns_next():
    g = Game()
    kind0 = g.piece.kind
    next0 = g.next_kind
    g.hold()
    assert g.held_kind == kind0
    assert g.piece.kind == next0
    assert not g.can_hold


def test_cannot_hold_twice():
    g = make_game("T")
    g.held_kind = "S"
    g.hold()
    piece0 = g.piece
    g.hold()
    assert g.piece is piece0
    assert g.held_kind == "T"


def test_hold_reallowed_after_soft_drop():
    g = make_game("T")
    g.held_kind = "S"
    g.move(0, 1)
    assert g.can_hold
    g.hold()
    assert g.piece.kind == "S"


# --- high score ------------------------------------------------------------------


def test_highscore_loaded_and_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    hs = tmp_path / "py-tetris" / "highscore"
    hs.parent.mkdir()
    hs.write_text("1234\n")
    assert Game().highscore == 1234
    save_highscore(2000)
    assert hs.read_text().strip() == "2000"
    assert Game().highscore == 2000


def test_highscore_survives_bad_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    hs = tmp_path / "py-tetris" / "highscore"
    hs.parent.mkdir()
    hs.write_text("garbage")
    assert Game().highscore == 0


def test_highscore_tracks_best_score():
    g = Game(highscore=100)
    g.score = 50
    g.lock()
    assert g.highscore == 100
    g.score = 200
    g.lock()
    assert g.highscore == 200


# --- sounds (headless) --------------------------------------------------------------


def test_tone_renders_valid_pcm():
    data = tetris._tone(440.0, 100, 0.5)
    assert len(data) == 2 * (22050 * 100 // 1000)
    assert tetris._tone(440.0, 100, 0.5) == data  # deterministic


def test_sounds_build_without_mixer():
    s = tetris.Sounds.build()  # headless: no mixer -> no sounds, no crash
    s.play("move")


def test_sounds_disabled_plays_nothing():
    s = tetris.Sounds(enabled=False)
    s.play("move")


# --- line clears, scoring, levels ---------------------------------------------


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_clear_lines_scores_by_table(n):
    g = make_game()
    g.level = 1
    fill_rows(g, n)
    score0 = g.score
    g._clear_lines()
    assert g.lines == n
    assert g.score - score0 == SCORE_TABLE[n]
    assert all(c is None for c in g.board[ROWS - 1])


def test_clear_lines_shifts_rows_down():
    g = make_game()
    marker = (1, 2, 3)
    g.board[ROWS - 2][0] = marker
    fill_rows(g, 1, color=(9, 9, 9))
    g._clear_lines()
    assert g.board[ROWS - 1][0] == marker
    assert g.lines == 1


def test_uncleared_rows_are_untouched():
    g = make_game()
    fill_rows(g, 3)
    g.board[ROWS - 5][2] = (1, 2, 3)
    g._clear_lines()
    assert g.board[ROWS - 2][2] == (1, 2, 3)  # fell exactly 3 rows


def test_level_up_after_ten_lines():
    g = make_game()
    g.lines = 9
    g.level = 1
    fill_rows(g, 1)
    g._clear_lines()
    assert g.lines == 10
    assert g.level == 2


def test_clear_uses_new_level_for_scoring():
    g = make_game()
    g.lines = 9
    g.level = 1
    fill_rows(g, 1)
    g._clear_lines()
    assert g.score == SCORE_TABLE[1] * 2  # level was already 2 when scoring


def test_drop_delay_decreases_with_level():
    g = make_game()
    d1 = g.drop_delay
    g.level = 10
    assert g.drop_delay < d1
    g.level = 10_000
    assert g.drop_delay == pytest.approx(0.08)


# --- gravity / update ----------------------------------------------------------


def test_gravity_advances_piece():
    g = make_game("O")
    y0 = g.piece.y
    g.update(1000)  # one gravity step at level 1 (0.6s)
    assert g.piece.y == y0 + 1


def test_update_is_noop_when_paused():
    g = make_game("O")
    g.paused = True
    y0 = g.piece.y
    g.update(5000)
    assert g.piece.y == y0


def test_update_is_noop_when_over():
    g = make_game("O")
    g.over = True
    y0 = g.piece.y
    g.update(5000)
    assert g.piece.y == y0


def test_gravity_locks_piece_at_floor():
    g = make_game("O")
    g.piece.y = ROWS - 2
    g.update(2000)
    assert sum(c == COLORS["O"] for row in g.board for c in row) == 4


# --- game over / reset ------------------------------------------------------------


def test_spawn_collision_ends_game():
    g = make_game()
    fill_top_rows(g, 4)
    g.spawn()
    assert g.over


def test_full_game_reaches_game_over():
    random.seed(42)
    g = Game()
    steps = 0
    while not g.over and steps < 10000:
        g.hard_drop()
        steps += 1
    assert g.over
    assert steps < 10000


def test_full_game_with_gravity_and_lock_delay():
    random.seed(3)
    g = Game()
    frames = 0
    while not g.over and frames < 200:
        g.update(5000)  # five seconds of game time per frame
        frames += 1
    assert g.over
    assert frames < 200


def test_reset_clears_everything():
    g = make_game()
    g.score = 500
    g.lines = 12
    g.level = 2
    g.paused = True
    g.over = True
    fill_rows(g, 3)
    g.reset()
    assert g.score == 0
    assert g.lines == 0
    assert g.level == 1
    assert not g.paused
    assert not g.over
    assert all(c is None for row in g.board for c in row)
    assert g.piece is not None


# --- rendering (headless) ----------------------------------------------------------


def test_render_frames_headless():
    import pygame

    pygame.init()
    try:
        screen = pygame.display.set_mode((tetris.WIDTH, tetris.HEIGHT))
        fonts = {
            "small": pygame.font.Font(None, 20),
            "med": pygame.font.Font(None, 30),
            "big": pygame.font.Font(None, 40),
            "huge": pygame.font.Font(None, 64),
        }
        g = Game()
        tetris.draw(screen, g, fonts)
        g.paused = True
        tetris.draw(screen, g, fonts)
        g.over = True
        tetris.draw(screen, g, fonts)
        pygame.display.flip()
    finally:
        pygame.quit()

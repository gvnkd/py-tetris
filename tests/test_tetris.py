import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

import pytest

from py_tetris.audio import (
    MUSIC_BEAT,
    THEME_A,
    THEME_BASS,
    Music,
    Sounds,
    _B1,
    _B2,
    _B_BRIDGE,
    _B_CLIMAX,
    _B_RUN,
    _B_RUN2,
    _B_WALKDOWN,
    _BRIDGE,
    _CLIMAX,
    _P1,
    _P2,
    _RUN,
    _RUN2,
    _WALKDOWN,
    _tone,
    note_freq,
    render_melody,
    render_voices,
)
from py_tetris.background import Background
from py_tetris.constants import (
    ARR_INTERVAL,
    BOT_THINK_INTERVAL,
    CLEAR_FLASH_DURATION,
    COLS,
    DAS_DELAY,
    HEIGHT,
    LOCK_DELAY,
    MAX_LOCK_RESETS,
    ROWS,
    SCORE_TABLE,
    SPRINT_TARGET,
    WIDTH,
)
from py_tetris.game import Bot, Game, evaluate_placement
from py_tetris.highscore import save_highscore
from py_tetris.input import AutoRepeat
from py_tetris.pieces import BOX, COLORS, I_KICKS, JLSTZ_KICKS, Piece, SHAPES, rotate_cells
from py_tetris.render import draw


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
    assert g.last_cleared == 1


def test_lock_reports_no_clear():
    g = make_game("O")
    g.lock()
    assert g.last_cleared == 0
    assert g.clear_flash == 0


def test_clear_flash_set_on_clear_and_expires():
    g = make_game("I")
    g.piece.x = 3
    g.piece.y = ROWS - 2
    for x in range(COLS):
        if not (3 <= x <= 6):
            g.board[ROWS - 1][x] = (5, 5, 5)
    assert g.lock() == 1
    assert g.clear_flash == CLEAR_FLASH_DURATION
    g.update(CLEAR_FLASH_DURATION * 1000 + 50)
    assert g.clear_flash == 0


def test_clear_flash_frozen_when_paused():
    g = make_game()
    g.clear_flash = CLEAR_FLASH_DURATION
    g.paused = True
    g.update(1000)
    assert g.clear_flash == CLEAR_FLASH_DURATION


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


# --- T-spins, back-to-back, combos -------------------------------------------------


def setup_tspin_double(g: Game) -> None:
    """Classic T-spin double slot: T (state 2, facing down) at x=1, y=ROWS-3."""
    c = (5, 5, 5)
    for x in (0, 1, 3, 4):  # overhang above
        g.board[ROWS - 3][x] = c
    for x in (0, 4, 5, 6, 7, 8, 9):
        g.board[ROWS - 2][x] = c
    for x in (0, 1, 3, 4, 5, 6, 7, 8, 9):
        g.board[ROWS - 1][x] = c
    p = Piece("T")
    p.cells = rotate_cells(rotate_cells(p.cells, 1, BOX["T"]), 1, BOX["T"])
    p.state = 2
    p.x, p.y = 1, ROWS - 3
    g.piece = p
    g.last_action = "rotate"


def setup_tetris(g: Game, gap=(3, 4, 5, 6)) -> None:
    """Four rows ready for a TETRIS: I piece completes the bottom row."""
    c = (5, 5, 5)
    for row in (ROWS - 4, ROWS - 3, ROWS - 2):
        for x in range(COLS):
            g.board[row][x] = c
    for x in range(COLS):
        if x not in gap:
            g.board[ROWS - 1][x] = c
    p = Piece("I")
    p.x, p.y = min(gap), ROWS - 2
    g.piece = p
    g.last_action = "drop"


def test_tspin_full_double():
    g = Game(highscore=0)
    setup_tspin_double(g)
    assert g.lock() == 2
    assert g.last_tspin == "full"
    assert g.score == 1200  # T-spin double, level 1
    assert g.combo == 1
    assert g.b2b_active


def test_tspin_mini_single():
    g = Game(highscore=0)
    c = (5, 5, 5)
    g.board[ROWS - 3][1] = c  # only ONE front corner (state 0 faces up)
    for x in (0, 4, 5, 6, 7, 8, 9):
        g.board[ROWS - 2][x] = c
    for x in (0, 1, 3, 4, 5, 6, 7, 8, 9):
        g.board[ROWS - 1][x] = c
    g.piece = Piece("T")  # state 0 at x=3, y=ROWS-3
    g.piece.x, g.piece.y = 1, ROWS - 3
    g.last_action = "rotate"
    assert g.lock() == 1
    assert g.last_tspin == "mini"
    assert g.score == 200
    assert not g.b2b_active  # mini single is not "difficult"


def test_tspin_requires_rotation():
    g = Game(highscore=0)
    setup_tspin_double(g)
    g.last_action = "move"  # slid in, not rotated in
    assert g.lock() == 2
    assert g.last_tspin == ""
    assert g.score == 300  # plain double


def test_tspin_zero_clear_scores():
    g = Game(highscore=0)
    c = (5, 5, 5)
    for x in (0, 1, 3, 4):
        g.board[ROWS - 3][x] = c
    for x in (0, 4):
        g.board[ROWS - 2][x] = c
        g.board[ROWS - 1][x] = c
    for x in (1, 3):
        g.board[ROWS - 1][x] = c
    p = Piece("T")
    p.cells = rotate_cells(rotate_cells(p.cells, 1, BOX["T"]), 1, BOX["T"])
    p.state = 2
    p.x, p.y = 1, ROWS - 3
    g.piece = p
    g.last_action = "rotate"
    assert g.lock() == 0
    assert g.last_tspin == "full"
    assert g.score == 400
    assert g.combo == 0  # no lines: combo neither advances nor resets


def test_back_to_back_bonus():
    g = Game(highscore=0)
    setup_tetris(g)
    g.lock()
    assert g.score == 800  # TETRIS, no b2b yet
    assert g.b2b_active
    setup_tspin_double(g)
    g.lock()
    # T-spin double x1.5 + combo (2nd consecutive clear) x50
    assert g.score == 800 + int(1200 * 1.5) + 50


def test_back_to_back_broken_by_normal_clear():
    g = Game(highscore=0)
    setup_tetris(g)
    g.lock()  # 800, b2b active
    c = (5, 5, 5)
    for x in range(COLS):
        if x not in (0, 1, 2, 3):
            g.board[ROWS - 1][x] = c
    p = Piece("I")
    p.x, p.y = 0, ROWS - 2
    g.piece = p
    g.last_action = "drop"
    g.lock()  # plain single: 100, breaks b2b; combo +50
    assert g.score == 800 + 100 + 50
    assert not g.b2b_active
    setup_tetris(g)
    g.lock()  # TETRIS again: 800 (no multiplier), combo +100
    assert g.score == 800 + 100 + 50 + 800 + 100


def test_combo_counts_consecutive_clears():
    g = Game(highscore=0)
    c = (5, 5, 5)
    for gap in ((0, 1, 2, 3), (5, 6, 7, 8)):
        for x in range(COLS):
            if x not in gap:
                g.board[ROWS - 1][x] = c
        p = Piece("I")
        p.x, p.y = min(gap), ROWS - 2
        g.piece = p
        g.last_action = "drop"
        g.lock()
    assert g.combo == 2
    # a lock without clears resets the combo
    g.piece = Piece("O")
    g.last_action = "drop"
    g.lock()
    assert g.combo == 0


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


# --- game modes ---------------------------------------------------------------------


def test_sprint_wins_at_target_lines():
    g = Game(game_mode="sprint", highscore=0)
    g.lines = SPRINT_TARGET - 1
    c = (5, 5, 5)
    for x in range(COLS):
        if x not in (3, 4, 5, 6):
            g.board[ROWS - 1][x] = c
    p = Piece("I")
    p.x, p.y = 3, ROWS - 2
    g.piece = p
    g.lock()
    assert g.over
    assert g.won
    assert g.lines == SPRINT_TARGET


def test_sprint_level_stays_fixed():
    g = Game(game_mode="sprint", highscore=0)
    c = (5, 5, 5)
    for row in (ROWS - 5, ROWS - 4, ROWS - 3, ROWS - 2):
        for x in range(COLS):
            g.board[row][x] = c
    for x in range(COLS):
        if x not in (3, 4, 5, 6):
            g.board[ROWS - 1][x] = c
    p = Piece("I")
    p.x, p.y = 3, ROWS - 2
    g.piece = p
    g.lock()
    assert g.lines == 5
    assert g.level == 1  # no speed-up in sprint


def test_ultra_counts_down_and_ends():
    g = Game(game_mode="ultra", highscore=0)
    assert g.level == 5
    g.time_left = 0.5
    g.update(1000)
    assert g.over
    assert not g.won
    assert g.time_left == 0


def test_ultra_level_stays_fixed():
    g = Game(game_mode="ultra", highscore=0)
    g.lines = 15
    for row in (ROWS - 5, ROWS - 4, ROWS - 3, ROWS - 2):
        for x in range(COLS):
            g.board[row][x] = (5, 5, 5)
    for x in range(COLS):
        if x not in (3, 4, 5, 6):
            g.board[ROWS - 1][x] = (5, 5, 5)
    p = Piece("I")
    p.x, p.y = 3, ROWS - 2
    g.piece = p
    g.lock()
    assert g.lines == 20
    assert g.level == 5  # fixed at ultra level


def test_marathon_level_still_rises():
    g = Game(game_mode="marathon", highscore=0)
    g.lines = 9
    c = (5, 5, 5)
    for x in range(COLS):
        if x not in (3, 4, 5, 6):
            g.board[ROWS - 1][x] = c
    p = Piece("I")
    p.x, p.y = 3, ROWS - 2
    g.piece = p
    g.lock()
    assert g.lines == 10
    assert g.level == 2


# --- DAS/ARR ------------------------------------------------------------------------


def test_auto_repeat_no_steps_before_das():
    ar = AutoRepeat()
    ar.press()
    assert ar.tick(DAS_DELAY * 1000 - 1) == 0  # just under DAS: nothing yet


def test_auto_repeat_das_then_arr():
    ar = AutoRepeat()
    ar.press()
    assert ar.tick(int(DAS_DELAY * 1000)) == 1  # first repeat at DAS
    assert ar.tick(int(ARR_INTERVAL * 1000) - 1) == 0
    assert ar.tick(1) == 1  # next repeat at ARR
    assert ar.tick(int(ARR_INTERVAL * 1000)) == 1


def test_auto_repeat_release_stops():
    ar = AutoRepeat()
    ar.press()
    ar.tick(1000)
    ar.release()
    assert ar.tick(1000) == 0


def test_auto_repeat_press_restarts_das():
    ar = AutoRepeat()
    ar.press()
    ar.tick(1000)
    ar.press()  # re-press: DAS window restarts
    assert ar.tick(DAS_DELAY * 1000 - 1) == 0


def test_auto_repeat_catches_up_on_large_dt():
    ar = AutoRepeat()
    ar.press()
    total_ms = 1000
    steps = ar.tick(total_ms)
    expected = 1 + int((total_ms / 1000 - DAS_DELAY) // ARR_INTERVAL)
    assert steps == expected


# --- sounds (headless) --------------------------------------------------------------


def test_tone_renders_valid_pcm():
    data = _tone(440.0, 100, 0.5)
    assert len(data) == 2 * (22050 * 100 // 1000)
    assert _tone(440.0, 100, 0.5) == data  # deterministic


def test_sounds_build_without_mixer():
    s = Sounds.build()  # headless: no mixer -> no sounds, no crash
    s.play("move")


def test_sounds_disabled_plays_nothing():
    s = Sounds(enabled=False)
    s.play("move")


def test_note_freq_reference_values():
    assert note_freq("A4") == pytest.approx(440.0)
    assert note_freq("E5") == pytest.approx(659.255, rel=1e-3)
    assert note_freq("C5") == pytest.approx(523.251, rel=1e-3)
    assert note_freq("G4") == pytest.approx(392.0, rel=1e-3)
    assert note_freq("B4") == pytest.approx(493.883, rel=1e-3)
    # an octave up doubles the frequency
    assert note_freq("E4") == pytest.approx(note_freq("E5") / 2)


def test_render_melody_rest_is_silence():
    data = render_melody((("R", 1), ("E5", 1)), 0.1, rate=8000)
    assert len(data) == 2 * 2 * 800  # two beats, 16-bit
    first_beat = data[:1600]
    assert first_beat == b"\x00" * 1600
    second_beat = data[1600:]
    peak = max(
        abs(int.from_bytes(second_beat[i : i + 2], "little", signed=True))
        for i in range(0, len(second_beat), 2)
    )
    assert peak > 0


def test_theme_a_is_well_formed():
    # transcription of tmp/korobeiniki_score_transcribed.txt:
    # (P1+P2) x4 + bridge + G5 climax + runs x4 + walkdown = 380 beats
    assert sum(b for _, b in _P1) == 32
    assert sum(b for _, b in _P2) == 32
    assert sum(b for _, b in _BRIDGE) == 56
    assert sum(b for _, b in _CLIMAX) == 8
    assert sum(b for _, b in _RUN) == 32
    assert sum(b for _, b in _RUN2) == 32
    assert sum(b for _, b in _WALKDOWN) == 60
    assert sum(beats for _, beats in THEME_A) == 380.0
    # the 64-beat phrase P1+P2 opens the piece and repeats 4 times
    assert THEME_A[: len(_P1) + len(_P2)] == _P1 + _P2
    assert THEME_A[len(_P1) + len(_P2) : 2 * (len(_P1) + len(_P2))] == _P1 + _P2
    for name, _ in THEME_A:
        if name != "R":
            note_freq(name)  # must not raise
    assert THEME_A[0][0] == "E5"  # opens on the accented high E
    assert THEME_A[-1][0] == "G4"  # ends on the walkdown's final G


def test_theme_bass_is_well_formed():
    # the bass is the score's lower voice; each section matches its
    # lead section's length so the voices stay in sync
    assert sum(b for _, b in _B1) == 32
    assert sum(b for _, b in _B2) == 32
    assert sum(b for _, b in _B_BRIDGE) == 56
    assert sum(b for _, b in _B_CLIMAX) == 8
    assert sum(b for _, b in _B_RUN) == 32
    assert sum(b for _, b in _B_RUN2) == 32
    assert sum(b for _, b in _B_WALKDOWN) == 60
    assert sum(beats for _, beats in THEME_BASS) == 380.0
    # same statement structure as THEME_A: phrase x4, bridge, climax,
    # runs x4, walkdown
    assert THEME_BASS[: len(_B1) + len(_B2)] == _B1 + _B2
    assert THEME_BASS[len(_B1) + len(_B2) : 2 * (len(_B1) + len(_B2))] == _B1 + _B2
    for name, _ in THEME_BASS:
        if name != "R":
            assert note_freq(name) < note_freq("C4")  # stays under the lead
    assert THEME_BASS[0][0] == "R"  # enters after the lead's first two beats
    assert THEME_BASS[-1][0] == "R"  # walkdown rests: the lead is already the bass


def test_render_melody_bass_mix():
    lead = (("R", 2), ("E5", 2))
    bass = (("B3", 4),)
    data = render_melody(lead, 0.1, rate=8000, bass=bass)
    # covers the full 4 beats (per-note rounding allows a few samples)
    assert abs(len(data) / 2 - 4 * 800) < 50
    assert data == render_melody(lead, 0.1, rate=8000, bass=bass)  # deterministic
    # where the lead rests, only the bass sounds: not silent
    first_beat = data[:1600]
    peak = max(
        abs(int.from_bytes(first_beat[i : i + 2], "little", signed=True))
        for i in range(0, len(first_beat), 2)
    )
    assert peak > 0
    # without a bass the output is the lead alone (unchanged behavior)
    assert render_melody(lead, 0.1, rate=8000) == render_melody(
        lead, 0.1, rate=8000, bass=None
    )
    # a loud mix is clamped to the 16-bit range, not lost
    mono = render_melody(lead, 0.1, rate=8000, vol=0.9, bass=bass, bass_vol=0.9)
    samples = [
        int.from_bytes(mono[i : i + 2], "little", signed=True) for i in range(0, len(mono), 2)
    ]
    assert max(samples) == 32767


def test_theme_render_with_bass_deterministic():
    a = render_melody(THEME_A, MUSIC_BEAT, rate=8000, bass=THEME_BASS)
    assert a == render_melody(THEME_A, MUSIC_BEAT, rate=8000, bass=THEME_BASS)
    # covers the full 380 beats (per-note rounding allows a few samples)
    expected = 8000 * MUSIC_BEAT * 380
    assert abs(len(a) / 2 - expected) < 200


def test_render_voices_length_aligned():
    # polyphonic playback: lead and bass are separate buffers that must have
    # the SAME sample count, or their independent play(-1) loops drift apart
    bufs = render_voices(rate=8000)
    assert len(bufs) == 2  # lead + bass
    lens = {len(b) for b in bufs}
    assert len(lens) == 1  # length-aligned
    # covers the full 380 beats (a few samples of rounding slack)
    expected = 8000 * MUSIC_BEAT * 380
    assert abs(lens.pop() / 2 - expected) < 200


def test_music_start_play_stop_without_mixer():
    m = Music()
    m.start()
    m.play()
    m.stop()
    m.start()  # idempotent
    m.play()
    m.stop()


# --- line clears, scoring, levels ---------------------------------------------


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_clear_lines_mechanics(n):
    g = make_game()
    g.level = 1
    fill_rows(g, n)
    g._clear_lines()
    assert g.lines == n
    assert all(c is None for c in g.board[ROWS - 1])


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_score_clear_by_table(n):
    g = make_game()
    g.level = 1
    score0 = g.score
    g._score_clear(n, "")
    assert g.score - score0 == SCORE_TABLE[n]


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


def test_score_clear_uses_level_set_by_clear():
    g = make_game()
    g.lines = 9
    g.level = 1
    fill_rows(g, 1)
    g._clear_lines()  # lines 9 -> 10, level 1 -> 2
    assert g.level == 2
    score0 = g.score
    g._score_clear(1, "")  # lock() scores after the level update
    assert g.score - score0 == SCORE_TABLE[1] * 2


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


# --- placement evaluation & bot -------------------------------------------------------


def test_evaluate_prefers_line_clear():
    board = [[None] * COLS for _ in range(ROWS)]
    for x in range(COLS):
        if x not in (2, 3, 4, 5):
            board[ROWS - 1][x] = (1, 1, 1)
    i_cells = frozenset(SHAPES["I"])
    clear = evaluate_placement(board, i_cells, 2, ROWS - 2)
    noclear = evaluate_placement(board, i_cells, 0, ROWS - 2)
    assert clear > noclear


def test_evaluate_penalizes_holes():
    board = [[None] * COLS for _ in range(ROWS)]
    o = frozenset(SHAPES["O"])
    grounded = evaluate_placement(board, o, 2, ROWS - 2)
    floating = evaluate_placement(board, o, 2, ROWS - 3)
    assert grounded > floating


def test_evaluate_penalizes_height():
    board = [[None] * COLS for _ in range(ROWS)]
    o = frozenset(SHAPES["O"])
    low = evaluate_placement(board, o, 2, ROWS - 2)
    high = evaluate_placement(board, o, 2, 0)
    assert low > high


def test_evaluate_height_uses_topmost_cell():
    # column 0 filled only in the bottom row: height 1 -> -2*1 - 1 (bump) = -3
    a = [[None] * COLS for _ in range(ROWS)]
    a[ROWS - 1][0] = (1, 1, 1)
    assert evaluate_placement(a, frozenset(), 0, 0) == -3
    # column 0 filled rows 16-19: height must be 4 (topmost), not 1 (bottommost)
    b = [[None] * COLS for _ in range(ROWS)]
    for row in range(ROWS - 4, ROWS):
        b[row][0] = (1, 1, 1)
    assert evaluate_placement(b, frozenset(), 0, 0) == -12


def test_bot_survives_long_games():
    # the depth-2 bot outlasts hundreds of pieces (depth-1 died at ~300)
    # 100ms ticks: coarse ticks (e.g. 1000ms) let gravity lock pieces
    # before the bot's plan executes, which is not how the real loop runs
    random.seed(11)
    g = Game(mode="demo")
    bot = Bot()
    steps = 0
    while g.lines < 50 and steps < 5000 and not g.over:
        bot.step(g, 100)
        g.update(100)
        steps += 1
    assert g.lines >= 50
    assert steps < 5000


def test_bot_ignores_human_games():
    random.seed(5)
    g = Game(mode="human")
    bot = Bot()
    piece0 = g.piece
    bot.step(g, 10000)
    assert g.piece is piece0  # untouched


def test_bot_thinks_before_acting():
    random.seed(2)
    g = Game(mode="demo")
    bot = Bot()
    piece0 = g.piece
    for _ in range(5):  # 500ms < BOT_THINK_INTERVAL: no plan yet
        bot.step(g, 100)
        g.update(100)
    assert g.piece is piece0
    for _ in range(30):  # plan + animated execution finishes the drop
        bot.step(g, 100)
        g.update(100)
        if g.piece is not piece0:
            break
    assert g.piece is not piece0


def test_bot_animates_moves_step_by_step():
    # a plan with several actions takes several ticks, not one
    random.seed(2)
    g = Game(mode="demo")
    bot = Bot()
    steps = 0
    while not bot.queue and steps < 60:  # wait for a non-trivial plan
        bot.step(g, 100)
        g.update(100)
        steps += 1
    assert bot.queue  # at least one rotate/move to animate
    piece = g.piece
    bot.step(g, 100)  # one tick: at most one micro-step
    assert g.piece is piece  # no instant drop
    for _ in range(30):
        bot.step(g, 100)
        g.update(100)
        if bot.phase == "pause":
            break
    assert bot.phase == "pause"  # finished with the human-like pause


def test_bot_demo_pace():
    # ~1 drop per 1.3-1.6s: a couple in 3s, not a machine gun
    random.seed(2)
    g = Game(mode="demo")
    bot = Bot()
    drops = 0
    in_pause = False
    for _ in range(30):
        bot.step(g, 100)
        g.update(100)
        if bot.phase == "pause":
            if not in_pause:
                drops += 1
            in_pause = True
        else:
            in_pause = False
    assert 1 <= drops <= 3


def test_bot_uses_hold_when_beneficial():
    g = Game(highscore=0)
    c = (5, 5, 5)
    for x in range(COLS):
        if x not in (3, 4, 5, 6):
            g.board[ROWS - 1][x] = c  # bottom row waits for the I in hold
    g.piece = Piece("T")
    g.held_kind = "I"
    g.can_hold = True
    Bot().play(g)
    assert g.held_kind == "T"  # bot held the T to let the I finish the line
    assert g.lines == 1


# --- rendering (headless) ----------------------------------------------------------


def test_render_frames_headless():
    import pygame

    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        fonts = {
            "tiny": pygame.font.Font(None, 16),
            "small": pygame.font.Font(None, 20),
            "med": pygame.font.Font(None, 30),
            "big": pygame.font.Font(None, 40),
            "huge": pygame.font.Font(None, 64),
        }
        g = Game(mode="demo")
        bg = Background(WIDTH, HEIGHT)
        draw(screen, g, fonts, bg)
        g.mode = "human"
        draw(screen, g, fonts, bg)
        g.last_cleared = 2
        g.clear_flash = CLEAR_FLASH_DURATION
        draw(screen, g, fonts, bg)  # with the line-clear flash
        g.paused = True
        draw(screen, g, fonts, bg)
        g.over = True
        draw(screen, g, fonts, bg)
        pygame.display.flip()
    finally:
        pygame.quit()


def test_background_animates():
    import pygame

    pygame.init()
    try:
        bg = Background(WIDTH, HEIGHT, rng=random.Random(42))
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        screen.fill((0, 0, 0))
        bg.draw(screen)
        first = screen.copy()
        for _ in range(120):  # ~2 s of frames
            bg.update(16.7)
            screen.fill((0, 0, 0))
            bg.draw(screen)
        diff = sum(
            1
            for x in range(0, WIDTH, 5)
            for y in range(0, HEIGHT, 5)
            if screen.get_at((x, y))[:3] != first.get_at((x, y))[:3]
        )
        assert diff > 40  # the backdrop visibly moves
    finally:
        pygame.quit()


def test_background_deterministic_with_seed():
    import pygame

    def frame() -> bytes:
        bg = Background(WIDTH, HEIGHT, rng=random.Random(7))
        for _ in range(30):
            bg.update(16.7)
        s = pygame.display.set_mode((WIDTH, HEIGHT))
        s.fill((0, 0, 0))
        bg.draw(s)
        return pygame.image.tostring(s, "RGB")

    pygame.init()
    try:
        assert frame() == frame()
    finally:
        pygame.quit()


def test_background_wraps_offscreen_drifters():
    import pygame

    pygame.init()
    try:
        bg = Background(WIDTH, HEIGHT, rng=random.Random(1))
        for _ in range(3600):  # ~60 s at 60 fps
            bg.update(16.7)
        for d in bg._drifters:
            assert -60 <= d.y < HEIGHT + 60
    finally:
        pygame.quit()

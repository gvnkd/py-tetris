# Project Memory

## Overview

Tetris in Python (pygame), packaged and run via a Nix flake. The game lives in the `py_tetris` package (src layout); the original single-file `tetris.py` was split into modules (M5).

- `src/py_tetris/` — the package:
  - `constants.py` — board/window/timing constants, colors, `Color` type, mode-button rects
  - `pieces.py` — SHAPES, BOX, COLORS, SRS kick tables, `rotate_cells`, `Piece`
  - `audio.py` — SFX tones, Korobeiniki music table (`THEME_A`), `note_freq`, `render_melody`, `Sounds`, `Music`
  - `background.py` — `Background`: animated backdrop (soft drifting glows + falling low-alpha tetromino silhouettes); `update(dt_ms)` + `draw(screen)`, seedable via `rng`
  - `highscore.py` — `~/.config/py-tetris/highscore` load/save (XDG honored)
  - `game.py` — board helpers (`collides`, `stamp_cells`, `clear_lines`, `place_piece`, `evaluate_board`, `rest_y`), `Game`, `evaluate_placement`, `Bot` (pure logic, no pygame)
  - `input.py` — `AutoRepeat` (DAS/ARR timing, pure logic)
  - `render.py` — all pygame drawing
  - `app.py` — `main()` (pygame init, event loop); `__main__.py` enables `python -m py_tetris`
- `pyproject.toml` — PEP 621 metadata, setuptools backend, `py-tetris = "py_tetris.app:main"` script, `[tool.mypy] strict`, pytest config (replaced legacy `setup.py`)
- `flake.nix` / `flake.lock` — nixpkgs pinned to `nixos-26.05` (stable); `packages`, `apps`, `devShells`, `checks` for 4 systems
- `py-tetris.desktop` + `icons/` — desktop entry and hicolor icons, installed by the package
- `tests/test_tetris.py` — headless pytest suite

## Commands

- Run game: `nix run .#`
- Dev shell (live editing): `nix develop .#` then `python3 -m py_tetris` (the shellHook sets `PYTHONPATH=src`)
- Build: `nix build .#`
- Tests + mypy: `nix flake check .#` (hermetic, runs `checks.default` pytest and `checks.mypy`)
- Tests in dev shell: `python3 -m pytest tests -v`
- Type check in dev shell: `python3 -m mypy` (config in pyproject: strict, `src/py_tetris`)
- Controls: arrows move, Down soft drop, Up/X and Z rotate, Space hard drop, C hold, M mute (SFX + music), P pause, R restart (after game over), Q quit
- The game starts in **demo mode** (an autoplay bot plays). Click a mode button in the sidebar — **MARATHON** / **SPRINT** (20 lines to win) / **ULTRA** (2 min, level 5) — or press R/Enter (marathon) to take over; the buttons also restart in human mode. Demo auto-restarts ~2s after its own game over.

## Nix findings (hard-won — do not rediscover)

- nix 2.34 flake apps use the new schema: `type = "app"; program = "..."`. The legacy `command` attribute is rejected (`attribute 'apps.<system>.default.program' does not exist`).
- `buildPythonApplication` requires an explicit build format: with a `pyproject.toml` use `pyproject = true` + `build-system = [ pkgs.python3Packages.setuptools ]` (builds a wheel via `python -m build`); legacy `format = "setuptools"` works for setup.py. Without either: "does not configure a `format`". Set `doInstallCheck = false` so the package build doesn't run the test suite (that is `checks.default`'s job).
- Runtime Python deps go in `dependencies = [ ... ]` (PEP 621 style; mapped to `propagatedBuildInputs` and injected into wrapped scripts via `site.addsitedir`). There is no `pythonImports` attribute in current nixpkgs — it is silently ignored, producing a package that crashes with `ModuleNotFoundError` at runtime.
- The local binary cache `http://192.168.0.254:5001` (in the user's nix substituters) works reliably (as of 2026-08) — no `--option substituters "https://cache.nixos.org"` workaround needed anymore (it used to time out and abort builds). Builds also run on remote builder `ssh-ng://builder`.
- `nix shell .#` resolves to `packages.default`, not the devShell. Use `.#devShells.<system>.default` explicitly.
- `nix shell --command` in this nix version execs argv directly with no shell: builtins (`echo ...`) and multi-word commands fail. Pass real binaries only.
- **Nix interpolates `${...}` inside string literals** (both `"..."` and `''...''`): `${FOO}` becomes a Nix variable reference (undefined → error), and `${FOO:+...}` is mangled (the `${`/`}` are stripped, inner text kept) — silently corrupting any shell parameter expansion you put in a `shellHook`/`postInstall`. So a hook line like `export X="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"` reaches the shell as `...srcPYTHONPATH:+:$PYTHONPATH`, breaking the path. **Never use `${...}` in a Nix string meant for a shell** — use bare `$VAR`, `$(...)`, and `if [ -n "$VAR" ]; then ... else ...; fi` instead (all pass through verbatim). The devShell `shellHook` follows this rule.
- The built package uses Python 3.13 on nixos-26.05 (`lib/python3.13/site-packages`) and has no `bin/python` — invoke `bin/py-tetris`.
- Flake source of a git worktree is computed from the **git state**: modified tracked files are included, but **untracked files are excluded**. New files (e.g. `tests/`) must be at least `git add`ed before they appear in flake builds. (Dirty state is reported as `<rev>-dirty`.)
- nixpkgs is pinned to **nixos-26.05 (stable)** in `flake.lock`. There, `python3Packages.pygame` is upstream **pygame** (dist-info name `pygame`); on nixos-unstable it is pygame-**ce** (dist-name `pygame-ce`). `pyproject.toml` therefore depends on **`pygame`** (upstream dist name) so the built wheel's `Requires-Dist` passes `pythonRuntimeDepsCheck` against 26.05's `dependencies = [ python3Packages.pygame ]` — no `dontCheckRuntimeDeps` needed. The check only matches dist-info **names**: if the flake is ever switched to unstable, flip the pyproject dep to `pygame-ce` (or re-add `dontCheckRuntimeDeps = true`). `pythonRelaxDeps` does NOT exist on 26.05 — don't use it.
- A **stale devShell environment poisons `nix run`**: if the session's `PYTHONPATH` contains another nixpkgs revision's python site-packages (e.g. an old `nix develop` still active), the game's `import pygame` picks the wrong (ABI-incompatible) pygame → `ModuleNotFoundError: No module named 'pygame.base'`. Verify launches with `env -u PYTHONPATH` (add `PYTHONPATH=src` for local package runs).
- Hermetic check derivations need `doCheck = true` (stdenv default is false — checkPhase is silently skipped) and an `installPhase = "mkdir -p $out"` or the build fails with "failed to produce output path".
- `python3.withPackages (ps: ...)` is the right way to get a buildable env with `python` + modules on PYTHONPATH; its `.env` attribute is interactive-only and fails under `nix shell --expr`.

## Testing / verification

- `tests/test_tetris.py` — 102 headless pytest cases: bag fairness, SRS kick tables (spec values + inverse-consistency) and rotation math (incl. a fuzz over positions), movement bounds, lock delay (expiry, resets, 15-reset cap), soft/hard drop scoring, line clears, T-spins (full/mini/zero-clear, rotation requirement), back-to-back + combo scoring, game modes (sprint win, fixed levels, ultra countdown), hold semantics, highscore load/save (tmp_path + XDG_CONFIG_HOME monkeypatch), DAS/ARR repeat timing, gravity/pause, game over, bot survival + hold usage + animation/pace, placement evaluator (clears/holes/height/topmost-cell regression), procedural-sound determinism, music (note frequencies, rest silence, theme well-formedness, bass theme well-formedness, bass mix determinism/clamping, polyphonic voice length-alignment, mixer-less no-op), headless rendered frames (SDL dummy driver, incl. demo mode and clear flash), animated background (frame-to-frame motion, seed determinism, offscreen drifter wrap).
- Run hermetically: `nix flake check .#` (flake `checks`: `default` = `PYTHONPATH=src python -m pytest`, `mypy` = `mypy --strict src/py_tetris`). CI (`.github/workflows/ci.yml`) runs `nix build .#` + `nix flake check` on push/PR. CI nix actions: `DeterminateSystems/nix-installer-action` + `nix-community/cache-nix-action` (the old `DeterminateSystems/nix-cache-action` repo is gone — 404).
- The whole package is fully type-hinted and mypy `--strict` clean (config in `pyproject.toml`).
- Headless run check:
  `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 6 nix run .#`
  Expect the `pygame 2.6.x ... (SDL ...)` banner and no traceback; being killed by timeout = success. (On nixos-unstable the banner says `pygame-ce` instead.)
- A `fc-list` UserWarning in sandboxed runs is harmless (fontconfig timeout); `SysFont` falls back to the bundled default font. Tests use `pygame.font.Font(None, ...)` (bundled font) to avoid fontconfig entirely.

## Git

- Commits so far: `a0f677c` initial game+flake, `8ffe056` project memory + milestones, `94344dc` M2 (tests, type hints, flake checks, CI), `a38361b` M1 (hold, lock delay, SRS, highscore, sounds), `354e0e8` demo bot + NEW GAME button, `f67094f` full 45-bar Korobeiniki music (score transcription) + ♩=190, `85e5a75` reference files to gitignored `tmp/`, `5e7273d` M5 (py_tetris package + pyproject), `a533a8e` music rebuilt from the score transcription txt, `448392a` M3 (desktop entry, nixos-26.05 pin, README), `c0abe96` M4 (DAS/ARR, T-spin scoring, flash, depth-2 bot, game modes), `0597efa` bot move animation (human-like pacing), `4c897e7` CI cache-action repo fix, `eb65ae8` project docs/memory update, `7c40952` CI cache-nix-action required inputs, `bb3594b` animated background, `e92a16a` DevShell shellHook dollar-brace fix, `fb61592` cleanup (line-clear helpers, runtime-deps check, UI/devShell fixes).
- `.envrc` (`use flake`) committed; `.direnv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `result`, `*.swp`, `tmp/` gitignored.

## Gameplay notes

- Rotation uses full SRS: `JLSTZ_KICKS` / `I_KICKS` tables keyed by (from_state, to_state); `Piece.state` tracks 0/1/2/3. Kicks are in board coordinates (+dy = down); the O piece never kicks.
- Lock delay: grounded pieces get `LOCK_DELAY` (0.5s), resettable by move/rotate up to `MAX_LOCK_RESETS` (15) per grounded spell; `Game.lock()` returns the number of lines cleared.
- Hold: one per piece (`can_hold`), re-allowed after any downward move or soft drop; the swap path must not touch `next_kind`.
- High score: `~/.config/py-tetris/highscore` (XDG_CONFIG_HOME honored, for tests); loaded in `Game.__init__`, saved when the game ends.
- Sounds: procedural sine tones (`_tone` → 16-bit mono PCM buffers), built in `Sounds.build()` after mixer init; all optional — the game runs fine with no audio device. One tone per action: `move`/`rotate`/`drop`/`hard`/`hold`/`clear`/`tetris`/`tspin`/`over`. `M` toggles SFX + music. Line clears play `tspin` (T-spin) / `tetris` (4 lines) / `clear` (1–3) via `Game.last_tspin`/`Game.last_cleared`, consumed by `main()` after the frame renders.
- Music: "The Peddlers" (Korobeiniki, the classic Tetris theme — public-domain folk melody, E minor, 4/4). Transcribed from `tmp/korobeiniki_score_transcribed.txt` (user-provided: per-octave staff lines, one char = one eighth note; 29 "bars" of 26 slots): the 64-beat phrase `_P1` (8-bar motif) + `_P2` (D5-F5-A5-G5 flourish + resolution) stated four times, then `_BRIDGE` (quarter notes, 56 beats) → `_CLIMAX` (held G5, 8 beats — the score's fermata bar) → `_RUN`/`_RUN2` run-throughs (4×32) → `_WALKDOWN` (arpeggio ending on G4, 60 beats). 380 beats ≈ 2min loop at ♩=190 (score says 170). `note_freq` + `render_melody` (PCM buffer, envelope per note; renders in ~0.5s) + `Music` (persistent `play(-1)` channel). `mixer.pre_init(22050, -16, 1, 512)` must precede `pygame.init()` so the buffer renders at the mixer rate. Verify rendered pitch/duration by zero-crossing analysis of the PCM (no audio on this machine). Repeated note onsets (e.g. the A4s in the motif) are kept as separate events so they re-articulate. **Two voices, polyphonic**: the lead is a square wave; a sine **bass** (`THEME_BASS` = `_B1`/`_B2`/… per-section tables, the score's lower 4|/3| staff dropped to octave 3, same beat lengths as the lead sections). `render_voices(rate)` renders the two as **separate, length-aligned** mono buffers (each padded to the same sample count so independent `play(-1)` loops never drift — per-note `int()` rounding otherwise makes them differ by ~23 samples). `Music` plays them on **separate mixer channels** (polyphonic), levels set by `LEAD_VOL`/`BASS_VOL` (0..1, independent) and tweakable at runtime via `Channel.set_volume`. `render_melody(..., bass=)` still returns the mono sum (used by tests); the walkdown bass rests — there the lead *is* the score's low voice.
- **`35149.mid` is NOT this melody** — it contains no E or B notes at all (different chromatic arrangement). The transcription txt (in `tmp/`) is the reference; the score PNGs are also there.
- Demo bot: `Bot.step()` paces the demo human-like — `BOT_THINK_INTERVAL` (0.6s) after a piece spawns (it falls a bit first), then **animates the plan** one rotation (`ROTATE_STEP` 0.15s) / one cell (`MOVE_STEP` 0.08s) at a time, `SETTLE` (0.15s) before a straight drop, and `BOT_DROP_PAUSE` (0.3s) idle after each drop (~0.8 pieces/s). If the planned piece gets locked mid-animation (fast gravity), the bot aborts and re-plans for the new piece. `Bot.play()` is the synchronous version (used by tests); `Bot.plan_move()` returns `(hold, rot, x)`. Planning: depth-2 lookahead — top-8 placements of the current piece (and of the held piece, when `can_hold`) × best depth-1 placement of the next piece on the simulated board; board scoring via `evaluate_placement`/`evaluate_board` (clears ×1000, −holes ×30, −Σheights ×2, −bumpiness). Plays 1000+ line games. `Game.mode` is `"demo"`/`"human"`; mode button rects: `MARATHON_RECT`/`SPRINT_RECT`/`ULTRA_RECT`.
- Scoring: guideline values — T-spin detection via 3-corner rule on the last action being a rotation (`_detect_tspin`, full = both front corners blocked); T-spin/mini tables in `TSPIN_SCORES`; back-to-back ×1.5 on consecutive difficult clears (TETRIS, T-spin 2+); combo +50×(n−1)×level. All in `Game._score_clear`.
- Input: DAS/ARR via `AutoRepeat` (`input.py`, pure logic): 170 ms DAS, 50 ms ARR; `pygame.key.set_repeat` is NOT used.
- FX: cleared rows flash white (`CLEAR_FLASH_DURATION`) with T-SPIN/COMBO text; `last_cleared`/`last_tspin` are consumed by `main()` after the frame renders.

## Known limitations (see `.opencode/milestones.md`)

- Demo bot is depth-2 greedy with hold usage (no deeper lookahead / no T-spin setup search); it plays 1000+ line games.
- Music is a square-wave lead + sine bass line (no chord voices, unlike the full piano arrangement); fixed tempo ♩≈190 (score: 170 + accelerando, flattened); the chordal sections are reduced to their top voice.
- Sprint gravity is level 1 (no official sprint speed); ultra has no per-line level scaling.

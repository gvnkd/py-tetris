# Project Memory

## Overview

Tetris in Python (pygame), packaged and run via a Nix flake. The game lives in the `py_tetris` package (src layout); the original single-file `tetris.py` was split into modules (M5).

- `src/py_tetris/` — the package:
  - `constants.py` — board/window/timing constants, colors, `Color` type, `NEW_GAME_RECT`
  - `pieces.py` — SHAPES, BOX, COLORS, SRS kick tables, `rotate_cells`, `Piece`
  - `audio.py` — SFX tones, Korobeiniki music table (`THEME_A`), `note_freq`, `render_melody`, `Sounds`, `Music`
  - `highscore.py` — `~/.config/py-tetris/highscore` load/save (XDG honored)
  - `game.py` — `Game`, `evaluate_placement`, `Bot` (pure logic, no pygame)
  - `render.py` — all pygame drawing
  - `app.py` — `main()` (pygame init, event loop); `__main__.py` enables `python -m py_tetris`
- `pyproject.toml` — PEP 621 metadata, setuptools backend, `py-tetris = "py_tetris.app:main"` script, `[tool.mypy] strict`, pytest config (replaced legacy `setup.py`)
- `flake.nix` / `flake.lock` — nixpkgs pinned to `nixos-unstable`; `packages`, `apps`, `devShells`, `checks` for 4 systems
- `tests/test_tetris.py` — headless pytest suite

## Commands

- Run game: `nix run .#`
- Dev shell (live editing): `nix develop .#` then `python3 -m py_tetris` (the shellHook sets `PYTHONPATH=src`)
- Build: `nix build .#`
- Tests + mypy: `nix flake check .#` (hermetic, runs `checks.default` pytest and `checks.mypy`)
- Tests in dev shell: `python3 -m pytest tests -v`
- Type check in dev shell: `python3 -m mypy` (config in pyproject: strict, `src/py_tetris`)
- Controls: arrows move, Down soft drop, Up/X and Z rotate, Space hard drop, C hold, M mute (SFX + music), P pause, R restart (after game over), Q quit
- The game starts in **demo mode** (an autoplay bot plays). Click the **NEW GAME** button in the sidebar (or press R/Enter) to take over; the button also restarts in human mode. Demo auto-restarts ~2s after its own game over.

## Nix findings (hard-won — do not rediscover)

- nix 2.34 flake apps use the new schema: `type = "app"; program = "..."`. The legacy `command` attribute is rejected (`attribute 'apps.<system>.default.program' does not exist`).
- `buildPythonApplication` requires an explicit build format: with a `pyproject.toml` use `pyproject = true` + `build-system = [ pkgs.python3Packages.setuptools ]` (builds a wheel via `python -m build`); legacy `format = "setuptools"` works for setup.py. Without either: "does not configure a `format`". Set `doInstallCheck = false` so the package build doesn't run the test suite (that is `checks.default`'s job).
- Runtime Python deps go in `dependencies = [ ... ]` (PEP 621 style; mapped to `propagatedBuildInputs` and injected into wrapped scripts via `site.addsitedir`). There is no `pythonImports` attribute in current nixpkgs — it is silently ignored, producing a package that crashes with `ModuleNotFoundError` at runtime.
- The local binary cache `http://192.168.0.254:5001` (in the user's nix substituters) times out and aborts the whole build. Workaround: `--option substituters "https://cache.nixos.org"`. Builds also run on remote builder `ssh-ng://builder`.
- `nix shell .#` resolves to `packages.default`, not the devShell. Use `.#devShells.<system>.default` explicitly.
- `nix shell --command` in this nix version execs argv directly with no shell: builtins (`echo ...`) and multi-word commands fail. Pass real binaries only.
- The built package uses Python 3.14 (`lib/python3.14/site-packages`) and has no `bin/python` — invoke `bin/py-tetris`.
- Flake source of a git worktree is computed from the **git state**: modified tracked files are included, but **untracked files are excluded**. New files (e.g. `tests/`) must be at least `git add`ed before they appear in flake builds. (Dirty state is reported as `<rev>-dirty`.)
- Hermetic check derivations need `doCheck = true` (stdenv default is false — checkPhase is silently skipped) and an `installPhase = "mkdir -p $out"` or the build fails with "failed to produce output path".
- `python3.withPackages (ps: ...)` is the right way to get a buildable env with `python` + modules on PYTHONPATH; its `.env` attribute is interactive-only and fails under `nix shell --expr`.

## Testing / verification

- `tests/test_tetris.py` — 68 headless pytest cases: bag fairness, SRS kick tables (spec values + inverse-consistency) and rotation math (incl. a fuzz over positions), movement bounds, lock delay (expiry, resets, 15-reset cap), soft/hard drop scoring, line clears, score table, level-ups, hold semantics, highscore load/save (tmp_path + XDG_CONFIG_HOME monkeypatch), gravity/pause, game over, full-game simulations (hard-drop, pure-gravity, bot-played), placement evaluator (clears/holes/height/topmost-cell regression), procedural-sound determinism, music (note frequencies, rest silence, theme well-formedness, mixer-less no-op), headless rendered frames (SDL dummy driver, incl. demo mode).
- Run hermetically: `nix flake check .#` (flake `checks`: `default` = `PYTHONPATH=src python -m pytest`, `mypy` = `mypy --strict src/py_tetris`). CI (`.github/workflows/ci.yml`) runs `nix build .#` + `nix flake check` on push/PR.
- The whole package is fully type-hinted and mypy `--strict` clean (config in `pyproject.toml`).
- Headless run check:
  `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 6 nix run .# --option substituters "https://cache.nixos.org"`
  Expect the `pygame-ce ... (SDL ...)` banner and no traceback; being killed by timeout = success.
- A `fc-list` UserWarning in sandboxed runs is harmless (fontconfig timeout); `SysFont` falls back to the bundled default font. Tests use `pygame.font.Font(None, ...)` (bundled font) to avoid fontconfig entirely.

## Git

- Commits so far: `a0f677c` initial game+flake, `8ffe056` project memory + milestones, `94344dc` M2 (tests, type hints, flake checks, CI), `a38361b` M1 (hold, lock delay, SRS, highscore, sounds), `354e0e8` demo bot + NEW GAME button, `f67094f` full 45-bar Korobeiniki music (score transcription) + ♩=190, `85e5a75` reference files to gitignored `tmp/`.
- `.envrc` (`use flake`) committed; `.direnv/`, `__pycache__/`, `result`, `*.swp` gitignored.

## Gameplay notes (M1)

- Rotation uses full SRS: `JLSTZ_KICKS` / `I_KICKS` tables keyed by (from_state, to_state); `Piece.state` tracks 0/1/2/3. Kicks are in board coordinates (+dy = down); the O piece never kicks.
- Lock delay: grounded pieces get `LOCK_DELAY` (0.5s), resettable by move/rotate up to `MAX_LOCK_RESETS` (15) per grounded spell; `Game.lock()` returns the number of lines cleared.
- Hold: one per piece (`can_hold`), re-allowed after any downward move or soft drop; the swap path must not touch `next_kind`.
- High score: `~/.config/py-tetris/highscore` (XDG_CONFIG_HOME honored, for tests); loaded in `Game.__init__`, saved when the game ends.
- Sounds: procedural sine tones (`_tone` → 16-bit mono PCM buffers), built in `Sounds.build()` after mixer init; all optional — the game runs fine with no audio device. `M` toggles SFX + music. Line clears play `clear` (1–3) / `tetris` (4) via `Game.last_cleared`, consumed once per frame in `main()`.
- Music: "The Peddlers" (Korobeiniki, the classic Tetris theme — public-domain folk melody, E minor, 4/4) — full 45-bar transcription of the score `korobeiniki_score_p1/p2.png` ("Piano Tiles Version", Zakura): `_MAIN` (bars 1–8 motif) + `_DEV` (development, chromatic runs, E6 fermata climax, 2/4 ff bar) + `_RETURN` (ff motif in eighths) + `_BRIDGE` + `_CLIMAX2` (high chromatic peak) + `_RUNS` + `_CODA` (final held A5). Every bar sums to 4 beats; rendered as a ~57s looping square wave at ♩≈190 (score says 170, played a bit faster). `note_freq` + `render_melody` (PCM buffer, envelope per note; renders in ~0.3s) + `Music` (persistent `play(-1)` channel). `mixer.pre_init(22050, -16, 1, 512)` must precede `pygame.init()` so the buffer renders at the mixer rate. Verify rendered pitch/duration by zero-crossing analysis of the PCM (no audio on this machine). The dense chromatic middle bars are a best-effort reading of the score — if a bar sounds off, the user can point it out.
- **`35149.mid` is NOT this melody** — it contains no E or B notes at all (different chromatic arrangement). The score PNGs are the reference; don't re-derive the music from the MIDI.
- Demo bot: `Bot.step()` thinks every `BOT_THINK_INTERVAL` (0.3s); scores every legal (rotation, x) placement of the current piece with `evaluate_placement` (clears ×1000, −holes ×30, −Σheights ×2, −bumpiness) restricted to rest positions reachable from the current height, then executes via rotate/move/hard_drop with hard-drop fallback on any failed step. `Game.mode` is `"demo"`/`"human"`; NEW GAME button rect is `NEW_GAME_RECT`.

## Known limitations (see `.opencode/milestones.md`)

- Demo bot is depth-1 greedy (no lookahead/hold usage); it plays ~100+ line games.
- `pygame.key.set_repeat` for held keys instead of tuned DAS/ARR.
- Music is a single square-wave lead (no bass/chords, unlike the full piano arrangement); fixed tempo ♩≈190 (score: 170 + accelerando, flattened); the 2/4 climax bar is normalized to 4/4.
- No T-spin detection, back-to-back/combo bonuses (M4).

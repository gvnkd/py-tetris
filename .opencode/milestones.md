# Milestones

Baseline is M0 (done). Work top-down; each milestone should leave the game runnable via `nix run .#`.

## M0 — Baseline (done)

- [x] Single-file pygame Tetris: 7-bag randomizer, ghost piece, wall kicks, soft/hard drop, scoring + levels, pause, restart, game over
- [x] Nix flake: `packages`, `apps`, `devShells` (4 systems), nixpkgs pinned in `flake.lock`
- [x] Headless verification pattern established (`SDL_VIDEODRIVER=dummy`, see AGENTS.md)
- [x] Git repo, first commit, `.gitignore`, `.envrc`

## M1 — Core gameplay feel

- [x] Hold piece: `C`, one hold per piece, re-allowed after downward movement; HOLD panel in sidebar (dimmed while locked out)
- [x] Lock delay: 500ms while grounded, reset by move/rotate, capped at 15 resets (no infinite spin)
- [x] SRS wall kicks: full JLSTZ + I tables keyed by (from, to) rotation state, O never kicks
- [x] High score persistence: `~/.config/py-tetris/highscore` (XDG_CONFIG_HOME honored), BEST row in sidebar
- [x] Sound effects: procedural sine tones for move / rotate / soft+hard drop / line clear / tetris / game over; `M` mutes; BGM deliberately omitted (see M4)

## M2 — Engineering

- [x] Pytest suite for game logic (headless): bag fairness, wall kicks (incl. position fuzz), bounds, drops + scoring, line clears, score table, level-ups, gravity/pause, game over, full-game simulation, headless render — 35 tests in `tests/test_tetris.py`
- [x] Flake `checks` output: `checks.default` (pytest) and `checks.mypy` (`mypy --strict`), both green via `nix flake check`
- [x] CI: GitHub Actions (`.github/workflows/ci.yml`) — `nix build .#` + `nix flake check` on push/PR (active once the repo is pushed to GitHub)
- [x] Full type hints on `tetris.py`, mypy `--strict` clean
- [x] SRS-kick and lock-delay test cases (landed with M1)

## M3 — Nix polish (done)

- [x] Desktop entry + icon (`py-tetris.desktop`, hicolor 128/512 icons) installed into the package; `meta.desktopName` set
- [x] Pinned nixpkgs to **nixos-26.05 (stable)**: builds after `dontCheckRuntimeDeps = true` (pygame vs pygame-ce dist-name mismatch on stable); see AGENTS.md
- [x] README.md with run/develop instructions incl. the dead-local-cache workaround

## M5 — Refactor (done)

- [x] Split `tetris.py` into the `py_tetris` package (src layout): `constants`, `pieces`, `audio`, `highscore`, `game` (pure logic), `render`, `app` + `__main__`
- [x] PEP 621 `pyproject.toml` (setuptools backend, `py-tetris` console script, strict mypy + pytest config) replaces legacy `setup.py`; flake uses `pyproject = true`
- [x] Dev shell: `python3 -m py_tetris`, mypy available; all 68 tests + mypy green on the new layout

## M4 — Nice to have (done)

- [x] Autoplay demo bot on startup; click a mode button (or R/Enter) to take over; demo auto-restarts after game over
- [x] Background music: Korobeiniki / "The Peddlers" — full piece from the user's transcription (`tmp/korobeiniki_score_transcribed.txt`): phrase ×4, quarter-note bridge, held-G5 climax, run-throughs, walkdown ending; 380 beats ≈ 2min loop at ♩≈190; `M` mutes music too. (`35149.mid` turned out to be a different chromatic arrangement — not this melody.)
- [x] DAS/ARR: explicit key-hold timing via `AutoRepeat` (170 ms / 50 ms), replaces `pygame.key.set_repeat`
- [x] T-spin detection (3-corner rule, full/mini) + back-to-back ×1.5 + combo scoring, T-SPIN sound and on-board text
- [x] Line-clear flash (blinking white overlay on the cleared rows, 0.25s)
- [x] Smarter bot: depth-2 lookahead (top-8 placements × next piece) + hold usage; plays 1000+ line games
- [x] Game modes: MARATHON (endless, level-up) / SPRINT (20 lines, fixed level, "YOU WIN") / ULTRA (2 min countdown, level 5, "TIME UP")

## Backlog (ideas, not scheduled)

- Deeper bot: 3–4 piece lookahead, T-spin setup search, better hold strategy
- Music: bass/chord voices under the lead; per-section dynamics (piano/ff) like the score
- Official sprint gravity (fixed fast level) and per-line ultra scaling
- More modes (e.g. marathon level cap, "sudden death")
- Key remapping / config file
- Packaging: nixos module (desktop integration), AppImage or pip-installable wheel

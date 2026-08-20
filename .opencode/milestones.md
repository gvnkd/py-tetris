# Milestones

Baseline is M0 (done). Work top-down; each milestone should leave the game runnable via `nix run .#`.

## M0 — Baseline (done)

- [x] Single-file pygame Tetris: 7-bag randomizer, ghost piece, wall kicks, soft/hard drop, scoring + levels, pause, restart, game over
- [x] Nix flake: `packages`, `apps`, `devShells` (4 systems), nixpkgs pinned in `flake.lock`
- [x] Headless verification pattern established (`SDL_VIDEODRIVER=dummy`, see AGENTS.md)
- [x] Git repo, first commit, `.gitignore`, `.envrc`

## M1 — Core gameplay feel

- [ ] Hold piece (bind to `C`, one held piece per game, no hold right after spawn)
- [ ] Lock delay (~500ms) with reset-on-move/rotate, capped resets (prevents infinite stalling)
- [ ] SRS wall kicks: standard 5-kick table per piece/rotation state (replaces ad-hoc `KICKS`)
- [ ] High score persistence: `~/.config/py-tetris/highscore`, shown in sidebar
- [ ] Sound effects: move / rotate / soft drop / hard drop / line clear / game over (`pygame.mixer`), optional BGM

## M2 — Engineering

- [x] Pytest suite for game logic (headless): bag fairness, wall kicks (incl. position fuzz), bounds, drops + scoring, line clears, score table, level-ups, gravity/pause, game over, full-game simulation, headless render — 35 tests in `tests/test_tetris.py`
- [x] Flake `checks` output: `checks.default` (pytest) and `checks.mypy` (`mypy --strict`), both green via `nix flake check`
- [x] CI: GitHub Actions (`.github/workflows/ci.yml`) — `nix build .#` + `nix flake check` on push/PR (active once the repo is pushed to GitHub)
- [x] Full type hints on `tetris.py`, mypy `--strict` clean
- [ ] SRS-kick and lock-delay test cases — deferred to M1 (they test features that don't exist yet)

## M3 — Nix polish

- [ ] Desktop entry + icon so the app shows in GUI menus
- [ ] Evaluate pinning nixpkgs to `stable` instead of `unstable` (fewer surprise rebuilds)
- [ ] Document the dead local-cache workaround (`--option substituters`) for other devs

## M4 — Nice to have

- [ ] DAS/ARR: explicit key-hold timing instead of `pygame.key.set_repeat`
- [ ] T-spin detection + back-to-back / combo scoring
- [ ] Line-clear flash animation before rows collapse
- [ ] Game modes (marathon / sprint / ultra)

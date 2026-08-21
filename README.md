# Py Tetris

Tetris in Python (pygame), run and developed via a Nix flake.

The game starts in **demo mode** (an autoplay bot plays at a human-like
pace). Pick a mode to take over: **MARATHON** (endless), **SPRINT**
(first to 20 lines) or **ULTRA** (2 minutes, level 5) — the sidebar
buttons start/restart in human mode.

## Features

- Full SRS rotation with wall kicks, 7-bag randomizer, ghost piece
- Hold, lock delay with move/rotate resets, DAS/ARR key repeat
- Guideline scoring: T-spins (full/mini), back-to-back, combos
- Game modes: marathon / sprint / ultra
- Persistent high score (`~/.config/py-tetris/highscore`)
- Procedural sound effects and the Korobeiniki ("The Peddlers") theme —
  no audio assets, everything is generated at startup
- Depth-2 lookahead demo bot with hold usage
- Installed as a desktop app (`py-tetris.desktop` + icon)

## Run

```sh
nix run .#
```

If your local Nix binary cache is unreachable and builds stall on
`narinfo` timeouts, point Nix at the public cache for the invocation:

```sh
nix run .# --option substituters "https://cache.nixos.org"
```

## Controls

| Key | Action |
| --- | --- |
| Left / Right | move |
| Down | soft drop |
| Up / X | rotate clockwise |
| Z | rotate counter-clockwise |
| Space | hard drop |
| C | hold piece |
| M | mute / unmute sounds and music |
| P | pause |
| R | restart (after game over) / start a human marathon in demo mode |
| Q | quit |

Held keys auto-repeat with DAS/ARR timing (170 ms delay, 50 ms rate).

## Develop

```sh
nix develop .#          # python3, pygame, pytest, mypy; PYTHONPATH=src set
python3 -m py_tetris    # run the game (live editing)
python3 -m pytest tests -v
python3 -m mypy         # strict type check (config in pyproject.toml)
```

Hermetic test run (what CI does):

```sh
nix flake check .#
```

## Layout

- `src/py_tetris/` — the package: `constants`, `pieces` (shapes + SRS),
  `audio` (SFX + Korobeiniki music), `highscore`, `game` (logic + bot,
  no pygame), `input` (DAS/ARR), `render`, `app` (entry point)
- `tests/` — headless pytest suite (95 cases)
- `pyproject.toml` — PEP 621 metadata, entry point, mypy/pytest config
- `flake.nix` — packages/app/devShell/checks, pinned to nixos-26.05
  (see `flake.lock`)
- `py-tetris.desktop` + `icons/` — desktop entry and hicolor icons
- `tmp/` — reference material for the music transcription (gitignored)

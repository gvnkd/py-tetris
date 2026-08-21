# Py Tetris

Tetris in Python (pygame), run and developed via a Nix flake.

The game starts in **demo mode** (an autoplay bot plays). Pick a mode to
take over: **MARATHON** (endless), **SPRINT** (first to 20 lines) or
**ULTRA** (2 minutes, level 5) — the sidebar buttons start/restart in
human mode.

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
| R | restart (after game over) |
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
  `audio` (SFX + Korobeiniki music), `highscore`, `game` (logic, bot),
  `render`, `app` (entry point)
- `tests/` — headless pytest suite
- `pyproject.toml` — PEP 621 metadata, entry point, mypy/pytest config
- `flake.nix` — pinned to nixos-26.05 (see `flake.lock`)
- `tmp/` — reference material for the music transcription (gitignored)

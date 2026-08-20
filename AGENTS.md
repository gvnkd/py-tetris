# Project Memory

## Overview

Single-file Tetris in Python (pygame), packaged and run via a Nix flake.

- `tetris.py` — the entire game (requirement: keep it one file)
- `setup.py` — minimal packaging so nix installs a `py-tetris` entry point
- `flake.nix` / `flake.lock` — nixpkgs pinned to `nixos-unstable`; `packages`, `apps`, `devShells` for 4 systems

## Commands

- Run game: `nix run .#`
- Dev shell (live editing): `nix develop .#` then `python3 tetris.py`
- Build: `nix build .#`
- Controls: arrows move, Down soft drop, Up/X and Z rotate, Space hard drop, P pause, R restart (after game over), Q quit

## Nix findings (hard-won — do not rediscover)

- nix 2.34 flake apps use the new schema: `type = "app"; program = "..."`. The legacy `command` attribute is rejected (`attribute 'apps.<system>.default.program' does not exist`).
- `buildPythonApplication` requires `format = "setuptools"` (legacy setup.py) or `pyproject = true`, else: "does not configure a `format`".
- Runtime Python deps go in `dependencies = [ ... ]` (PEP 621 style; mapped to `propagatedBuildInputs` and injected into wrapped scripts via `site.addsitedir`). There is no `pythonImports` attribute in current nixpkgs — it is silently ignored, producing a package that crashes with `ModuleNotFoundError` at runtime.
- The local binary cache `http://192.168.0.254:5001` (in the user's nix substituters) times out and aborts the whole build. Workaround: `--option substituters "https://cache.nixos.org"`. Builds also run on remote builder `ssh-ng://builder`.
- `nix shell .#` resolves to `packages.default`, not the devShell. Use `.#devShells.<system>.default` explicitly.
- `nix shell --command` in this nix version execs argv directly with no shell: builtins (`echo ...`) and multi-word commands fail. Pass real binaries only.
- The built package uses Python 3.14 (`lib/python3.14/site-packages`) and has no `bin/python` — invoke `bin/py-tetris`.

## Testing / verification

- Game logic (`Game` class) is headless; no display needed for logic tests.
- Headless run check:
  `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 6 nix run .# --option substituters "https://cache.nixos.org"`
  Expect the `pygame-ce ... (SDL ...)` banner and no traceback; being killed by timeout = success.
- A `fc-list` UserWarning in sandboxed runs is harmless (fontconfig timeout); `SysFont` falls back to the bundled default font.
- Verified by a throwaway smoke script: rotations + kicks, soft/hard drop, 2-line clear scoring, one rendered frame, and a full game played to game over. Pattern is in git history of this session if needed (script was in /tmp, not committed).

## Git

- Repo initialized, first commit `a0f677c`.
- `.envrc` (`use flake`) committed; `.direnv/`, `__pycache__/`, `result` gitignored.

## Known limitations (see `.opencode/milestones.md`)

- No lock delay: pieces lock the moment gravity can't advance them.
- Ad-hoc wall-kick table instead of SRS.
- No hold piece, no high-score persistence, no sounds.
- `pygame.key.set_repeat` for held keys instead of tuned DAS/ARR.

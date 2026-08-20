"""High score persistence in ~/.config/py-tetris/highscore (XDG honored)."""

import os


def highscore_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME", "")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "py-tetris", "highscore")


def load_highscore() -> int:
    try:
        with open(highscore_path(), encoding="utf-8") as f:
            return max(0, int(f.read().strip() or 0))
    except (OSError, ValueError):
        return 0


def save_highscore(score: int) -> None:
    if score <= 0:
        return
    path = highscore_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{score}\n")
    except OSError:
        pass

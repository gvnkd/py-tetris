"""Procedural sound effects and the Korobeiniki background music."""

import math
import struct
from array import array
from dataclasses import dataclass

import pygame


def _tone(freq: float, ms: int, vol: float, rate: int = 22050) -> bytes:
    """Render a simple sine tone (with linear fade-out) to 16-bit mono PCM."""
    n = max(1, int(rate * ms / 1000))
    out = bytearray()
    amp = 32767.0 * vol
    for i in range(n):
        v = math.sin(2.0 * math.pi * freq * i / rate)
        v *= (n - i) / n
        out += struct.pack("<h", int(amp * v))
    return bytes(out)


@dataclass
class Sounds:
    enabled: bool = True
    move: pygame.mixer.Sound | None = None
    rotate: pygame.mixer.Sound | None = None
    drop: pygame.mixer.Sound | None = None
    hard: pygame.mixer.Sound | None = None
    clear: pygame.mixer.Sound | None = None
    tetris: pygame.mixer.Sound | None = None
    over: pygame.mixer.Sound | None = None

    @classmethod
    def build(cls) -> "Sounds":
        s = cls()
        if not pygame.mixer.get_init():
            return s
        try:
            fmt = pygame.mixer.get_init()
            rate = fmt[0] if fmt and fmt[0] else 22050
            s.move = pygame.mixer.Sound(buffer=_tone(240, 45, 0.3, rate))
            s.rotate = pygame.mixer.Sound(buffer=_tone(440, 60, 0.35, rate))
            s.drop = pygame.mixer.Sound(buffer=_tone(180, 50, 0.35, rate))
            s.hard = pygame.mixer.Sound(buffer=_tone(90, 120, 0.5, rate))
            s.clear = pygame.mixer.Sound(buffer=_tone(660, 130, 0.5, rate))
            s.tetris = pygame.mixer.Sound(buffer=_tone(880, 220, 0.55, rate))
            s.over = pygame.mixer.Sound(buffer=_tone(110, 700, 0.5, rate))
        except pygame.error:
            pass
        return s

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        snd = getattr(self, name, None)
        if snd is not None:
            snd.play()


_NOTE_INDEX: dict[str, int] = {
    n: i for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())
}


def note_freq(note: str) -> float:
    """Frequency in Hz for a note name like "C5" (A4 = 440)."""
    idx = _NOTE_INDEX[note[:-1]]
    octave = int(note[-1])
    semitones = idx + 12 * (octave - 4) - 9
    return 440.0 * math.exp(math.log(2.0) * semitones / 12.0)


# "The Peddlers" (Korobeiniki) - public-domain Russian folk melody,
# the classic Tetris theme. Full 45-bar transcription of the score
# korobeiniki_score_p1/p2.png ("Piano Tiles Version", Zakura):
# E minor, 4/4, quarter note = 170 in the score (played a bit faster).
# (note, beats); "R" = rest; every bar sums to 4 beats.
# NOTE: 35149.mid does NOT contain this melody (it has no E or B notes
# at all - it is a different chromatic arrangement); the score is the
# reference. The dense chromatic middle bars are a best-effort reading
# of the score; listen and flag any bar that sounds off.
_MAIN: tuple[tuple[str, float], ...] = (  # bars 1-8
    ("E5", 2), ("B4", 1), ("C5", 1),
    ("D5", 2), ("C5", 1), ("B4", 1),
    ("A4", 2), ("A4", 1), ("C5", 1),
    ("E5", 2), ("D5", 1), ("C5", 1),
    ("B4", 2), ("R", 1), ("C5", 1),
    ("D5", 2), ("E5", 1), ("R", 1),
    ("C5", 2), ("A4", 1), ("R", 1),
    ("A4", 4),
)
_DEV: tuple[tuple[str, float], ...] = (  # bars 9-20: development + runs to the climax
    ("C5", 1), ("A4", 1), ("C5", 1), ("E5", 1),  # 9
    ("F#5", 0.5), ("E5", 0.5), ("D5", 1), ("C5", 1), ("B4", 1),  # 10
    ("E5", 0.5), ("D#5", 0.5), ("D5", 1), ("C#5", 1), ("B4", 1),  # 11
    ("C5", 0.5), ("A4", 0.5), ("B4", 1), ("C5", 1), ("A4", 1),  # 12
    ("B4", 0.5), ("E5", 0.5), ("G#4", 1), ("B4", 1), ("G4", 1),  # 13
    ("A4", 1), ("G4", 1), ("F4", 1), ("D4", 1),  # 14
    ("A4", 1), ("G4", 1), ("F4", 1), ("D4", 1),  # 15
    ("E4", 0.5), ("D#4", 0.5), ("E4", 0.5), ("F#4", 0.5), ("G4", 0.5), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5),  # 16
    ("D5", 0.5), ("C5", 0.5), ("D5", 0.5), ("C5", 0.5), ("B4", 0.5), ("A4", 0.5), ("G#4", 0.5), ("E4", 0.5),  # 17
    ("G#4", 0.5), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("D5", 0.5), ("D#5", 0.5), ("E5", 0.5), ("F#5", 0.5),  # 18
    ("E6", 3), ("R", 1),  # 19: fermata climax
    ("G4", 2), ("R", 2),  # 20: 2/4 ff bar (normalized)
)
_RETURN: tuple[tuple[str, float], ...] = (  # bars 21-25: ff return of the motif in eighths
    ("E5", 0.5), ("B4", 0.5), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("C5", 0.5), ("B4", 0.5), ("A4", 0.5),  # 21
    ("A4", 0.5), ("A4", 0.5), ("C5", 0.5), ("E5", 0.5), ("D5", 0.5), ("C5", 0.5), ("B4", 0.5), ("A4", 0.5),  # 22
    ("B4", 0.5), ("B4", 0.5), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("D5", 0.5), ("C5", 0.5), ("B4", 0.5),  # 23
    ("C5", 0.5), ("A4", 0.5), ("A4", 2), ("R", 1),  # 24
    ("R", 0.5), ("D5", 0.5), ("F5", 0.5), ("A5", 0.5), ("G5", 0.5), ("F5", 0.5), ("E5", 0.5), ("D5", 0.5),  # 25
)
_BRIDGE: tuple[tuple[str, float], ...] = (  # bars 26-30
    ("R", 0.5), ("G4", 0.5), ("C5", 0.5), ("E5", 0.5), ("D5", 0.5), ("D#5", 0.5), ("B4", 1),  # 26
    ("B4", 1), ("B4", 0.5), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("F5", 1),  # 27
    ("C5", 1), ("A4", 1), ("A4", 2),  # 28
    ("R", 0.5), ("B4", 0.5), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("D5", 0.5), ("C5", 1),  # 29
    ("R", 0.5), ("B4", 0.5), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("D5", 0.5), ("C5", 1),  # 30
)
_CLIMAX2: tuple[tuple[str, float], ...] = (  # bars 31-34: high chromatic peak
    ("R", 0.5), ("B4", 0.5), ("C5", 0.5), ("D5", 0.5), ("D#5", 1), ("F5", 0.5), ("G5", 0.5),  # 31
    ("E5", 0.5), ("D#5", 0.5), ("D5", 0.5), ("C#5", 0.5), ("C5", 0.5), ("B4", 0.5), ("A#4", 0.5), ("A4", 0.5),  # 32
    ("G4", 0.5), ("F#4", 0.5), ("F4", 0.5), ("E4", 0.5), ("D#4", 0.5), ("D4", 0.5), ("C4", 0.5), ("B3", 0.5),  # 33
    ("G5", 0.5), ("G5", 0.5), ("F5", 0.5), ("E5", 0.5), ("D5", 0.5), ("E5", 0.5), ("D5", 0.5), ("B4", 0.5),  # 34
)
_RUNS: tuple[tuple[str, float], ...] = (  # bars 35-41: fast eighth-note runs
    ("E5", 0.5), ("D5", 0.5), ("C5", 0.5), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("B4", 0.5), ("G#4", 0.5),  # 35
    ("A4", 0.5), ("G#4", 0.5), ("A4", 0.5), ("B4", 0.5), ("E5", 0.5), ("D5", 0.5), ("C5", 0.5), ("B4", 0.5),  # 36
    ("E5", 0.5), ("F5", 0.5), ("E5", 0.5), ("C5", 0.5), ("D5", 0.5), ("C5", 0.5), ("B4", 0.5), ("D5", 0.5),  # 37
    ("E5", 0.5), ("D5", 0.5), ("C5", 0.5), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("B4", 0.5), ("G#4", 0.5),  # 38
    ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("B4", 0.5), ("A4", 1), ("E4", 1),  # 39
    ("E5", 0.5), ("F5", 0.5), ("E5", 0.5), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("D5", 0.5), ("B4", 0.5),  # 40
    ("C5", 0.5), ("D5", 0.5), ("C5", 0.5), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("B4", 0.5), ("G#4", 0.5),  # 41
)
_CODA: tuple[tuple[str, float], ...] = (  # bars 42-45
    ("A4", 0.5), ("G#4", 0.5), ("A4", 0.5), ("B4", 0.5), ("C#5", 0.5), ("D5", 0.5), ("B4", 1),  # 42
    ("E5", 0.5), ("F5", 0.5), ("E5", 0.5), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("D5", 0.5), ("B4", 0.5),  # 43
    ("C5", 0.5), ("D5", 0.5), ("C5", 0.5), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("B4", 0.5), ("G#4", 0.5),  # 44
    ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("E5", 0.5), ("A5", 2),  # 45: final held A
)
THEME_A: tuple[tuple[str, float], ...] = (
    _MAIN
    + (("R", 0.5),)  # breath before the development
    + _DEV
    + _RETURN
    + _BRIDGE
    + _CLIMAX2
    + _RUNS
    + _CODA
)
MUSIC_BEAT = 60.0 / 190.0  # seconds per quarter note (score is 170; played a bit faster)


def render_melody(
    notes: tuple[tuple[str, float], ...],
    beat: float,
    rate: int = 22050,
    vol: float = 0.22,
) -> bytes:
    """Render a melody of square-wave notes to 16-bit mono PCM."""
    samples = array("h")
    for name, beats in notes:
        n = max(1, int(rate * beat * beats))
        if name == "R":
            samples.extend([0] * n)
            continue
        freq = note_freq(name)
        amp = 32767.0 * vol
        for i in range(n):
            phase = (freq * i / rate) % 1.0
            v = 1.0 if phase < 0.5 else -1.0
            env = min(1.0, i / 120.0, (n - i) / (n * 0.2 + 1.0))
            samples.append(int(amp * v * env))
    return samples.tobytes()


class Music:
    """Loops the background melody; safe no-op when no audio device exists."""

    def __init__(self) -> None:
        self.sound: pygame.mixer.Sound | None = None
        self.channel: pygame.mixer.Channel | None = None

    def start(self) -> None:
        if self.sound is not None or not pygame.mixer.get_init():
            return
        try:
            fmt = pygame.mixer.get_init()
            rate = fmt[0] if fmt is not None and fmt[0] else 22050
            self.sound = pygame.mixer.Sound(buffer=render_melody(THEME_A, MUSIC_BEAT, rate))
        except pygame.error:
            self.sound = None

    def play(self) -> None:
        if self.sound is not None and self.channel is None:
            self.channel = self.sound.play(-1)

    def stop(self) -> None:
        if self.channel is not None:
            self.channel.stop()
            self.channel = None

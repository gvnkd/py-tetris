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
    hold: pygame.mixer.Sound | None = None
    hard: pygame.mixer.Sound | None = None
    clear: pygame.mixer.Sound | None = None
    tetris: pygame.mixer.Sound | None = None
    tspin: pygame.mixer.Sound | None = None
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
            s.hold = pygame.mixer.Sound(buffer=_tone(330, 60, 0.35, rate))
            s.hard = pygame.mixer.Sound(buffer=_tone(90, 120, 0.5, rate))
            s.clear = pygame.mixer.Sound(buffer=_tone(660, 130, 0.5, rate))
            s.tetris = pygame.mixer.Sound(buffer=_tone(880, 220, 0.55, rate))
            s.tspin = pygame.mixer.Sound(buffer=_tone(1046, 90, 0.5, rate))
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
# the classic Tetris theme. Transcribed from
# tmp/korobeiniki_score_transcribed.txt (per-octave staff lines,
# one char = one eighth note, "R" = rest), E minor, 4/4.
# Structure: the 32-beat phrase P1 (motif) + P2 (flourish) is stated
# four times, then a quarter-note bridge to the held-G5 climax, four
# run-throughs of the phrase, and a walkdown ending. 380 beats total.
# NOTE: 35149.mid and the score PNGs are in tmp/ for reference; the
# MIDI does NOT contain this melody (no E or B notes at all).
_P1: tuple[tuple[str, float], ...] = (  # motif, 32 beats (8 bars)
    ("E5", 2), ("B4", 1), ("C5", 1),
    ("D5", 1), ("E5", 0.5), ("D5", 0.5), ("C5", 1), ("B4", 1),
    ("A4", 2), ("A4", 1), ("C5", 1),
    ("E5", 2), ("D5", 1), ("C5", 1),
    ("B4", 3), ("C5", 1),
    ("D5", 2), ("E5", 2),
    ("C5", 2), ("A4", 2),
    ("A4", 4),
)
_P2: tuple[tuple[str, float], ...] = (  # flourish + resolution, 32 beats
    ("D5", 3), ("F5", 1), ("A5", 2), ("G5", 1), ("F5", 1),
    ("E5", 3), ("C5", 1), ("E5", 2), ("D5", 1), ("C5", 1),
    ("B4", 3), ("C5", 1),
    ("D5", 2), ("E5", 2),
    ("C5", 2), ("A4", 2),
    ("A4", 4),
)
_BRIDGE: tuple[tuple[str, float], ...] = (  # quarter-note bridge, 56 beats
    ("E5", 4), ("C5", 4),
    ("D5", 4), ("B4", 4),
    ("C5", 4), ("A4", 4),
    ("G4", 4), ("B4", 4),
    ("E5", 4), ("C5", 4),
    ("D5", 4), ("B4", 4),
    ("C5", 2), ("E5", 2), ("A5", 4),
)
_CLIMAX: tuple[tuple[str, float], ...] = (
    ("G5", 8),  # the held climax note (fermata bar in the score)
)
_RUN: tuple[tuple[str, float], ...] = (  # run-through of P1, 32 beats
    ("E5", 2), ("B4", 1), ("C5", 1),
    ("D5", 1), ("E5", 0.5), ("D5", 0.5), ("C5", 1), ("B4", 1),
    ("A4", 2), ("A4", 1), ("C5", 1),
    ("E5", 2), ("D5", 1), ("C5", 1),
    ("B4", 1), ("E4", 1), ("G4", 1), ("C5", 1),
    ("D5", 2), ("E5", 2),
    ("C5", 2), ("A4", 2),
    ("A4", 4),
)
_RUN2: tuple[tuple[str, float], ...] = (  # run-through of P2, 32 beats
    ("D5", 3), ("F5", 1), ("A5", 2), ("G5", 1), ("F5", 1),
    ("E5", 3), ("C5", 1), ("E5", 2), ("D5", 1), ("C5", 1),
    ("B4", 1), ("E4", 1), ("G4", 1), ("C5", 1),
    ("D5", 2), ("E5", 2),
    ("C5", 2), ("A4", 2),
    ("A4", 4),
)
_WALKDOWN: tuple[tuple[str, float], ...] = (  # arpeggio walkdown ending, 60 beats
    ("E4", 4), ("C4", 4),
    ("D4", 4), ("B3", 4),
    ("C4", 4), ("A3", 4),
    ("G3", 4), ("B3", 4),
    ("E4", 4), ("C4", 4),
    ("D4", 4), ("B3", 4),
    ("C4", 2), ("E4", 2), ("A4", 4),
    ("G4", 4),
)
THEME_A: tuple[tuple[str, float], ...] = (
    _P1 + _P2 + _P1 + _P2
    + _BRIDGE
    + _CLIMAX
    + _RUN + _RUN2 + _RUN + _RUN2
    + _WALKDOWN
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

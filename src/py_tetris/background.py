"""Animated background: soft drifting glows and falling tetromino silhouettes."""

import math
import random

import pygame

from py_tetris.constants import Color
from py_tetris.pieces import COLORS, SHAPES

KINDS = tuple(SHAPES)


def _soft_glow(radius: int, color: Color) -> pygame.Surface:
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        alpha = int(48 * (1 - r / radius) ** 2)
        pygame.draw.circle(glow, (*color, alpha), (radius, radius), r)
    return glow


class _TetrominoSprite:
    def __init__(self, kind: str, cell: int, alpha: int) -> None:
        cells = SHAPES[kind]
        min_x = min(cx for cx, _ in cells)
        max_x = max(cx for cx, _ in cells)
        min_y = min(cy for _, cy in cells)
        max_y = max(cy for _, cy in cells)
        img = pygame.Surface(
            ((max_x - min_x + 1) * cell, (max_y - min_y + 1) * cell),
            pygame.SRCALPHA,
        )
        for cx, cy in cells:
            rect = pygame.Rect((cx - min_x) * cell, (cy - min_y) * cell, cell, cell)
            pygame.draw.rect(img, (*COLORS[kind], alpha), rect, border_radius=3)
        self.img = img


class _Drifter:
    __slots__ = ("sprite", "base_x", "y", "speed", "phase", "sway", "freq")

    def __init__(
        self,
        sprite: _TetrominoSprite,
        base_x: float,
        y: float,
        speed: float,
        phase: float,
        sway: float,
        freq: float,
    ) -> None:
        self.sprite = sprite
        self.base_x = base_x
        self.y = y
        self.speed = speed
        self.phase = phase
        self.sway = sway
        self.freq = freq

    @property
    def x(self) -> float:
        return self.base_x + math.sin(self.phase) * self.sway


class _Glow:
    __slots__ = ("img", "cx", "cy", "rx", "ry", "phase", "speed")

    def __init__(
        self,
        img: pygame.Surface,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        phase: float,
        speed: float,
    ) -> None:
        self.img = img
        self.cx = cx
        self.cy = cy
        self.rx = rx
        self.ry = ry
        self.phase = phase
        self.speed = speed

    @property
    def pos(self) -> tuple[int, int]:
        x = self.cx + math.cos(self.phase) * self.rx - self.img.get_width() / 2
        y = self.cy + math.sin(self.phase * 0.8 + 1.3) * self.ry - self.img.get_height() / 2
        return (int(x), int(y))


class Background:
    """Ambient animated backdrop. Call update(dt_ms) then draw(screen) per frame."""

    def __init__(self, w: int, h: int, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._w = w
        self._h = h
        self._glows: list[_Glow] = []
        for color, radius in (
            ((40, 70, 130), 180),
            ((90, 45, 120), 230),
            ((30, 100, 100), 150),
        ):
            self._glows.append(
                _Glow(
                    _soft_glow(radius, color),
                    self._rng.uniform(0, w),
                    self._rng.uniform(0, h),
                    self._rng.uniform(40, 110),
                    self._rng.uniform(30, 80),
                    self._rng.uniform(0, math.tau),
                    self._rng.uniform(0.05, 0.12),
                )
            )
        self._drifters = [
            self._make_drifter(self._rng.uniform(-60, h)) for _ in range(20)
        ]

    def _make_drifter(self, y: float) -> _Drifter:
        kind = KINDS[self._rng.randrange(len(KINDS))]
        sprite = _TetrominoSprite(
            kind, self._rng.choice((9, 12, 15)), self._rng.randint(35, 75)
        )
        return _Drifter(
            sprite=sprite,
            base_x=self._rng.uniform(0, self._w),
            y=y,
            speed=self._rng.uniform(10, 34),
            phase=self._rng.uniform(0, math.tau),
            sway=self._rng.uniform(6, 22),
            freq=self._rng.uniform(0.15, 0.5),
        )

    def update(self, dt: float) -> None:
        s = dt / 1000.0
        for i, d in enumerate(self._drifters):
            d.y += d.speed * s
            d.phase += d.freq * s * math.tau
            if d.y > self._h + 60:
                self._drifters[i] = self._make_drifter(-60)
        for g in self._glows:
            g.phase += g.speed * s

    def draw(self, surf: pygame.Surface) -> None:
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(0, 0, self._w, self._h))
        for g in self._glows:
            surf.blit(g.img, g.pos)
        for d in self._drifters:
            x = int(d.x - d.sprite.img.get_width() / 2)
            surf.blit(d.sprite.img, (x, int(d.y)))
        surf.set_clip(clip)

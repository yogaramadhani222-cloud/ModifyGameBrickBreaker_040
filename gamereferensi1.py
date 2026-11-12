import math
import random
from array import array
from collections import deque

import pygame

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

# Pengaturan dasar

WIDTH, HEIGHT = 600, 500
FPS = 60
HUD_H = 42  # tinggi bar atas

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Block Breaker - Neon Edition")
clock = pygame.time.Clock()

font_small = pygame.font.Font('freesansbold.ttf', 15)
font_mid = pygame.font.Font('freesansbold.ttf', 20)
font_big = pygame.font.Font('freesansbold.ttf', 46)
font_tiny = pygame.font.Font('freesansbold.ttf', 12)

# ---------------------------------------------------------------
# Warna
# ---------------------------------------------------------------
BG_TOP = (8, 12, 30)
BG_BOTTOM = (18, 30, 62)
WHITE = (245, 246, 255)
CYAN = (80, 220, 255)
ACCENT = (255, 107, 107)
SOFT = (170, 215, 255)

ROW_COLORS = [
    (56, 189, 248),   # biru langit
    (59, 130, 246),   # biru
    (99, 102, 241),   # indigo
]


def mix(c1, c2, t):
    """Campur dua warna. t=0 -> c1, t=1 -> c2."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ---------------------------------------------------------------
# Aset visual yang dibuat sekali saja
# ---------------------------------------------------------------
def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        color = mix(BG_TOP, BG_BOTTOM, y / HEIGHT)
        pygame.draw.line(bg, color, (0, y), (WIDTH, y))

    rng = random.Random(7)
    for _ in range(80):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        r = rng.choice([1, 1, 1, 2])
        b = rng.randint(100, 220)
        pygame.draw.circle(bg, (b - 30, b - 10, b), (x, y), r)
    return bg


def make_glow(radius, color, strength=110):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        a = int(strength * (1 - r / radius) ** 2)
        pygame.draw.circle(surf, (*color, a), (radius, radius), r)
    return surf


def make_paddle_glow(width, height, color):
    pad = 18
    surf = pygame.Surface((width + pad * 2, height + pad * 2), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        rect = pygame.Rect(pad - i * 3, pad - i * 3,
                           width + i * 6, height + i * 6)
        pygame.draw.rect(surf, (*color, 14), rect, border_radius=14)
    return surf, pad


BACKGROUND = make_background()
BALL_GLOW = make_glow(22, CYAN)
FX_LAYER = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

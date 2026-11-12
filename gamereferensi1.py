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


# ---------------------------------------------------------------
# Audio (semua suara dibuat lewat kode, tanpa file eksternal)
# ---------------------------------------------------------------
SR = 22050


def _wave(kind, phase):
    if kind == 'sine':
        return math.sin(phase)
    if kind == 'tri':
        return 2 / math.pi * math.asin(math.sin(phase))
    if kind == 'square':
        return 1.0 if math.sin(phase) >= 0 else -1.0
    return ((phase / math.pi) % 2) - 1  # saw


def synth(f0, f1, dur, vol, kind='sine', attack=0.004, decay=2.0):
    """Satu nada dengan pitch meluncur dari f0 ke f1."""
    n = int(SR * dur)
    out = []
    phase = 0.0
    att = max(1, int(SR * attack))
    for i in range(n):
        t = i / n
        phase += 2 * math.pi * (f0 + (f1 - f0) * t) / SR
        env = min(1.0, i / att) * (1 - t) ** decay
        out.append(_wave(kind, phase) * env * vol)
    return out


def add(a, b):
    n = max(len(a), len(b))
    return [(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)
            for i in range(n)]


def arpeggio(freqs, dur, vol, kind='tri', last_mult=2.2, decay=1.5):
    out = []
    for i, f in enumerate(freqs):
        d = dur * (last_mult if i == len(freqs) - 1 else 1)
        out += synth(f, f, d, vol, kind, decay=decay)
    return out


class Audio:
    # nada pentatonik: makin panjang combo, makin tinggi nadanya
    SCALE = [523.25, 587.33, 659.25, 783.99, 880.00,
             1046.50, 1174.66, 1318.51]

    def __init__(self):
        global SR
        self.ok = False
        self.sounds = {}
        self.music = None
        self.channel = None
        self.music_on = True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            SR, fmt, self.channels = pygame.mixer.get_init()
            if fmt != -16:
                raise RuntimeError("format audio tidak didukung")
            self._build()
            self.ok = True
        except Exception as err:
            print("Audio dimatikan:", err)

    def _to_sound(self, samples, volume=1.0):
        data = array('h')
        for v in samples:
            iv = int(max(-1.0, min(1.0, v)) * 32767)
            data.append(iv)
            if self.channels == 2:
                data.append(iv)
        snd = pygame.mixer.Sound(buffer=data.tobytes())
        snd.set_volume(volume)
        return snd

    def _build(self):
        mk = self._to_sound
        self.sounds['paddle'] = mk(synth(300, 430, 0.10, 0.6, 'tri'), 0.8)
        self.sounds['wall'] = mk(synth(210, 170, 0.06, 0.45, 'sine'), 0.7)
        self.sounds['block_hit'] = mk(synth(540, 470, 0.09, 0.28, 'square'), 0.7)
        self.sounds['launch'] = mk(synth(280, 780, 0.20, 0.5, 'tri'), 0.8)
        self.sounds['lose'] = mk(synth(430, 80, 0.60, 0.35, 'saw', decay=1.0), 0.8)
        self.sounds['levelup'] = mk(
            arpeggio([523.25, 659.25, 783.99, 1046.50], 0.10, 0.5), 0.9)
        self.sounds['gameover'] = mk(
            arpeggio([392.00, 349.23, 311.13, 261.63], 0.20, 0.45,
                     last_mult=3, decay=1.2), 0.9)

        for i, f in enumerate(self.SCALE):
            tone = add(synth(f, f, 0.22, 0.45, 'sine'),
                       synth(f * 2, f * 2, 0.12, 0.18, 'tri'))
            self.sounds[f'note{i}'] = mk(tone, 0.9)

        self.music = self._build_music()
        self.channel = self.music.play(loops=-1)
        self.music.set_volume(0.35)

    def _build_music(self):
        """Loop 8 detik: arpeggio lembut di atas progresi Am - F - C - G."""
        chords = [
            ([440.00, 523.25, 659.25, 880.00], 110.00),
            ([349.23, 440.00, 523.25, 698.46], 87.31),
            ([523.25, 659.25, 783.99, 1046.50], 130.81),
            ([392.00, 493.88, 587.33, 783.99], 98.00),
        ]
        pattern = [0, 1, 2, 3, 2, 1, 2, 1]
        step = 0.25
        total = int(SR * step * len(pattern) * len(chords))
        buf = [0.0] * total

        def mix_in(start_s, samples):
            s0 = int(start_s * SR)
            for i, v in enumerate(samples):
                if s0 + i >= total:
                    break
                buf[s0 + i] += v

        for ci, (tones, bass) in enumerate(chords):
            base = ci * step * len(pattern)
            mix_in(base, synth(bass, bass, step * len(pattern), 0.30,
                               'sine', attack=0.05, decay=0.6))
            for pi, idx in enumerate(pattern):
                f = tones[idx]
                mix_in(base + pi * step, synth(f, f, 0.34, 0.16, 'tri', decay=1.6))
        return self._to_sound(buf)

    def play(self, name):
        if self.ok and name in self.sounds:
            self.sounds[name].play()

    def toggle_music(self):
        if not self.ok or self.channel is None:
            return
        self.music_on = not self.music_on
        if self.music_on:
            self.channel.unpause()
        else:
            self.channel.pause()

    def draw_hint(self):
        if not self.ok:
            return
        state = "ON" if self.music_on else "OFF"
        img = font_tiny.render(f"M : musik {state}", True, (110, 130, 165))
        screen.blit(img, img.get_rect(bottomright=(WIDTH - 10, HEIGHT - 8)))


# ---------------------------------------------------------------
# Fungsi gambar bantu
# ---------------------------------------------------------------
def draw_text(text, font, color, center, shadow=True):
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        screen.blit(sh, sh.get_rect(center=(center[0] + 2, center[1] + 2)))
    img = font.render(text, True, color)
    rect = img.get_rect(center=center)
    screen.blit(img, rect)
    return rect


def draw_heart(surf, cx, cy, s, color):
    r = s // 2
    pygame.draw.circle(surf, color, (cx - r, cy), r)
    pygame.draw.circle(surf, color, (cx + r, cy), r)
    pygame.draw.polygon(surf, color, [
        (cx - 2 * r + 1, cy + r // 3),
        (cx + 2 * r - 1, cy + r // 3),
        (cx, cy + int(2.6 * r)),
    ])


def draw_hud(score, level, lives):
    bar = pygame.Surface((WIDTH, HUD_H), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 120))
    screen.blit(bar, (0, 0))
    pygame.draw.line(screen, (*CYAN,), (0, HUD_H), (WIDTH, HUD_H), 2)

    draw_text(f"SKOR  {score}", font_mid, WHITE, (85, HUD_H // 2))
    draw_text(f"LEVEL {level}", font_mid, SOFT, (WIDTH // 2, HUD_H // 2))
    for i in range(3):
        x = WIDTH - 130 + i * 38
        if i < lives:
            draw_heart(screen, x, HUD_H // 2 - 3, 12, ACCENT)
        else:
            draw_heart(screen, x, HUD_H // 2 - 3, 12, (45, 55, 80))


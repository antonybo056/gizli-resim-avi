"""
Gizli Resim Avı: Python (pygame) sürümü.

Kartları çevir, çiftleri eşleştir. Her eşleşen çift kalkınca arkadaki
gizli resmin bir parçası açılır. Bütün çiftleri bulunca resmin tamamı çıkar.

Çalıştırma:
    pip install pygame
    python eslestirme.py

Kısayollar:
    R  aynı ayarlarla yeniden karıştır
    N  yeni oyun ekranı
    Esc  geri dön / çık
"""

import json
import math
import os
import random
import time
from array import array

import pygame

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(APP_DIR, "eslestirme_rekorlar.json")

LEVELS = [("kolay", "Kolay", 4, 3), ("orta", "Orta", 4, 4), ("zor", "Zor", 6, 4), ("uzman", "Uzman", 6, 5)]
THEMES = [
    ("Hayvanlar", ["🐶", "🐱", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐸", "🐵", "🐧", "🐤", "🦉", "🐙", "🦋", "🐢", "🐬", "🦄"]),
    ("Meyveler", ["🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🥕", "🌽", "🥑"]),
    ("Doğa & Uzay", ["🌵", "🌻", "🌈", "⭐", "🌙", "☀️", "🍄", "🌲", "🌊", "❄️", "🔥", "⚡", "🌍", "🪐", "🚀", "🛸", "☄️", "🌋"]),
]
CARD_RATIO = 3 / 4  # kart genişlik / yükseklik

# Renkler: gece müzesi (mürekkep moru zemin, lacivert kart sırtları, mercan vurgu)
BG = (22, 18, 38)
BG_GLOW = (42, 33, 80)
PANEL = (32, 26, 52)
PANEL2 = (42, 35, 66)
LINE = (59, 50, 89)
TEXT = (244, 240, 251)
MUTED = (169, 161, 198)
CORAL = (255, 143, 163)
CORAL_HI = (255, 168, 184)
CORAL_INK = (59, 12, 23)
GOLD = (245, 201, 106)
BACK1 = (61, 67, 150)
BACK2 = (38, 42, 106)
FACE = (251, 248, 255)
FACE_EDGE = (228, 222, 244)
OK = (127, 224, 182)
BAD = (255, 123, 123)

BAR_H = 70
FPS = 60
FLIP_T = 0.32


# ====================================================================
# Yardımcılar
# ====================================================================
def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(c0, c1, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))


def grad_color(stops, t):
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            return lerp(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0)
    return stops[-1][1]


def ease_out(k):
    return 1 - (1 - k) ** 3


def fmt_time(sec):
    t = int(sec)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def rounded(surf, radius):
    """Yüzeyin köşelerini yuvarlar (yumuşak kenarlı)."""
    w, h = surf.get_size()
    big = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
    pygame.draw.rect(big, (255, 255, 255, 255), big.get_rect(), border_radius=radius * 2)
    mask = pygame.transform.smoothscale(big, (w, h))
    out = surf.convert_alpha()
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def cover_crop(src, w, h):
    """Resmi (w, h) alanını dolduracak şekilde ortadan kırpıp ölçekler."""
    sw, sh = src.get_size()
    k = max(w / sw, h / sh)
    scaled = pygame.transform.smoothscale(src, (max(w, math.ceil(sw * k)), max(h, math.ceil(sh * k))))
    x, y = (scaled.get_width() - w) // 2, (scaled.get_height() - h) // 2
    return scaled.subsurface((x, y, w, h)).copy()


def cubic(p0, c1, c2, p1, t):
    u = 1 - t
    a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    return (a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0], a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1])


def ask_image_path():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Gizli resim için bir resim seç",
            filetypes=[("Resimler", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tga"), ("Tüm dosyalar", "*.*")])
        root.destroy()
        return path or None
    except Exception:
        return None


# ====================================================================
# Örnek resimler (koddan üretilir, dosya gerekmez)
# ====================================================================
def sample_sunset():
    W, H = 1500, 1000
    surf = pygame.Surface((W, H))
    rnd = random.Random(7)
    hz = int(H * 0.62)
    sky = [(0, (19, 26, 71)), (0.38, (74, 42, 108)), (0.72, (214, 97, 122)), (1, (255, 197, 111))]
    for y in range(hz):
        pygame.draw.line(surf, grad_color(sky, y / hz), (0, y), (W, y))
    fx = pygame.Surface((W, H), pygame.SRCALPHA)
    for _ in range(260):
        sx, sy = rnd.random() * W, rnd.random() * hz * 0.55
        a = int(255 * (1 - sy / (hz * 0.55)) * (0.3 + 0.7 * rnd.random()))
        pygame.draw.circle(fx, (255, 255, 255, a), (sx, sy), rnd.random() * 1.7 + 0.8)
    mx, my = W * 0.15, H * 0.15
    pygame.draw.circle(fx, (251, 241, 210, 255), (mx, my), 40)
    pygame.draw.circle(fx, (0, 0, 0, 0), (mx + 17, my - 9), 36)
    surf.blit(fx, (0, 0))
    sx, sy, sr = W * 0.64, hz - 70, 150
    glow = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(24, 0, -1):
        pygame.draw.circle(glow, (255, 200, 130, 5), (sx, sy), sr + i * 14)
    surf.blit(glow, (0, 0))
    stripes = [(sy - 10 + i * 24, sy - 10 + i * 24 + 3 + i * 2.2) for i in range(7)]
    sun = [(0, (255, 243, 166)), (0.6, (255, 176, 90)), (1, (255, 122, 74))]
    for y in range(int(sy - sr), int(sy + sr)):
        if any(a <= y < b for a, b in stripes):
            continue
        half = math.sqrt(max(0, sr * sr - (y - sy) ** 2))
        pygame.draw.line(surf, grad_color(sun, (y - (sy - sr)) / (2 * sr)), (sx - half, y), (sx + half, y))
    cl = pygame.Surface((W, H), pygame.SRCALPHA)
    for cx, cy, w, col in [(W * 0.3, H * 0.3, 420, (255, 160, 190, 80)), (W * 0.82, H * 0.22, 360, (255, 190, 210, 64)),
                           (W * 0.48, H * 0.44, 300, (120, 60, 130, 90))]:
        for i in range(6):
            ex, ey = cx + (i - 2.5) * w * 0.17, cy + math.sin(i * 1.7) * 6
            pygame.draw.ellipse(cl, col, (ex - w * 0.2, ey - w * 0.05, w * 0.4, w * 0.1))
    surf.blit(cl, (0, 0))

    def ridge(base, amp, col, seed, freq):
        r = random.Random(seed)
        pts = [(0, H)]
        for i in range(121):
            n = abs(math.sin(i * freq + seed)) * 0.6 + abs(math.sin(i * freq * 2.7 + seed * 3)) * 0.3 + r.random() * 0.08
            pts.append((i / 120 * W, base - amp * n))
        pts.append((W, H))
        pygame.draw.polygon(surf, col, pts)
    ridge(hz, 250, (138, 74, 126), 2, 0.045)
    ridge(hz, 170, (92, 49, 112), 5, 0.07)
    ridge(hz, 95, (52, 33, 79), 9, 0.11)
    for y in range(hz, H):
        pygame.draw.line(surf, lerp((67, 48, 95), (13, 19, 48), (y - hz) / (H - hz)), (0, y), (W, y))
    rf = pygame.Surface((W, H), pygame.SRCALPHA)
    for _ in range(90):
        t = rnd.random() ** 1.4
        yy, ww = hz + 6 + t * (H - hz - 10), (1 - t) * 230 * (0.4 + rnd.random()) + 20
        pygame.draw.rect(rf, (255, 170 + int(rnd.random() * 50), 110, int(255 * (0.55 * (1 - t) + 0.08))),
                         (sx - ww / 2 + (rnd.random() - 0.5) * 60, yy, ww, 2 + rnd.random() * 3))
    surf.blit(rf, (0, 0))
    dark = (11, 14, 34)
    left = [(0, hz + 40)] + [cubic((0, hz + 40), (W * 0.18, hz + 30), (W * 0.3, H * 0.84), (W * 0.42, H), k / 30) for k in range(1, 31)] + [(0, H)]
    right = [(W, hz + 110)] + [cubic((W, hz + 110), (W * 0.9, hz + 120), (W * 0.84, H * 0.9), (W * 0.78, H), k / 30) for k in range(1, 31)] + [(W, H)]
    pygame.draw.polygon(surf, dark, left)
    pygame.draw.polygon(surf, dark, right)

    def pine(px, py, h):
        for i in range(4):
            w, y0 = h * (0.34 - i * 0.06), py - h * (0.2 + i * 0.22)
            pygame.draw.polygon(surf, dark, [(px, y0 - h * 0.34), (px - w, y0 + h * 0.1), (px + w, y0 + h * 0.1)])
        pygame.draw.rect(surf, dark, (px - h * 0.03, py - h * 0.2, h * 0.06, h * 0.2))
    for a in [(40, hz + 60, 230), (120, hz + 80, 300), (205, hz + 95, 210), (290, hz + 120, 260), (360, hz + 160, 180),
              (W - 40, hz + 140, 260), (W - 120, hz + 150, 200), (W - 190, hz + 175, 240)]:
        pine(*a)
    kx, ky = 410, hz + 215
    pygame.draw.rect(surf, (21, 22, 46), (kx, ky - 60, 110, 60))
    pygame.draw.polygon(surf, (21, 22, 46), [(kx - 14, ky - 58), (kx + 55, ky - 110), (kx + 124, ky - 58)])
    for wx in (kx + 20, kx + 68):
        pygame.draw.rect(surf, (255, 207, 107), (wx, ky - 44, 22, 20))
    rr = pygame.Surface((W, H), pygame.SRCALPHA)
    for wx in (kx + 18, kx + 66):
        pygame.draw.rect(rr, (255, 207, 107, 64), (wx, ky + 20, 26, 60))
    surf.blit(rr, (0, 0))
    for bx, by, s in [(900, 260, 18), (950, 240, 14), (990, 275, 12), (860, 290, 10)]:
        pygame.draw.lines(surf, (42, 27, 59), False, [(bx - s, by - s * 0.4), (bx - s * 0.4, by - s * 0.55), (bx, by),
                                                        (bx + s * 0.4, by - s * 0.55), (bx + s, by - s * 0.4)], 3)
    return surf


def sample_mosaic():
    W, H, T = 1400, 1000, 200
    surf = pygame.Surface((W, H))
    rnd = random.Random(21)
    pal = [(29, 53, 87), (38, 70, 83), (42, 157, 143), (142, 202, 230), (233, 196, 106), (244, 162, 97),
           (231, 111, 81), (241, 250, 238), (181, 131, 141), (109, 89, 122)]

    def pick(ex):
        while True:
            c = rnd.choice(pal)
            if c not in ex:
                return c
    for r in range(H // T):
        for c in range(W // T):
            X, Y = c * T, r * T
            bg = pick([])
            fg = pick([bg])
            ac = pick([bg, fg])
            surf.set_clip(pygame.Rect(X, Y, T, T))
            surf.fill(bg)
            kind, q = int(rnd.random() * 6), int(rnd.random() * 4)
            if kind == 0:
                pygame.draw.circle(surf, fg, (X + T // 2, Y + T // 2), int(T * 0.36))
                pygame.draw.circle(surf, ac, (X + T // 2, Y + T // 2), int(T * 0.14))
            elif kind == 1:
                pygame.draw.circle(surf, fg, (X + (q & 1) * T, Y + (q >> 1) * T), T)
            elif kind == 2:
                a = q * math.pi / 2
                pygame.draw.circle(surf, fg, (X + T / 2 + math.cos(a) * T / 2, Y + T / 2 + math.sin(a) * T / 2), T // 2)
            elif kind == 3:
                k = [(X, Y), (X + T, Y), (X + T, Y + T), (X, Y + T)]
                pygame.draw.polygon(surf, fg, [k[q], k[(q + 1) % 4], k[(q + 2) % 4]])
            elif kind == 4:
                for i in range(4):
                    if q & 1:
                        surf.fill(fg, (X + i * T // 4, Y, T // 8, T))
                    else:
                        surf.fill(fg, (X, Y + i * T // 4, T, T // 8))
            else:
                for i in range(3, 0, -1):
                    pygame.draw.circle(surf, fg if i % 2 else ac, (X + T // 2, Y + T // 2), int(T * 0.14 * i))
            surf.set_clip(None)
            if rnd.random() < 0.35:
                pygame.draw.circle(surf, ac, (X + T * (0.2 + rnd.random() * 0.6), Y + T * (0.2 + rnd.random() * 0.6)), 9)
    return surf


# ====================================================================
# Ses (dalgalar koddan üretilir)
# ====================================================================
class Sounds:
    def __init__(self):
        self.ok = False
        try:
            init = pygame.mixer.get_init()
            if not init:
                return
            self.rate, _, self.channels = init
            self.sounds = {
                "flip": self._make([(700, 1100, 0, 0.07, 0.25, "tri")]),
                "match": self._make([(660, 660, 0, 0.18, 0.3, "sin"), (990, 990, 0.08, 0.25, 0.28, "sin")]),
                "miss": self._make([(220, 150, 0, 0.22, 0.25, "tri")]),
                "win": self._make([(f, f, i * 0.12, 0.6, 0.22, "sin") for i, f in enumerate([523.25, 659.25, 783.99, 1046.5, 1318.5])]),
            }
            self.ok = True
        except Exception:
            self.ok = False

    def _make(self, tones):
        total = max(start + dur for _, _, start, dur, _, _ in tones) + 0.03
        n = int(self.rate * total)
        buf = [0.0] * n
        for f0, f1, start, dur, vol, kind in tones:
            s0, ln = int(start * self.rate), int(dur * self.rate)
            phase = 0.0
            for i in range(ln):
                t = i / self.rate
                f = f0 * (f1 / f0) ** min(1.0, t / (dur * 0.8))
                phase += 2 * math.pi * f / self.rate
                w = math.sin(phase) if kind == "sin" else 2 / math.pi * math.asin(math.sin(phase))
                env = min(1.0, t / 0.008) * math.exp(-5 * t / dur)
                if s0 + i < n:
                    buf[s0 + i] += w * env * vol
        data = array("h")
        for v in buf:
            data.extend([int(clamp(v, -1, 1) * 32000)] * self.channels)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def play(self, name, enabled):
        if self.ok and enabled:
            self.sounds[name].play()


# ====================================================================
# Kart
# ====================================================================
class Card:
    def __init__(self, sym, icon, rect):
        self.sym, self.icon, self.rect = sym, icon, rect
        self.up = False           # mantıksal durum: açık mı
        self.flip_t = -10.0       # son çevirme başlangıcı
        self.matched = False
        self.gone_t = None        # kalkma animasyonu başlangıcı
        self.shake_t = None
        self.mark = None          # "hit" | "miss"
        self.tile = None          # altındaki resim parçası


# ====================================================================
# Uygulama
# ====================================================================
class App:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        info = pygame.display.Info()
        self.W = max(1000, min(1400, info.current_w - 80))
        self.H = max(680, min(900, info.current_h - 120))
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Gizli Resim Avı")
        pygame.display.set_icon(self._brand_mark(32))
        self.clock = pygame.time.Clock()
        self.stage = pygame.Rect(0, BAR_H, self.W, self.H - BAR_H)

        def font(size, bold=False, mono=False):
            names = "consolas,dejavusansmono,couriernew" if mono else "segoeui,dejavusans,arial"
            return pygame.font.SysFont(names, size, bold=bold)
        self.f_brand = font(22, True)
        self.f_title = font(29, True)
        self.f_h2 = font(30, True)
        self.f_btn = font(15, True)
        self.f_body = font(15)
        self.f_small = font(13)
        self.f_label = font(11, True)
        self.f_value = font(19, True, mono=True)
        self.f_big_value = font(22, True, mono=True)
        self.emoji_path = None
        for name in ("segoeuiemoji", "notocoloremoji", "applecoloremoji", "twemojimozilla"):
            self.emoji_path = pygame.font.match_font(name)
            if self.emoji_path:
                break
        self.emoji_cache = {}

        self.settings = load_settings()
        self.level = clamp(int(self.settings.get("level", 1)), 0, len(LEVELS) - 1)
        self.theme = clamp(int(self.settings.get("theme", 0)), 0, len(THEMES) - 1)
        self.sound_on = bool(self.settings.get("sound", True))
        self.sounds = Sounds()

        self.bg = self._make_bg(self.stage.w, self.stage.h)
        self.dim = pygame.Surface(self.stage.size, pygame.SRCALPHA)
        self.dim.fill((10, 8, 22, 170))
        self.samples = {"sunset": sample_sunset().convert(), "mosaic": sample_mosaic().convert()}
        self.thumbs = {k: rounded(cover_crop(v, 68, 46), 8) for k, v in self.samples.items()}

        self.state = "play"          # play | setup | won
        self.cards, self.open = [], []
        self.timers, self.hot = [], []
        self.toast_msg, self.toast_until = "", 0
        self.show_result = True
        self.set_source(self.samples["sunset"], "Örnek · Gün batımı", "sunset")
        self.new_game()              # açılışta oyun hazır; ilk karta tıklayınca süre başlar

    # ---------- varlıklar ----------
    def _brand_mark(self, size):
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        w, h, g = size * 0.42, size * 0.46, size * 0.08
        for i, col in enumerate([BACK1, CORAL, CORAL, BACK1]):
            x, y = (i % 2) * (w + g), (i // 2) * (h + g)
            pygame.draw.rect(s, col, (x, y, w, h), border_radius=max(2, size // 10))
            if col == BACK1:
                pygame.draw.rect(s, GOLD, (x, y, w, h), 1, border_radius=max(2, size // 10))
        return s

    def _make_bg(self, w, h):
        surf = pygame.Surface((w, h))
        surf.fill(BG)
        steps = 40
        for i in range(steps):
            k = i / steps
            rw, rh = w * 1.4 * (1 - k), h * 1.2 * (1 - k)
            pygame.draw.ellipse(surf, lerp(BG, BG_GLOW, k ** 1.2), (w / 2 - rw / 2, h * 0.45 - rh / 2, rw, rh))
        return surf

    def emoji(self, ch, size):
        key = (ch, size)
        if key not in self.emoji_cache:
            try:
                f = pygame.font.Font(self.emoji_path, 64)
                img = f.render(ch, True, (60, 40, 110))
                k = size / max(img.get_size())
                img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
            except Exception:
                img = pygame.font.SysFont("segoeui", size, bold=True).render("?", True, (60, 40, 110))
            self.emoji_cache[key] = img
        return self.emoji_cache[key]

    # ---------- kaynak resim ----------
    def set_source(self, surf, name, sample_key=None):
        self.source, self.source_name, self.sample_key = surf, name, sample_key
        self.preview = None

    def load_image(self, path):
        try:
            img = pygame.image.load(path).convert()
            w, h = img.get_size()
            k = min(1, 2000 / max(w, h))
            if k < 1:
                img = pygame.transform.smoothscale(img, (int(w * k), int(h * k)))
        except Exception:
            self.toast("Bu dosya açılamadı. JPG, PNG, BMP, GIF veya WEBP bir resim seç.")
            return
        self.set_source(img, os.path.basename(path))
        self.open_setup()
        self.toast("Gizli resim hazır. Oyunu başlatabilirsin.")

    def upload(self):
        path = ask_image_path()
        if path:
            self.load_image(path)

    # ---------- oyun ----------
    def new_game(self):
        _, _, cols, rows = LEVELS[self.level]
        pairs = cols * rows // 2
        icons = random.sample(THEMES[self.theme][1], pairs)
        deck = [(i, ic) for i, ic in enumerate(icons)] * 2
        random.shuffle(deck)

        pad, gap = 10, 8
        st = self.stage.inflate(-36, -36)
        ratio = (cols * CARD_RATIO) / rows
        bw = min(st.w, st.h * ratio)
        bh = bw / ratio
        cw = int((bw - 2 * pad - gap * (cols - 1)) / cols)
        ch = int((bh - 2 * pad - gap * (rows - 1)) / rows)
        bw, bh = cw * cols + gap * (cols - 1) + 2 * pad, ch * rows + gap * (rows - 1) + 2 * pad
        self.board = pygame.Rect(0, 0, bw, bh)
        self.board.center = st.center
        self.cols, self.rows, self.pairs = cols, rows, pairs

        cover = cover_crop(self.source, bw, bh)
        self.reveal = rounded(cover, 18)
        self.card_back = self._render_back(cw, ch)
        self.card_front = self._render_front(cw, ch)
        radius = max(6, min(cw, ch) // 12)
        self.cards = []
        for i, (sym, icon) in enumerate(deck):
            r, c = divmod(i, cols)
            rect = pygame.Rect(self.board.x + pad + c * (cw + gap), self.board.y + pad + r * (ch + gap), cw, ch)
            card = Card(sym, icon, rect)
            card.tile = rounded(cover.subsurface((rect.x - self.board.x, rect.y - self.board.y, cw, ch)).copy(), radius)
            self.cards.append(card)
        self.open, self.timers = [], []
        self.moves = self.found = self.misses = 0
        self.elapsed, self.t0 = 0.0, None
        self.lock = False
        self.done, self.done_t = False, None
        self.state = "play"
        self.show_result = True

    def _render_back(self, w, h):
        s = pygame.Surface((w, h))
        for y in range(h):
            pygame.draw.line(s, lerp(BACK1, BACK2, y / h), (0, y), (w, y))
        pat = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(-h, w + h, 14):
            pygame.draw.line(pat, (255, 255, 255, 16), (x, 0), (x + h, h), 6)
            pygame.draw.line(pat, (255, 255, 255, 16), (x + h, 0), (x, h), 6)
        s.blit(pat, (0, 0))
        r = max(6, min(w, h) // 12)
        pygame.draw.rect(s, GOLD, s.get_rect(), 2, border_radius=r)
        inner = s.get_rect().inflate(-12, -12)
        pygame.draw.rect(s, lerp(GOLD, BACK2, 0.55), inner, 1, border_radius=max(3, r - 4))
        cr = int(min(w, h) * 0.2)
        circ = pygame.Surface((cr * 2, cr * 2), pygame.SRCALPHA)
        pygame.draw.circle(circ, (245, 201, 106, 46), (cr, cr), cr)
        s.blit(circ, (w // 2 - cr, h // 2 - cr))
        q = pygame.font.SysFont("segoeui", int(min(w, h) * 0.3), bold=True).render("?", True, GOLD)
        s.blit(q, q.get_rect(center=(w // 2, h // 2 + 1)))
        return rounded(s, r)

    def _render_front(self, w, h):
        s = pygame.Surface((w, h))
        s.fill(FACE)
        r = max(6, min(w, h) // 12)
        pygame.draw.rect(s, FACE_EDGE, s.get_rect(), 2, border_radius=r)
        return rounded(s, r)

    def clock_time(self):
        return self.elapsed + (time.perf_counter() - self.t0 if self.t0 is not None else 0)

    def stop_clock(self):
        if self.t0 is not None:
            self.elapsed += time.perf_counter() - self.t0
            self.t0 = None

    def after(self, delay, fn):
        self.timers.append((time.perf_counter() + delay, fn))

    def flip(self, card):
        if self.state != "play" or self.done or self.lock or card.matched or card in self.open:
            return
        now = time.perf_counter()
        if self.t0 is None:
            self.t0 = now
        card.up, card.flip_t = True, now
        self.open.append(card)
        self.sounds.play("flip", self.sound_on)
        if len(self.open) < 2:
            return
        self.moves += 1
        a, b = self.open
        if a.sym == b.sym:
            self.open = []
            a.matched = b.matched = True
            a.mark = b.mark = "hit"
            self.found += 1
            self.sounds.play("match", self.sound_on)

            def remove():
                t = time.perf_counter()
                a.gone_t = b.gone_t = t
                if self.found == self.pairs and not self.done:
                    self.win()
            self.after(0.52, remove)
        else:
            self.lock = True
            self.misses += 1

            def wrong():
                t = time.perf_counter()
                for c in (a, b):
                    c.mark, c.shake_t = "miss", t
                self.sounds.play("miss", self.sound_on)

            def close():
                t = time.perf_counter()
                for c in (a, b):
                    c.up, c.flip_t, c.mark = False, t, None
                self.open, self.lock = [], False
            self.after(0.38, wrong)
            self.after(1.05, close)

    def win(self):
        self.stop_clock()
        self.done, self.done_t = True, time.perf_counter()
        self.sounds.play("win", self.sound_on)
        lid, lname, _, _ = LEVELS[self.level]
        best_all = self.settings.setdefault("best", {})
        prev = best_all.get(lid)
        notes = []
        if not prev:
            notes.append("Bu seviyedeki ilk derecen kaydedildi")
            best_all[lid] = {"time": self.elapsed, "moves": self.moves}
        else:
            if self.elapsed < prev["time"]:
                notes.append("Yeni süre rekoru")
            if self.moves < prev["moves"]:
                notes.append("En az hamle rekoru")
            best_all[lid] = {"time": min(prev["time"], self.elapsed), "moves": min(prev["moves"], self.moves)}
        self._save()
        self.win_info = {"line": f"{lname} seviyesi · {self.pairs} çift · {self.misses} yanlış deneme",
                         "record": " · ".join(notes), "acc": round(self.pairs / self.moves * 100)}
        self.after(1.7, lambda: setattr(self, "state", "won") if self.done else None)

    def open_setup(self):
        if self.state == "setup":
            return
        self.stop_clock()
        self.prev_state = self.state
        self.state = "setup"

    def resume_from_setup(self):
        self.state = self.prev_state if self.done else "play"
        if not self.done and (self.moves or self.open):
            self.t0 = time.perf_counter()

    def start_from_setup(self):
        self.new_game()

    def toggle_sound(self):
        self.sound_on = not self.sound_on
        self._save()
        self.sounds.play("flip", self.sound_on)

    def _save(self):
        self.settings.update({"level": self.level, "theme": self.theme, "sound": self.sound_on})
        save_settings(self.settings)

    def toast(self, msg):
        self.toast_msg, self.toast_until = msg, time.perf_counter() + 2.6

    # ---------- olaylar ----------
    def handle(self, ev):
        if ev.type == pygame.DROPFILE:
            self.load_image(ev.file)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.state == "setup":
                    self.resume_from_setup()
                else:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif ev.key == pygame.K_r and self.state != "setup":
                self.new_game()
            elif ev.key == pygame.K_n and self.state != "setup":
                self.open_setup()
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state == "setup":
                self.start_from_setup()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for rect, cb in reversed(self.hot):
                if rect.collidepoint(ev.pos):
                    cb()
                    return
            if self.state == "play":
                for c in self.cards:
                    if c.rect.collidepoint(ev.pos) and c.gone_t is None:
                        self.flip(c)
                        break

    def update(self):
        now = time.perf_counter()
        due = [t for t in self.timers if t[0] <= now]
        self.timers = [t for t in self.timers if t[0] > now]
        for _, fn in due:
            fn()

    # ---------- çizim yardımcıları ----------
    def text(self, s, font, color, pos, anchor="topleft"):
        img = font.render(s, True, color)
        r = img.get_rect(**{anchor: pos})
        self.screen.blit(img, r)
        return r

    def button(self, rect, label, cb, kind="plain", active=False, font=None):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        if kind == "coral":
            bg, fg, border = (CORAL_HI if hover else CORAL), CORAL_INK, None
        elif active:
            bg, fg, border = (PANEL2 if hover else PANEL), CORAL_HI, CORAL
        else:
            bg, fg, border = (PANEL2 if hover else (PANEL if kind == "tool" else PANEL2)), TEXT, (MUTED if hover else LINE)
        pygame.draw.rect(self.screen, bg, rect, border_radius=11)
        if border:
            pygame.draw.rect(self.screen, border, rect, 1, border_radius=11)
        self.text(label, font or self.f_btn, fg, rect.center, "center")
        self.hot.append((rect, cb))
        return rect

    def card_panel(self, rect):
        rect = pygame.Rect(rect)
        sh = pygame.Surface((rect.w + 60, rect.h + 60), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 110), (30, 40, rect.w, rect.h), border_radius=24)
        sh = pygame.transform.smoothscale(pygame.transform.smoothscale(sh, ((rect.w + 60) // 6, (rect.h + 60) // 6)), sh.get_size())
        self.screen.blit(sh, (rect.x - 30, rect.y - 30))
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=20)
        pygame.draw.rect(self.screen, LINE, rect, 1, border_radius=20)
        return rect

    # ---------- çizim ----------
    def draw(self):
        self.hot = []
        scr = self.screen
        scr.fill(BG)
        scr.blit(self.bg, self.stage.topleft)
        self.draw_board()
        if self.state == "setup":
            scr.blit(self.dim, self.stage.topleft)
            self.draw_setup()
        elif self.state == "won":
            if self.show_result:
                self.draw_result()
            else:
                self.button(pygame.Rect(self.W // 2 - 90, self.H - 62, 180, 44), "Sonuçları göster",
                            lambda: setattr(self, "show_result", True), "coral")
        self.draw_bar()
        if self.toast_msg and time.perf_counter() < self.toast_until:
            img = self.f_body.render(self.toast_msg, True, TEXT)
            r = img.get_rect(midbottom=(self.W // 2, self.H - 18)).inflate(28, 16)
            pygame.draw.rect(scr, PANEL, r, border_radius=12)
            pygame.draw.rect(scr, LINE, r, 1, border_radius=12)
            scr.blit(img, img.get_rect(center=r.center))
        pygame.display.flip()

    def draw_board(self):
        scr, now = self.screen, time.perf_counter()
        b = self.board
        sh = pygame.Surface((b.w + 80, b.h + 80), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 120), (40, 55, b.w, b.h), border_radius=24)
        sh = pygame.transform.smoothscale(pygame.transform.smoothscale(sh, ((b.w + 80) // 8, (b.h + 80) // 8)), sh.get_size())
        scr.blit(sh, (b.x - 40, b.y - 40))
        pygame.draw.rect(scr, (13, 10, 26), b, border_radius=18)
        pygame.draw.rect(scr, (40, 34, 64), b, 1, border_radius=18)
        for c in self.cards:
            self.draw_card(c, now)
        if self.done and self.done_t is not None:
            k = clamp((now - self.done_t - 0.35) / 1.2, 0, 1)
            if k > 0:
                self.reveal.set_alpha(int(255 * ease_out(k)))
                scr.blit(self.reveal, b.topleft)

    def draw_card(self, c, now):
        scr, r = self.screen, c.rect
        # altındaki resim parçası (eşleşince yavaşça belirir)
        if c.gone_t is not None:
            k = clamp((now - c.gone_t) / 0.5, 0, 1)
            tile = c.tile
            if k < 1:
                s = 0.92 + 0.08 * ease_out(k)
                tile = pygame.transform.smoothscale(c.tile, (int(r.w * s), int(r.h * s)))
                tile.set_alpha(int(255 * k))
            scr.blit(tile, tile.get_rect(center=r.center))
            if k >= 1:
                return
            # kart kalkarken büyüyüp kaybolur
            fade = 1 - ease_out(clamp((now - c.gone_t) / 0.45, 0, 1))
            s = 1 + 0.12 * (1 - fade)
            img = self.card_face(c, True)
            img = pygame.transform.smoothscale(img, (int(r.w * s), int(r.h * s)))
            img.set_alpha(int(255 * fade))
            scr.blit(img, img.get_rect(center=r.center))
            return
        # çevirme animasyonu: yatayda daralıp öbür yüzle açılır
        k = clamp((now - c.flip_t) / FLIP_T, 0, 1)
        if k < 0.5:
            face_up, sx = (not c.up), 1 - 2 * k
        else:
            face_up, sx = c.up, 2 * k - 1
        sx = max(0.02, sx)
        dx = 0
        if c.shake_t is not None:
            t = now - c.shake_t
            if t < 0.38:
                dx = int(math.sin(t * 50) * 7 * (1 - t / 0.38))
        img = self.card_face(c, face_up)
        hover = (self.state == "play" and not face_up and not self.lock and r.collidepoint(pygame.mouse.get_pos()))
        lift = -3 if hover else 0
        sh = pygame.Rect(0, 0, int(r.w * sx), r.h)
        sh.center = (r.centerx + dx, r.centery + 5)
        pygame.draw.rect(scr, (8, 6, 18), sh, border_radius=10)
        if sx < 0.999:
            img = pygame.transform.smoothscale(img, (max(1, int(r.w * sx)), r.h))
        scr.blit(img, img.get_rect(center=(r.centerx + dx, r.centery + lift)))
        if hover:
            pygame.draw.rect(scr, CORAL, pygame.Rect(r.x, r.y + lift, r.w, r.h), 2, border_radius=max(6, min(r.w, r.h) // 12))

    def card_face(self, c, face_up):
        if not face_up:
            return self.card_back
        key = (c.icon, c.mark)
        cache = getattr(self, "_face_cache", None)
        if cache is None or cache.get("size") != c.rect.size:
            cache = self._face_cache = {"size": c.rect.size}
        if key not in cache:
            img = self.card_front.copy()
            w, h = c.rect.size
            e = self.emoji(c.icon, int(min(w, h) * 0.52))
            img.blit(e, e.get_rect(center=(w // 2, h // 2)))
            if c.mark:
                pygame.draw.rect(img, OK if c.mark == "hit" else BAD, img.get_rect(), 3, border_radius=max(6, min(w, h) // 12))
            cache[key] = img
        return cache[key]

    def draw_bar(self):
        scr = self.screen
        pygame.draw.rect(scr, PANEL, (0, 0, self.W, BAR_H))
        pygame.draw.line(scr, LINE, (0, BAR_H - 1), (self.W, BAR_H - 1))
        scr.blit(self._brand_mark(28), (16, BAR_H // 2 - 14))
        self.text("Gizli Resim Avı", self.f_brand, TEXT, (54, BAR_H // 2), "midleft")
        vals = [("SÜRE", fmt_time(self.clock_time())), ("HAMLE", str(self.moves)), ("BULUNAN", f"{self.found}/{self.pairs}")]
        x = 240
        for i, (k, v) in enumerate(vals):
            r = pygame.Rect(x + i * 108, 10, 100 if i < 2 else 130, BAR_H - 20)
            pygame.draw.rect(scr, PANEL2, r, border_radius=12)
            pygame.draw.rect(scr, LINE, r, 1, border_radius=12)
            self.text(k, self.f_label, MUTED, (r.x + 12, r.y + 6))
            self.text(v, self.f_value, TEXT, (r.x + 12, r.y + 19))
            if i == 2:
                n = self.pairs
                step = min(8, (r.w - 24) / max(1, n))
                for j in range(n):
                    pygame.draw.circle(scr, CORAL if j < self.found else (62, 55, 88), (r.x + 15 + j * step, r.bottom - 7), 2.6)
        right = self.W - 16
        tools = [("Yeni oyun", self.open_setup, "coral", False),
                 ("Karıştır", self.new_game, "tool", False),
                 ("Ses: Açık" if self.sound_on else "Ses: Kapalı", self.toggle_sound, "tool", self.sound_on)]
        for label, cb, kind, active in tools:
            w = self.f_btn.size(label)[0] + 28
            self.button((right - w, 15, w, BAR_H - 30), label, cb, kind, active)
            right -= w + 6

    def draw_setup(self):
        scr = self.screen
        cw, ch = min(940, self.W - 48), min(560, self.stage.h - 40)
        card = pygame.Rect(0, 0, cw, ch)
        card.center = self.stage.center
        self.card_panel(card)
        pr = pygame.Rect(card.x + 24, card.y + 24, int((cw - 70) * 0.48), ch - 74)
        pygame.draw.rect(scr, (14, 11, 28), pr, border_radius=16)
        if self.preview is None or self.preview[0] != pr.size:
            sw, sh_ = self.source.get_size()
            k = min((pr.w - 24) / sw, (pr.h - 24) / sh_)
            self.preview = (pr.size, rounded(pygame.transform.smoothscale(self.source, (int(sw * k), int(sh_ * k))), 8))
        img = self.preview[1]
        scr.blit(img, img.get_rect(center=pr.center))
        self.hot.append((pr, self.upload))
        hov = pr.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(scr, CORAL if hov else LINE, pr, 2 if hov else 1, border_radius=16)
        if hov:
            hint = self.f_small.render("Tıkla veya resmi pencereye sürükle", True, TEXT)
            hr = hint.get_rect(midbottom=(pr.centerx, pr.bottom - 14)).inflate(22, 10)
            pygame.draw.rect(scr, (22, 18, 38), hr, border_radius=12)
            scr.blit(hint, hint.get_rect(center=hr.center))
        name = self.source_name if len(self.source_name) <= 44 else self.source_name[:41] + "..."
        self.text(name, self.f_small, MUTED, (pr.x + 2, pr.bottom + 10))
        self.text(f"{self.source.get_width()} × {self.source.get_height()}", self.f_small, MUTED, (pr.right - 2, pr.bottom + 10), "topright")

        x, y = pr.right + 26, card.y + 24
        sw = card.right - 24 - x
        self.text("YENİ OYUN", self.f_label, CORAL, (x, y))
        y += 18
        self.text("Çiftleri bul, arkadaki", self.f_title, TEXT, (x, y))
        y += 34
        self.text("resmi ortaya çıkar.", self.f_title, TEXT, (x, y))
        y += 50
        self.text("GİZLİ RESİM", self.f_label, MUTED, (x, y))
        y += 18
        self.button((x, y, 130, 46), "Resim yükle", self.upload)
        tx = x + 140
        for key, label in (("sunset", "Örnek · Gün batımı"), ("mosaic", "Örnek · Mozaik")):
            r = pygame.Rect(tx, y, 68, 46)
            scr.blit(self.thumbs[key], r)
            pygame.draw.rect(scr, CORAL if self.sample_key == key else LINE, r.inflate(4, 4), 2, border_radius=10)
            self.hot.append((r, lambda k=key, n=label: self.set_source(self.samples[k], n, k)))
            tx += 78
        y += 64
        self.text("KART RESİMLERİ", self.f_label, MUTED, (x, y))
        y += 18
        bw = (sw - 12) // 3
        for i, (tname, icons) in enumerate(THEMES):
            r = pygame.Rect(x + i * (bw + 6), y, bw, 58)
            self._seg(r, i == self.theme, lambda i=i: self._set("theme", i))
            ex = r.centerx - 30
            for j, ic in enumerate(icons[:3]):
                e = self.emoji(ic, 26)
                scr.blit(e, e.get_rect(center=(ex + j * 30, r.y + 19)))
            self.text(tname, self.f_small, TEXT, (r.centerx, r.y + 32), "midtop")
        y += 70
        self.text("ZORLUK", self.f_label, MUTED, (x, y))
        y += 18
        bw = (sw - 18) // 4
        for i, (_, lname, c_, r_) in enumerate(LEVELS):
            r = pygame.Rect(x + i * (bw + 6), y, bw, 50)
            sel = i == self.level
            self._seg(r, sel, lambda i=i: self._set("level", i))
            self.text(lname, self.f_btn, TEXT, (r.centerx, r.y + 6), "midtop")
            self.text(f"{c_ * r_ // 2} çift", self.f_small, CORAL_HI if sel else MUTED, (r.centerx, r.y + 27), "midtop")
        y += 62
        lid, lname, _, _ = LEVELS[self.level]
        rec = self.settings.get("best", {}).get(lid)
        box = pygame.Rect(x, y, sw, 38)
        pygame.draw.rect(scr, PANEL2, box, border_radius=12)
        pygame.draw.rect(scr, LINE, box, 1, border_radius=12)
        msg = (f"En iyi derecen ({lname}): {fmt_time(rec['time'])} · {rec['moves']} hamle" if rec
               else f"{lname} seviyesinde henüz derecen yok. İlkini sen koy.")
        self.text(msg, self.f_small, TEXT if rec else MUTED, (box.x + 12, box.centery), "midleft")
        ay = card.bottom - 74
        if not self.done:
            self.button((x, ay, 130, 50), "Oyuna dön", self.resume_from_setup)
            self.button((x + 138, ay, sw - 138, 50), "Oyunu Başlat", self.start_from_setup, "coral", font=self.f_brand)
        else:
            self.button((x, ay, sw, 50), "Oyunu Başlat", self.start_from_setup, "coral", font=self.f_brand)

    def _seg(self, r, sel, cb):
        hov = r.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, (58, 36, 64) if sel else ((50, 42, 78) if hov else PANEL2), r, border_radius=12)
        pygame.draw.rect(self.screen, CORAL if sel else LINE, r, 1, border_radius=12)
        self.hot.append((r, cb))

    def _set(self, attr, i):
        setattr(self, attr, i)
        self._save()

    def draw_result(self):
        info = self.win_info
        h = 300 if info["record"] else 266
        r = pygame.Rect(0, 0, 470, h)
        r.midbottom = (self.W // 2, self.H - 16)
        self.card_panel(r)
        self.text("Resmi buldun!", self.f_h2, TEXT, (r.centerx, r.y + 18), "midtop")
        self.text(info["line"], self.f_body, MUTED, (r.centerx, r.y + 62), "midtop")
        bw = (r.w - 48 - 16) // 3
        for i, (k, v) in enumerate([("SÜRE", fmt_time(self.elapsed)), ("HAMLE", str(self.moves)), ("İSABET", f"%{info['acc']}")]):
            b = pygame.Rect(r.x + 24 + i * (bw + 8), r.y + 96, bw, 60)
            pygame.draw.rect(self.screen, PANEL2, b, border_radius=12)
            pygame.draw.rect(self.screen, LINE, b, 1, border_radius=12)
            self.text(k, self.f_label, MUTED, (b.centerx, b.y + 9), "midtop")
            self.text(v, self.f_big_value, TEXT, (b.centerx, b.y + 25), "midtop")
        if info["record"]:
            img = self.f_small.render(info["record"], True, OK)
            pr = img.get_rect(midtop=(r.centerx, r.y + 172)).inflate(24, 10)
            pygame.draw.rect(self.screen, (30, 60, 56), pr, border_radius=14)
            self.screen.blit(img, img.get_rect(center=pr.center))
        bw = (r.w - 48 - 12) // 3
        y = r.bottom - 70
        self.button((r.x + 24, y, bw, 46), "Resme bak", lambda: setattr(self, "show_result", False))
        self.button((r.x + 30 + bw, y, bw, 46), "Yeni resim", self.open_setup)
        self.button((r.x + 36 + 2 * bw, y, bw, 46), "Tekrar oyna", self.new_game, "coral")

    # ---------- ana döngü ----------
    def run(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                else:
                    self.handle(ev)
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    App().run()

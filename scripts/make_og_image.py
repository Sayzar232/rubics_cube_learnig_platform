# -*- coding: utf-8 -*-
"""Генерация OG-картинки (1200x630) для превью в соцсетях: frontend/public/og-image.png."""
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (11, 17, 32)          # #0b1120 тёмный фон
ACCENT = (37, 99, 235)     # #2563eb
YELLOW = (251, 191, 36)    # #fbbf24
RED = (239, 68, 68)        # #ef4444
BLUE = (59, 130, 246)      # #3b82f6
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
font_big = ImageFont.truetype(os.path.join(FONT_DIR, "arialbd.ttf"), 96)
font_sub = ImageFont.truetype(os.path.join(FONT_DIR, "arialbd.ttf"), 40)
font_small = ImageFont.truetype(os.path.join(FONT_DIR, "arial.ttf"), 30)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Мягкие акцентные пятна на фоне
for cx, cy, r, color in ((-80, -60, 380, (30, 58, 138)), (1280, 690, 420, (30, 58, 138))):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)

# Изометрический кубик Рубика (как логотип на сайте)
cx, cy, s = 215, 315, 150  # центр и полуширина
top = [(cx, cy - s), (cx + s, cy - s / 2), (cx, cy), (cx - s, cy - s / 2)]
left = [(cx - s, cy - s / 2), (cx, cy), (cx, cy + s), (cx - s, cy + s / 2)]
right = [(cx + s, cy - s / 2), (cx, cy), (cx, cy + s), (cx + s, cy + s / 2)]
draw.polygon(top, fill=YELLOW)
draw.polygon(left, fill=RED)
draw.polygon(right, fill=BLUE)

# Текстовый блок
text_x = 480
draw.text((text_x, 165), "Cube", font=font_big, fill=WHITE)
w = draw.textlength("Cube", font=font_big)
draw.text((text_x + w, 165), "Learn", font=font_big, fill=ACCENT)

draw.text((text_x, 300), "Скоростная сборка кубика Рубика", font=font_sub, fill=WHITE)
draw.text((text_x, 365), "Метод CFOP: 57 OLL + 21 PLL", font=font_sub, fill=MUTED)

draw.line((text_x, 470, 1090, 470), fill=(51, 65, 85), width=2)
draw.text((text_x, 500), "Диаграммы · видеоуроки · отслеживание прогресса", font=font_small, fill=MUTED)

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, "frontend", "public", "og-image.png")
img.save(out, "PNG", optimize=True)
print("saved:", out, img.size)

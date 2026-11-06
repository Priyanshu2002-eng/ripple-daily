#!/usr/bin/env python3
"""Ripple Daily cover, brand standard: black background, white "R" with a square violet full stop (the R. mark),
"Ripple" in white and "Daily" in violet. Usage: make_cover.py [out.jpg]"""
import sys
from PIL import Image, ImageDraw, ImageFont
S = 3000
F = "/usr/share/fonts/opentype/inter/"
BLACK, WHITE, VIOLET = (3, 3, 3), (243, 243, 243), (139, 92, 246)   # violet #8B5CF6
im = Image.new("RGB", (S, S), BLACK); d = ImageDraw.Draw(im)
big = ImageFont.truetype(F + "InterDisplay-Black.otf", 2050)
bb = d.textbbox((0, 0), "R", font=big); rw, rh = bb[2] - bb[0], bb[3] - bb[1]
sq = int(rh * 0.25); gap = int(rh * 0.06)
x = (S - (rw + gap + sq)) // 2; top = 330
d.text((x - bb[0], top - bb[1]), "R", font=big, fill=WHITE)
d.rectangle([x + rw + gap, top + rh - sq, x + rw + gap + sq, top + rh], fill=VIOLET)
word = ImageFont.truetype(F + "InterDisplay-ExtraBold.otf", 330)
w1, w2 = d.textlength("Ripple ", font=word), d.textlength("Daily", font=word)
wx = (S - (w1 + w2)) / 2; wy = top + rh + 300
d.text((wx, wy), "Ripple ", font=word, fill=WHITE)
d.text((wx + w1, wy), "Daily", font=word, fill=VIOLET)
out = sys.argv[1] if len(sys.argv) > 1 else "cover.jpg"
im.save(out, quality=92, optimize=True)

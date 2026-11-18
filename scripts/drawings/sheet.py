"""Lay the rendered views side by side on one sheet: python3 sheet.py out/sheet.png "title" out/a_0.png out/a_1.png out/b_0.png"""
import sys
from PIL import Image, ImageDraw
out, title, files = sys.argv[1], sys.argv[2], sys.argv[3:]
ims = [Image.open(f).convert("RGB") for f in files]
c = Image.new("RGB", (sum(i.width for i in ims), max(i.height for i in ims) + 40), "white")
x = 0
for i in ims:
    c.paste(i, (x, 40)); x += i.width
ImageDraw.Draw(c).text((10, 10), title, fill=(0, 0, 0))
c.save(out)

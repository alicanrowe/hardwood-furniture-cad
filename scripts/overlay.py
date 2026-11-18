#!/usr/bin/env python3
"""Labels and encode for a build animation: flattens each RGBA frame onto pure white, sets each step's
title and note straight on the white (no box, plate or scrim), fades them in and out, and encodes an MP4.

  python3 scripts/overlay.py build/frames build/anim.track.json --out build/build.mp4 [--audio music.wav]

Type follows assets/theme.json: serif title in uppercase, mono note, grey ink. Labels sit in a fixed band
(top-left for 16:9; clear of the top 220 px and bottom 380 px of a 9:16 reel, where Instagram draws its UI).
Fades are 0.6 s with an ease-in-out. Missing frames (rendered with --every N) are held from the previous one.
"""
import argparse, glob, json, math, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import furnlib as F


def ease(t):
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("frames"); ap.add_argument("track"); ap.add_argument("--out", default="build.mp4")
    ap.add_argument("--audio"); ap.add_argument("--theme"); ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()
    T = F.theme(a.theme)
    tr = json.load(open(a.track))
    fps, N = tr["fps"], tr["frames"]
    files = {int(re.findall(r"(\d+)", os.path.basename(p))[-1]): p for p in glob.glob(os.path.join(a.frames, "*.png"))}
    if not files:
        sys.exit("no frames")
    tmp = tempfile.mkdtemp()
    last = None
    ink = tuple(int(c * 255) for c in F.hex_rgb(T["ink_heading"]))
    note_ink = tuple(int(c * 255) for c in F.hex_rgb(T["ink"]))
    for fr in range(1, N + 1):
        if fr in files:
            last = files[fr]
        im = Image.open(last).convert("RGBA")
        W, H = im.size
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
        s = W / 1440 if W >= H else W / 390               # site px -> canvas px
        tf = ImageFont.truetype(T["fonts"]["serif_display"], int(21 * s * (1.4 if W >= H else 1.0)))
        nf = ImageFont.truetype(T["fonts"]["mono"], int(11.5 * s * (1.3 if W >= H else 1.0)))
        x0 = int(24 * s) if W >= H else int(23 * s)
        y0 = int(24 * s) if W >= H else max(240, int(H * 0.14))
        txt = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
        for st in tr["steps"]:
            fade = 0.6 * fps
            if not (st["start"] <= fr <= st["end"]):
                continue
            al = min(ease((fr - st["start"]) / fade), ease((st["end"] - fr) / fade))
            if al <= 0:
                continue
            d.text((x0, y0), st["title"].upper(), font=tf, fill=(*ink, int(255 * al)))
            if st.get("note"):
                d.text((x0, y0 + int(tf.size * 1.5)), st["note"], font=nf, fill=(*note_ink, int(255 * al)))
        im = Image.alpha_composite(im, txt).convert("RGB")
        im.save(os.path.join(tmp, f"o{fr:05d}.jpg"), quality=94)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "o%05d.jpg")]
    if a.audio:
        cmd += ["-i", a.audio, "-shortest", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(a.crf), "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)
    print(f"{N} frames, {N / fps:.1f} s -> {a.out}")


if __name__ == "__main__":
    main()

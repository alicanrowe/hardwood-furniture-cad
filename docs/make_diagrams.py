#!/usr/bin/env python3
"""Draws the teaching diagrams in docs/lessons/ (before / after for each rule) in the house theme.
Every number on them is measured from the geometry drawn, not typed in.

  python3 docs/make_diagrams.py
"""
import json, math, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, Circle
from shapely.geometry import box, Polygon, Point, LineString
from shapely.ops import nearest_points, unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "lessons"); os.makedirs(OUT, exist_ok=True)
T = json.load(open(os.path.join(ROOT, "assets", "theme.json")))
F = {k: os.path.join(ROOT, "assets", v) for k, v in T["fonts"].items()}
for f in F.values():
    fm.fontManager.addfont(f)
plt.rcParams["hatch.color"] = "#C9B994"
plt.rcParams["hatch.linewidth"] = 0.4
SERIF = fm.FontProperties(fname=F["serif_display"]); BODY = fm.FontProperties(fname=F["serif"]); MONO = fm.FontProperties(fname=F["mono"])
RED, INK, HEAD, MUTED, WOOD, WOOD2, HATCH = T["red"], T["ink"], T["ink_heading"], T["muted"], T["wood_fill"], T["wood_fill_end"], T["hatch"]


def frac(x, den=32):
    n = round(x * den); w, r = divmod(n, den)
    if not r: return f"{w}"
    g = math.gcd(r, den); return (f"{w} " if w else "") + f"{r // g}/{den // g}"


def fig(n, w=4.2, h=4.6, title=None):
    f, axs = plt.subplots(1, n, figsize=(w * n, h), dpi=220)
    axs = [axs] if n == 1 else list(axs)
    f.patch.set_facecolor("white")
    for a in axs:
        a.set_aspect("equal"); a.axis("off")
    if title:
        f.subplots_adjust(top=0.80)
        f.text(0.03, 0.99, title.upper(), fontproperties=SERIF, fontsize=17, color=HEAD, va="top")
    return f, axs


def draw(ax, geom, fill=WOOD, hatch=True, lw=1.1, end=False):
    gs = geom.geoms if hasattr(geom, "geoms") else [geom]
    for g in gs:
        ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc=WOOD2 if end else fill, ec=INK, lw=lw,
                           hatch="////" if hatch else None, zorder=2))
        for h in g.interiors:
            ax.add_patch(MPoly(list(h.coords), closed=True, fc="white", ec=INK, lw=lw, zorder=3))


def label(ax, x, y, s, color=INK, size=9, font=None, **kw):
    ax.text(x, y, s, fontproperties=font or MONO, fontsize=size, color=color, **kw)


def head(ax, s, sub=None, ok=None):
    col = RED if ok is False else HEAD
    ax.set_title(s.upper(), fontproperties=SERIF, fontsize=13, color=col, loc="left", pad=14)


def neck_line(ax, a, b, txt, dx=0.05, dy=0.05):
    p, q = nearest_points(a, b)
    ax.plot([p.x, q.x], [p.y, q.y], color=RED, lw=2.4, zorder=5, solid_capstyle="butt")
    d = p.distance(q)
    label(ax, (p.x + q.x) / 2 + dx, (p.y + q.y) / 2 + dy, txt.format(d=d), color=RED, size=9, zorder=6)
    return d


def save(f, name):
    f.savefig(os.path.join(OUT, name), facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(f)
    print("wrote", name)


# ------------------------------------------------------------------ 1. corner post neck
def corner(ax, depth, off, title, ok, post=1.0, gw=0.25):
    P = box(0, 0, post, post)
    gA = box(post - depth, off, post, off + gw)            # front wall groove, entered from the right face
    gB = box(off, post - depth, off + gw, post)            # side wall groove, entered from the top face
    body = P.difference(gA).difference(gB)
    draw(ax, body, end=True)
    # tenons in the grooves
    for g, rect in ((gA, box(post - depth + 0.02, off, post + 0.6, off + gw)), (gB, box(off, post - depth + 0.02, off + gw, post + 0.6))):
        pass
    draw(ax, box(post, off - 0.0, post + 0.55, off + gw), hatch=False, fill="#F4EEE2")
    draw(ax, box(post - depth + 1 / 64, off, post, off + gw), hatch=False, fill="#F4EEE2", lw=0.6)
    draw(ax, box(off, post, off + gw, post + 0.55), hatch=False, fill="#F4EEE2")
    draw(ax, box(off, post - depth + 1 / 64, off + gw, post), hatch=False, fill="#F4EEE2", lw=0.6)
    d = neck_line(ax, gA, gB, "neck {d:.2f} in", dx=-0.42, dy=-0.13)
    ax.set_xlim(-0.15, post + 0.7); ax.set_ylim(-0.75, post + 0.7)
    label(ax, 0, -0.25, f"grooves {frac(depth)} deep, {frac(off)} from outside", size=8)
    label(ax, 0, -0.38, f"outside cheek {frac(off)} in", size=8)
    label(ax, 0, -0.51, f"inside block {frac(post - off - gw)} in square", size=8)
    label(ax, 0, -0.66, "OK" if ok else "TOO THIN: snaps along the grain", color=RED if not ok else INK, size=8)
    label(ax, -0.12, post / 2, "OUTSIDE", size=7, color=MUTED, rotation=90, va="center")
    label(ax, post / 2, -0.12, "OUTSIDE", size=7, color=MUTED, ha="center")
    head(ax, title, ok=ok)
    return d


f, axs = fig(3, title="Corner post: check the neck between two grooves")
corner(axs[0], 3 / 8, 1 / 4, "As drawn", False)
corner(axs[1], 3 / 8, 3 / 16, "Biased 1/16 out", True)
corner(axs[2], 5 / 16, 3 / 16, "Biased + 5/16 deep", True)
save(f, "corner-neck.png")


# ------------------------------------------------------------------ 2. one stick, two cuts: web
def stick(ax, bad):
    t, h = 0.75, 1.25                 # rail thickness (x) and height (y); outside at x=0
    R = box(0, 0, t, h)
    pg = box(0.25, h - 0.375, 0.5, h)                       # panel groove on top
    if bad:
        c2 = box(0.375, 0.5, t, 0.75)                       # second groove for the floor, from the inside
        floor = box(0.375 + 1 / 64, 0.5, t + 0.9, 0.75)
    else:
        R = box(0, 0, 1.0, h); t = 1.0
        pg = box(3 / 16, h - 0.375, 3 / 16 + 0.25, h)
        c2 = box(0.5, 0, t, 0.625)                          # rabbet on the inside bottom edge
        floor = box(0.5 + 1 / 64, 0.25, t + 0.9, 0.625)
    body = R.difference(pg).difference(c2)
    draw(ax, body, end=True)
    draw(ax, box(pg.bounds[0], pg.bounds[1] + 1 / 16, pg.bounds[2], h + 0.5), hatch=False, fill="#F4EEE2")
    draw(ax, floor, hatch=False, fill="#EFE8DA")
    label(ax, t + 0.95, (floor.bounds[1] + floor.bounds[3]) / 2, "floor", size=8, va="center")
    label(ax, pg.bounds[2] + 0.05, h + 0.3, "panel", size=8)
    d = neck_line(ax, pg, c2, "web {d:.2f} in", dx=0.12, dy=0.04 if bad else 0.06)
    if not bad:
        # apron tongue under the floor
        draw(ax, unary_union([box(0, -0.6, 1.125, -1 / 64), box(0.5 + 1 / 32, -0.02, 1.0 - 1 / 32, 0.25 - 1 / 64)]), hatch=True, fill=WOOD)
        label(ax, 1.25, -0.2, "stand apron with a tongue:", size=8, va="center")
        label(ax, 1.25, -0.33, "the rabbet drops over it", size=8, va="center")
    label(ax, 0, -0.85 if not bad else -0.25, ("1 x 1 1/4 rail: groove 3/16 from outside, rabbet 1/2 x 5/8"
                                               if not bad else "3/4 x 1 1/4 rail: panel groove over a floor groove"), size=8)
    label(ax, 0, -1.0 if not bad else -0.4, "solid inside cheek, 1/4 in web" if not bad else "1/8 in web, thin inside cheek", size=8,
          color=RED if bad else INK)
    ax.set_xlim(-0.2, 3.2); ax.set_ylim(-1.15, h + 0.65)
    head(ax, "Fails the gut check" if bad else "Rabbet instead of a second groove", ok=not bad)


f, axs = fig(2, w=5.2, h=4.4, title="One stick, two cuts: keep 1/4 in of web")
stick(axs[0], True); stick(axs[1], False)
save(f, "rail-web.png")


# ------------------------------------------------------------------ 3. thicken on the inside only
def thick(ax, t, ok):
    post = box(0, 0, 1, 1)
    gA = box(1 - 5 / 16, 3 / 16, 1, 3 / 16 + 0.25)
    draw(ax, post.difference(gA), end=True)
    rail = box(1, 0, 3.2, t)
    draw(ax, rail, hatch=True)
    draw(ax, box(1 - 5 / 16 + 1 / 64, 3 / 16, 1, 3 / 16 + 0.25), hatch=False, fill="#F4EEE2", lw=0.6)
    ax.plot([0, 3.4], [0, 0], color=MUTED, lw=0.6, ls=(0, (4, 3)))
    label(ax, 3.25, -0.02, "outside face", size=7, color=MUTED, va="center")
    ax.annotate("", xy=(3.35, 0), xytext=(3.35, t), arrowprops=dict(arrowstyle="<->", color=RED, lw=0.8))
    label(ax, 3.42, t / 2, f"{frac(t)}", color=RED, size=9, va="center")
    if not ok:
        ax.add_patch(MPoly([(1, t), (1, 1), (1.15, 1), (1.15, t)], closed=True, fc="none", ec=RED, lw=1.2, ls=(0, (2, 2))))
        label(ax, 1.25, 1.12, "shoulder seats on 3/4 of the post;", size=8, color=RED)
        label(ax, 1.25, 0.95, "the inside corner is a lone square", size=8, color=RED)
    else:
        label(ax, 1.25, 1.3, "filled out flush with the inside of the post;", size=8)
        label(ax, 1.25, 1.13, "the outside doesn't change", size=8)
    ax.set_xlim(-0.2, 4.1); ax.set_ylim(-0.45, 1.5)
    head(ax, "Rail 3/4, post 1" if not ok else "Rail 1, flush inside", ok=ok)


f, axs = fig(2, w=5.0, h=2.6, title="Thicken on the inside only (plan)")
thick(axs[0], 0.75, False); thick(axs[1], 1.0, True)
save(f, "thicken-inside.png")


# ------------------------------------------------------------------ 4. mortise near the end of a leg
def leg(ax, start, haunch):
    L = box(0, 0, 2.0, 3.0)                     # leg top, elevation, top at y=3
    mh = 1.75
    m = box(0.75, 3 - start - mh, 1.25, 3 - start)
    draw(ax, L.difference(m), hatch=True)
    ax.add_patch(MPoly(list(m.exterior.coords), closed=True, fc="white", ec=INK, lw=1.0, ls=(0, (3, 2)), zorder=3))
    # apron tenon
    ten = box(0.75 + 1 / 64, 3 - start - mh + 1 / 64, 1.25 - 1 / 64, 3 - start - 1 / 64)
    cap = box(0.75, 3 - start, 1.25, 3)
    ax.annotate("", xy=(2.25, 3), xytext=(2.25, 3 - start), arrowprops=dict(arrowstyle="<->", color=RED, lw=0.8))
    label(ax, 2.35, 3 - start / 2, f"{frac(start)} to the top", color=RED, size=9, va="center")
    if haunch:
        hn = box(0.75, 3 - start, 1.25, 3 - start + 0.25)
        ax.add_patch(MPoly(list(hn.exterior.coords), closed=True, fc="#F4EEE2", ec=INK, lw=0.8, zorder=4))
        label(ax, 2.35, 2.25, "haunch 1/4 deep fills it", size=8, va="center")
    else:
        ax.add_patch(MPoly(list(cap.exterior.coords), closed=True, fc="none", ec=RED, lw=1.6, zorder=4))
        label(ax, 2.35, 2.5, "thin cap of short grain", size=8, color=RED)
        label(ax, 2.35, 2.3, "blows out when the joint", size=8, color=RED)
        label(ax, 2.35, 2.1, "is driven home", size=8, color=RED)
    label(ax, -0.1, 3 - start - mh / 2, "mortise", size=8, ha="right", va="center")
    ax.set_xlim(-0.6, 4.4); ax.set_ylim(0.6, 3.4)
    head(ax, "Mortise 1/4 from the top" if not haunch else "1/2 down, haunched tenon", ok=haunch)


f, axs = fig(2, w=4.6, h=3.8, title="Mortises keep away from the end of a leg")
leg(axs[0], 0.25, False); leg(axs[1], 0.5, True)
save(f, "leg-mortise.png")


# ------------------------------------------------------------------ 5. muntin tenons in pockets
def muntin(ax, long_):
    rail_t = box(0, 3.0, 3.0, 4.0)          # top rail (section along the rail), groove on its underside
    groove = box(0, 3.0, 3.0, 3.375)
    mw = 1.0; mx0 = 1.0
    pocket_d = 0.75 if long_ else 0.375
    pocket = box(mx0 + 0.25, 3.0, mx0 + 0.75, 3.0 + pocket_d)
    draw(ax, rail_t.difference(groove).difference(pocket), hatch=True)
    mun = box(mx0, 0, mx0 + mw, 3.0)
    ten = box(mx0 + 0.25, 3.0, mx0 + 0.75, 3.0 + pocket_d - 1 / 32)
    draw(ax, unary_union([mun, ten]), hatch=True, fill="#F4EEE2")
    for x0, x1 in ((0, mx0), (mx0 + mw, 3.0)):
        draw(ax, box(x0, 1.0, x1, 3.0 + 0.375 - 1 / 16), hatch=False, fill="#EFE8DA", lw=0.6)
    ax.annotate("", xy=(3.2, 3.0), xytext=(3.2, 3.0 + pocket_d), arrowprops=dict(arrowstyle="<->", color=RED, lw=0.8))
    label(ax, 3.3, 3.0 + pocket_d / 2, f"tenon {frac(pocket_d)}", color=RED, size=9, va="center")
    label(ax, 0.05, 1.5, "panel", size=8); label(ax, mx0 + 0.1, 1.5, "muntin", size=8)
    label(ax, 0, -0.2, "deeper pocket inside the groove:" if long_ else "stub only fills the groove:", size=8)
    label(ax, 0, -0.45, "the groove still locates it, the pocket holds it" if long_ else "little glue area, racks loose", size=8,
          color=INK if long_ else RED)
    ax.set_xlim(-0.2, 4.3); ax.set_ylim(-0.6, 4.2)
    head(ax, "Stub tenon" if not long_ else "Long tenon, deep pocket", ok=long_)


f, axs = fig(2, w=4.2, h=4.4, title="Muntin tenons: long, in pockets inside the groove")
muntin(axs[0], False); muntin(axs[1], True)
save(f, "muntin-tenon.png")


# ------------------------------------------------------------------ 6. case on stand
def stand(ax, strips):
    # section across one side: case bottom rail at x 0..1, floor inward, stand apron below
    if strips:
        rail = box(0, 0, 0.75, 1.25).difference(box(0.375, 0.5, 0.75, 0.75))
        floor = box(0.375 + 1 / 64, 0.5, 3.0, 0.75)
        strip = box(0.75, 0.125, 1.125, 0.5)
        draw(ax, rail, end=True); draw(ax, floor, hatch=False, fill="#EFE8DA")
        draw(ax, strip, hatch=True, fill="#E9D7B7")
        apron = box(0.0, -1.6, 0.75, 0.0 - 1 / 64)
        draw(ax, apron, hatch=True)
        ax.add_patch(Circle((0.95, 0.31), 0.32, fc="none", ec=RED, lw=1.4, zorder=6))
        label(ax, 1.35, 0.3, "glued-on locating strip:", size=8, color=RED)
        label(ax, 1.35, 0.08, "shows under the case, falls off", size=8, color=RED)
    else:
        rail = box(0, 0, 1.0, 1.25).difference(box(0.5, 0, 1.0, 0.625)).difference(box(3 / 16, 0.875, 7 / 16, 1.25))
        floor = box(0.5 + 1 / 64, 0.25, 3.0, 0.625)
        draw(ax, rail, end=True); draw(ax, floor, hatch=False, fill="#EFE8DA")
        apron = unary_union([box(0.0, -1.6, 1.125, 0.0 - 1 / 64), box(0.5 + 1 / 32, -0.1, 1.125, 0.25 - 1 / 64)])
        draw(ax, apron, hatch=True)
        label(ax, 1.35, 0.05, "rabbet all round the case bottom", size=8)
        label(ax, 1.35, -0.17, "drops over a tongue on the aprons:", size=8)
        label(ax, 1.35, -0.39, "locates both ways, can't be seen", size=8)
    label(ax, 1.35, 0.85, "floor", size=8)
    label(ax, -0.1, -0.8, "stand apron", size=8, ha="right", va="center")
    label(ax, -0.1, 0.62, "case rail", size=8, ha="right", va="center")
    ax.set_xlim(-1.3, 3.2); ax.set_ylim(-1.7, 1.5)
    head(ax, "Locating strips" if strips else "Hidden rabbet over a tongue", ok=not strips)


f, axs = fig(2, w=4.6, h=4.0, title="Locating a case on its stand (section)")
stand(axs[0], True); stand(axs[1], False)
save(f, "case-on-stand.png")


# ------------------------------------------------------------------ 7. laser plate
def plate(ax, good):
    t = 1 / 16
    frame = box(0, 0, 3, 2).difference(box(0.3, 0.3, 2.7, 1.7))
    bars = [box(x, 0.3, x + (0.12 if good else 0.12), 1.7) for x in (0.9, 2.0)]
    ring_c = Point(1.5, 1.0)
    ring = ring_c.buffer(0.45).difference(ring_c.buffer(0.45 - (0.12 if good else 0.035)))
    leaf = Point(1.5, 1.0).buffer(0.14)
    parts = [frame] + bars + [ring, leaf]
    if good:
        parts += [box(1.035, 0.97, 1.5 - 0.09, 1.07), box(1.5 + 0.09, 0.97, 1.965, 1.07),
                  box(1.02, 0.94, 1.05, 1.06), box(1.95, 0.94, 1.98, 1.06)]
        parts += [box(1.02 - 0.12, 0.94, 1.08, 1.06), box(1.92, 0.94, 2.0 + 0.12, 1.06)]
    sh = unary_union(parts)
    gs = sh.geoms if hasattr(sh, "geoms") else [sh]
    for g in gs:
        ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fc="none", ec=RED, lw=1.0))
        for h in g.interiors:
            ax.add_patch(MPoly(list(h.coords), closed=True, fc="none", ec=RED, lw=1.0))
    if not good:
        ax.add_patch(Circle((1.5, 1.0), 0.2, fc="none", ec=INK, lw=0.8, ls=(0, (2, 2))))
        label(ax, 0, -0.25, "ring 0.035 in wide on 1/16 sheet: burns away", size=8, color=RED)
        label(ax, 0, -0.4, "centre motif touches nothing: falls out", size=8, color=RED)
    else:
        label(ax, 0, -0.25, "every bar at least the sheet thickness", size=8)
        label(ax, 0, -0.4, "every motif tied into the bars", size=8)
    ax.set_xlim(-0.1, 3.1); ax.set_ylim(-0.55, 2.1)
    head(ax, "Thin and floating" if not good else "Tied in, full-width bars", ok=good)


f, axs = fig(2, w=4.4, h=3.4, title="Laser-cut plates: red outlines, no thin webs")
plate(axs[0], False); plate(axs[1], True)
save(f, "laser-plate.png")

#!/usr/bin/env python3
"""Full-size (1:1) part printouts and cut sheets, drawn as red outlines.

  python3 scripts/printouts.py MODEL.glb --units m --spec piece.cadcheck.json --cutlist build/cutlist.json --out build/

For one part of every lettered group in the cut list it draws four views at full size: the face (L x W),
the edge (L x T), the end (W x T, the profile of every through groove, rabbet and tenon) and a section at
mid-length (shows stopped grooves and the webs and necks between cuts: hold it up to the reviewer). Outlines are
red; visible edges inside the outline are thin red; the letter, name, quantity and sizes are red text set
straight on the page with no box behind them. Three files:

  fullsize_roll.pdf     one long page per roll width (default 36 in) for a plotter or print shop
  fullsize_tiled.pdf    the same layout tiled onto letter pages with overlap, crop marks, a page grid
                        (A1, A2 ...) and a 1 in check square on every page: tape them together
  fullsize_parts.svg    the whole layout as one SVG, 1 unit = 1 in, for a laser or CNC

--laser REGEX draws only the parts that match (sheet metal plates, a cardboard mockup) as single closed
red outlines in an SVG at 1:1, hairline stroke, ready for the cutter, and runs the sheet check on them
(see sheetcheck.py): no web thinner than the sheet, nothing floating.

Before printing at a shop: print the first tiled page and measure the check square.
"""
import argparse, json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import furnlib as F
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union


def project(m, c, R, view):
    """2D outline and visible sharp edges of mesh m seen along one axis of its frame.
    view: 'face' (look along T, x=L, y=W), 'edge' (along W, x=L, y=T), 'end' (along L, x=W, y=T)."""
    P = (m.vertices - c) @ R            # columns L, W, T
    ax = {"face": (0, 1, 2), "edge": (0, 2, 1), "end": (1, 2, 0)}[view]
    xy = P[:, [ax[0], ax[1]]]
    depth = P[:, ax[2]]
    tris = [Polygon(xy[f]) for f in m.faces]
    tris = [t for t in tris if t.is_valid and t.area > 1e-9]
    sil = unary_union(tris).buffer(0)
    # visible sharp edges: midpoints not hidden behind other faces (ray toward the viewer)
    lines = []
    try:
        adj = m.face_adjacency
        ang = m.face_adjacency_angles
        edges = m.face_adjacency_edges[ang > math.radians(20)]
        if len(edges):
            mids = (m.vertices[edges[:, 0]] + m.vertices[edges[:, 1]]) / 2
            vdir = R[:, ax[2]]
            ok = np.ones(len(edges), bool)
            for sgn in (1,):
                origins = mids + vdir * 1e-3
                hit = m.ray.intersects_any(origins, np.tile(vdir, (len(edges), 1)))
                ok &= ~hit
            for e, v in zip(edges, ok):
                if v:
                    a, b = xy[e[0]], xy[e[1]]
                    if np.linalg.norm(a - b) > 1e-3:
                        lines.append((tuple(a), tuple(b)))
    except Exception:
        pass
    return sil, lines


def mid_section(m, c, R, at=0.5):
    """Cross-section (W x T) through the part at a fraction of its length: shows stopped grooves,
    mortises and webs that an end view hides."""
    P = (m.vertices - c) @ R
    lo, hi = P[:, 0].min(), P[:, 0].max()
    x = lo + (hi - lo) * at
    sec = m.section(plane_origin=c + R[:, 0] * x, plane_normal=R[:, 0])
    if sec is None:
        return None
    polys = []
    for ent in sec.discrete:
        q = (ent - c) @ R
        if len(q) >= 3:
            polys.append(Polygon(q[:, [1, 2]]).buffer(0))
    shape = Polygon()
    for p in polys:
        shape = shape.symmetric_difference(p)
    return shape if not shape.is_empty else None


def part_views(m, grain, section=True):
    c, R, (T, W, L) = F.frame(m, grain)
    views = {}
    for v in ("face", "edge", "end"):
        sil, lines = project(m, c, R, v)
        minx, miny, maxx, maxy = sil.bounds
        views[v] = dict(sil=sil, lines=lines, off=(-minx, -miny), w=maxx - minx, h=maxy - miny)
    if section:
        sh = mid_section(m, c, R)
        if sh is not None:
            minx, miny, maxx, maxy = sh.bounds
            views["section"] = dict(sil=sh, lines=[], off=(-minx, -miny), w=maxx - minx, h=maxy - miny)
    return views, (T, W, L)


def layout(items, page_w, margin=1.0, gap=0.75, label_h=0.9):
    """Shelf-pack blocks (one per part: its three views stacked) left to right, rows downward.
    Returns placed items with x, y (inches from top-left) and the total length used."""
    x, y, row_h = margin, margin, 0
    placed = []
    for it in items:
        w, h = it["bw"], it["bh"] + label_h
        if x + w > page_w - margin and x > margin:
            x, y, row_h = margin, y + row_h + gap, 0
        placed.append(dict(it, x=x, y=y + label_h))
        x += w + gap
        row_h = max(row_h, h)
    return placed, y + row_h + margin


def block(views, gap=0.5):
    """Arrange face, edge and end views: face on top, edge under it, end to the right of the edge."""
    f, e, n = views["face"], views["edge"], views["end"]
    pos = {"face": (0, 0), "edge": (0, f["h"] + gap), "end": (max(f["w"], e["w"]) + gap, f["h"] + gap)}
    bw = max(f["w"], pos["end"][0] + n["w"])
    bh = f["h"] + gap + max(e["h"], n["h"])
    if "section" in views:
        sv = views["section"]
        pos["section"] = (pos["end"][0] + n["w"] + gap, f["h"] + gap)
        bw = max(bw, pos["section"][0] + sv["w"])
        bh = max(bh, f["h"] + gap + sv["h"])
    return pos, bw, bh


def draw_pdf(path, placed, page_w, page_h, T, title, tiles=None, tile=(8.5, 11.0), overlap=0.5):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("Serif", T["fonts"]["serif"]))
    pdfmetrics.registerFont(TTFont("Mono", T["fonts"]["mono"]))
    red = F.hex_rgb(T["red"]); ink = F.hex_rgb(T["ink"])
    I = 72.0

    def paint(cv, ox, oy, ph):
        """ox, oy: the sheet's top-left in layout inches; ph: page height in inches."""
        def P(x, y):
            return ((x - ox) * I, (ph - (y - oy)) * I)
        cv.setStrokeColorRGB(*red); cv.setFillColorRGB(*red)
        for it in placed:
            bx, by = it["x"], it["y"]
            cv.setFont("Serif", 14); cv.drawString(*P(bx, by - 0.45), f"{it['letter']}  {it['label'].upper()}")
            cv.setFont("Mono", 8)
            cv.drawString(*P(bx, by - 0.2), f"x{it['qty']}   {F.frac(it['T'])} x {F.frac(it['W'])} x {F.frac(it['L'])}")
            for v, (px, py) in it["pos"].items():
                vw = it["views"][v]
                x0, y0 = bx + px, by + py
                cv.setFont("Mono", 7); cv.drawString(*P(x0, y0 - 0.06), "SECTION AT MID-LENGTH" if v == "section" else v.upper())
                geoms = vw["sil"].geoms if isinstance(vw["sil"], MultiPolygon) else [vw["sil"]]
                for g in geoms:
                    for ring in [g.exterior] + list(g.interiors):
                        pts = [(x0 + vw["off"][0] + a, y0 + vw["h"] - (vw["off"][1] + b)) for a, b in ring.coords]
                        pth = cv.beginPath(); pth.moveTo(*P(*pts[0]))
                        for q in pts[1:]:
                            pth.lineTo(*P(*q))
                        pth.close(); cv.setLineWidth(0.9); cv.drawPath(pth, stroke=1, fill=0)
                cv.setLineWidth(0.35)
                for a, b in vw["lines"]:
                    pa = (x0 + vw["off"][0] + a[0], y0 + vw["h"] - (vw["off"][1] + a[1]))
                    pb = (x0 + vw["off"][0] + b[0], y0 + vw["h"] - (vw["off"][1] + b[1]))
                    cv.line(*P(*pa), *P(*pb))

    if tiles is None:
        cv = canvas.Canvas(path, pagesize=(page_w * I, page_h * I))
        cv.setTitle(title + " full size")
        paint(cv, 0, 0, page_h)
        cv.setFillColorRGB(*ink); cv.setFont("Mono", 9)
        cv.drawString(0.5 * I, 0.4 * I, f"{title}  ·  FULL SIZE 1:1  ·  check square = 1 in")
        cv.setStrokeColorRGB(*red); cv.rect(page_w * I - 1.5 * I, 0.3 * I, I, I)
        cv.save()
        return 1
    tw, th = tile
    m = 0.4                                   # printer margin
    sw, sh = tw - 2 * m - overlap, th - 2 * m - overlap
    cols, rows = math.ceil(page_w / sw), math.ceil(page_h / sh)
    cv = canvas.Canvas(path, pagesize=(tw * I, th * I))
    cv.setTitle(title + " full size, tiled")
    n = 0
    for r in range(rows):
        for ccol in range(cols):
            ox, oy = ccol * sw - m, r * sh - m
            # skip empty tiles
            if not any(it["x"] < ox + tw and it["x"] + it["bw"] > ox and it["y"] - 1 < oy + th and it["y"] + it["bh"] > oy for it in placed):
                continue
            paint(cv, ox, oy, th)
            cv.setStrokeColorRGB(*ink); cv.setLineWidth(0.3)
            for x in (m, tw - m):
                for y in (m, th - m):
                    cv.line((x - 0.15) * I, y * I, (x + 0.15) * I, y * I); cv.line(x * I, (y - 0.15) * I, x * I, (y + 0.15) * I)
            cv.setFillColorRGB(*ink); cv.setFont("Mono", 8)
            cv.drawString(m * I, (m - 0.25) * I, f"{title}  ·  {chr(65 + r)}{ccol + 1}  ·  row {r + 1} of {rows}, column {ccol + 1} of {cols}  ·  overlap {overlap} in  ·  1:1")
            cv.setStrokeColorRGB(*red); cv.rect((tw - m - 1.1) * I, (m + 0.1) * I, I, I)
            cv.showPage(); n += 1
    cv.save()
    return n


def draw_svg(path, placed, page_w, page_h, T, outlines_only=False):
    red = T["red"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w}in" height="{page_h}in" viewBox="0 0 {page_w} {page_h}">',
           f'<rect width="{page_w}" height="{page_h}" fill="#FFFFFF"/>']
    for it in placed:
        bx, by = it["x"], it["y"]
        if not outlines_only:
            out.append(f'<text x="{bx}" y="{by - 0.45}" font-family="Newsreader, Georgia, serif" font-size="0.2" fill="{red}">{it["letter"]}  {it["label"].upper()}</text>')
            out.append(f'<text x="{bx}" y="{by - 0.2}" font-family="IBM Plex Mono, monospace" font-size="0.11" fill="{red}">x{it["qty"]}  {F.frac(it["T"])} x {F.frac(it["W"])} x {F.frac(it["L"])}</text>')
        for v, (px, py) in it["pos"].items():
            vw = it["views"][v]
            x0, y0 = bx + px, by + py
            geoms = vw["sil"].geoms if isinstance(vw["sil"], MultiPolygon) else [vw["sil"]]
            d = []
            for g in geoms:
                for ring in [g.exterior] + list(g.interiors):
                    pts = [(x0 + vw["off"][0] + a, y0 + vw["h"] - (vw["off"][1] + b)) for a, b in ring.coords]
                    d.append("M" + " L".join(f"{p[0]:.4f},{p[1]:.4f}" for p in pts) + " Z")
            sw = "0.001" if outlines_only else "0.012"
            out.append(f'<path d="{" ".join(d)}" fill="none" stroke="{red}" stroke-width="{sw}"/>')
            if not outlines_only:
                for a, b in vw["lines"]:
                    pa = (x0 + vw["off"][0] + a[0], y0 + vw["h"] - (vw["off"][1] + a[1]))
                    pb = (x0 + vw["off"][0] + b[0], y0 + vw["h"] - (vw["off"][1] + b[1]))
                    out.append(f'<line x1="{pa[0]:.4f}" y1="{pa[1]:.4f}" x2="{pb[0]:.4f}" y2="{pb[1]:.4f}" stroke="{red}" stroke-width="0.005"/>')
    out.append("</svg>")
    open(path, "w").write("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--units", default="m", choices=["in", "mm", "m"])
    ap.add_argument("--up", default="auto", choices=["x", "y", "z", "auto"])
    ap.add_argument("--spec")
    ap.add_argument("--cutlist", help="cutlist.json from cutlist.py (keeps the same letters)")
    ap.add_argument("--only", help="REGEX of part labels or letters to print")
    ap.add_argument("--roll", type=float, default=36.0, help="roll width, in")
    ap.add_argument("--tile", default="8.5x11", help="tile page size for the tiled PDF, e.g. 8.5x11 or 11x17")
    ap.add_argument("--laser", help="REGEX of parts to send as laser cut sheets (face outline only)")
    ap.add_argument("--sheet-t", type=float, help="sheet thickness for the laser sheet check (default: the part's T)")
    ap.add_argument("--theme")
    ap.add_argument("--out", default="build")
    ap.add_argument("--title")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    T = F.theme(a.theme)
    parts, spec = F.load(a.model, a.units, a.up, a.spec)
    rows = json.load(open(a.cutlist))["parts"] if a.cutlist else F.parts_table(parts)
    title = a.title or os.path.splitext(os.path.basename(a.model))[0]

    if a.laser:
        import sheetcheck
        names = [n for n in sorted(parts) if re.search(a.laser, n)]
        items = []
        for n in names:
            m = parts[n]
            views, (t, w, l) = part_views(m, None, section=False)
            views = {"face": views["face"]}
            items.append(dict(letter="", label=n, qty=1, T=t, W=w, L=l, views=views, pos={"face": (0, 0)},
                              bw=views["face"]["w"], bh=views["face"]["h"]))
            for f in sheetcheck.check(views["face"]["sil"], a.sheet_t or t):
                print(f"  [{f['check']}] {n}: {f['detail']}")
        placed, length = layout(items, a.roll, label_h=0.2, gap=0.25)
        draw_svg(os.path.join(a.out, "laser_cut.svg"), placed, a.roll, length, T, outlines_only=True)
        print(f"{len(items)} sheet parts -> {a.out}/laser_cut.svg ({a.roll} x {length:.1f} in)")
        return

    items = []
    for r in rows:
        if r["role"] in ("hardware",) or not r.get("letter"):
            continue
        if a.only and not re.search(a.only, r["label"]) and not re.fullmatch(a.only, r["letter"]):
            continue
        n = r["names"][0]
        if n not in parts:
            continue
        role, grain = F.C.part_info(n, parts[n])
        views, _ = part_views(parts[n], grain)
        pos, bw, bh = block(views)
        items.append(dict(letter=r["letter"], label=r["label"], qty=r["qty"], T=r["T"], W=r["W"], L=r["L"],
                          views=views, pos=pos, bw=bw, bh=bh))
    placed, length = layout(items, a.roll)
    draw_pdf(os.path.join(a.out, "fullsize_roll.pdf"), placed, a.roll, length, T, title)
    tw, th = (float(x) for x in a.tile.split("x"))
    n = draw_pdf(os.path.join(a.out, "fullsize_tiled.pdf"), placed, a.roll, length, T, title, tiles=True, tile=(tw, th))
    draw_svg(os.path.join(a.out, "fullsize_parts.svg"), placed, a.roll, length, T)
    print(f"{len(items)} parts at full size: roll {a.roll} x {length:.1f} in, {n} tiled pages -> {a.out}/fullsize_*.pdf, .svg")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Laser / waterjet sheet check for flat cut parts (metal plates, grilles, tracery, mockup cardboard).

  python3 scripts/sheetcheck.py plate.svg --t 0.06           # an SVG of closed outlines, units = inches
  python3 scripts/sheetcheck.py MODEL.glb --units m --only BarPlate   # flat parts in a model

Rules it checks (both from real plates that had to be redrawn):
  thin_web   no bar, bridge, web or pointed tip narrower than the sheet thickness (default) or --min-web. Narrower
             bits burn away, warp or snap. Reported with where and how wide they are.
  floating   every motif must tie into the bars: a piece of the plate that isn't connected to the rest
             falls out when it's cut (a leaf, a ring, the centre of a letter O).
  tiny_hole  holes and slots narrower than the sheet thickness won't cut cleanly.
"""
import argparse, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union


def check(shape, t, min_web=None):
    """shape: shapely (Multi)Polygon of the plate in inches. Returns a list of flag dicts."""
    w = min_web or t
    flags = []
    geoms = list(shape.geoms) if isinstance(shape, MultiPolygon) else [shape]
    geoms = [g for g in geoms if g.area > 1e-6]
    if len(geoms) > 1:
        main = max(geoms, key=lambda g: g.area)
        for g in geoms:
            if g is not main:
                c = g.representative_point()
                flags.append(dict(check="floating", detail=f"a {g.area:.3f} in^2 piece at ({c.x:.2f}, {c.y:.2f}) isn't tied to the rest: it falls out"))
    for g in geoms:
        opened = g.buffer(-w / 2 * 0.98, join_style=2).buffer(w / 2 * 0.98, join_style=2)
        thin = g.difference(opened)
        thin_g = list(thin.geoms) if hasattr(thin, "geoms") else [thin]
        for p in thin_g:
            if p.is_empty or p.area < (w * w) * 0.15:
                continue
            c = p.representative_point()
            flags.append(dict(check="thin_web", detail=f"a bar, web or pointed tip narrower than {w:.3f} in near ({c.x:.2f}, {c.y:.2f}), "
                                                       f"{p.area:.4f} in^2 of it: widen it or end the tip round"))
        for hole in g.interiors:
            h = Polygon(hole)
            if h.buffer(-w / 2 * 0.98).is_empty and h.area > 0:
                c = h.representative_point()
                flags.append(dict(check="tiny_hole", detail=f"opening narrower than {w:.3f} in at ({c.x:.2f}, {c.y:.2f})"))
    return flags


def svg_shape(path):
    """Closed paths (M/L/H/V/Z, polylines, polygons, rects) of an SVG -> one shape, even-odd fill."""
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    rings = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "path":
            toks = re.findall(r"[MLHVZmlhvz]|-?[\d.]+(?:e-?\d+)?", el.get("d", ""))
            cur, ring, cmd, i = [0.0, 0.0], [], "M", 0
            while i < len(toks):
                if toks[i] in "MLHVZmlhvz":
                    cmd = toks[i]; i += 1
                    if cmd in "Zz":
                        if len(ring) > 2: rings.append(ring)
                        ring = []
                    continue
                if cmd in "Mm":
                    x, y = float(toks[i]), float(toks[i + 1]); i += 2
                    if ring and len(ring) > 2: rings.append(ring)
                    cur = [cur[0] + x, cur[1] + y] if cmd == "m" else [x, y]; ring = [tuple(cur)]
                    cmd = "l" if cmd == "m" else "L"
                elif cmd in "Ll":
                    x, y = float(toks[i]), float(toks[i + 1]); i += 2
                    cur = [cur[0] + x, cur[1] + y] if cmd == "l" else [x, y]; ring.append(tuple(cur))
                elif cmd in "Hh":
                    x = float(toks[i]); i += 1; cur = [cur[0] + x if cmd == "h" else x, cur[1]]; ring.append(tuple(cur))
                elif cmd in "Vv":
                    y = float(toks[i]); i += 1; cur = [cur[0], cur[1] + y if cmd == "v" else y]; ring.append(tuple(cur))
            if len(ring) > 2: rings.append(ring)
        elif tag in ("polygon", "polyline"):
            v = [float(x) for x in re.findall(r"-?[\d.]+", el.get("points", ""))]
            rings.append(list(zip(v[0::2], v[1::2])))
        elif tag == "rect":
            x, y, w, h = (float(el.get(k, 0)) for k in ("x", "y", "width", "height"))
            rings.append([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    shape = Polygon()
    for r in rings:
        p = Polygon(r).buffer(0)
        shape = shape.symmetric_difference(p)
    return shape


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--t", type=float, help="sheet thickness, in (from the part when reading a model)")
    ap.add_argument("--min-web", type=float, help="narrowest bar allowed (default: the sheet thickness)")
    ap.add_argument("--scale", type=float, default=1.0, help="SVG units to inches (e.g. 1/25.4 for mm)")
    ap.add_argument("--units", default="m", choices=["in", "mm", "m"])
    ap.add_argument("--up", default="auto")
    ap.add_argument("--only", default="(plate|sheet|grille|tracery|laser)")
    a = ap.parse_args()
    n_flags = 0
    if a.file.lower().endswith(".svg"):
        from shapely import affinity
        s = affinity.scale(svg_shape(a.file), a.scale, a.scale, origin=(0, 0))
        if not a.t:
            sys.exit("--t (sheet thickness) is needed for an SVG")
        for f in check(s, a.t, a.min_web):
            print(f"  [{f['check']}] {f['detail']}"); n_flags += 1
    else:
        import furnlib as F, printouts as P
        parts, _ = F.load(a.file, a.units, a.up)
        for n in sorted(parts):
            if not re.search(a.only, n, re.I):
                continue
            views, (t, w, l) = P.part_views(parts[n], None)
            for f in check(views["face"]["sil"], a.t or t, a.min_web):
                print(f"  [{f['check']}] {n}: {f['detail']}"); n_flags += 1
    print(f"{n_flags} flag(s)")
    sys.exit(1 if n_flags else 0)


if __name__ == "__main__":
    main()

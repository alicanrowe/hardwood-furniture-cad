#!/usr/bin/env python3
"""hinge.py: look up a hinge and work out its mortises for a door.

  python hinge.py --list [TYPE|MAKER]            list hinges in the library
  python hinge.py MODEL --door 3/4 --gap 1/16     mortise sizes for that hinge on that door
  python hinge.py MODEL --json                    the raw record

Inches unless the record says mm. Mortise math (fit to the real hinge before cutting):
  butt / stop / lift-off   depth per leaf = (barrel - gap) / 2  (Whitechapel's rule; no barrel known: leaf thickness)
                           width = open width / 2 - 1/32 so the pin centre sits just proud of the case,
                           or open width / 2 - barrel / 2 to show the whole barrel (loose pin, ball tip)
                           length = hinge length; a door over 48 in wants a third hinge
  knife (straight/offset)  mortise in the door top/bottom and the case, depth = leaf thickness, width = leaf width,
                           door at least leaf width + 1/8 thick (Brusso centre pivots: + 1/4)
  concealed barrel (SOSS, Sugatsune)  door at least the minimum thickness; mortise depth from the record or template
  euro cup (Blum)          35 mm cup, at least 13 mm deep, 3-7 mm from the door edge; overlay = X + B - H
"""
import argparse, json, os, sys
from fractions import Fraction

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "hinges.json")


def num(s):
    if s is None:
        return None
    try:
        return float(sum(Fraction(p) for p in str(s).split()))
    except ValueError:
        sys.exit(f"can't read {s!r} as a number (use 0.75 or 3/4 or '1 1/2')")


def frac(x, d=64):
    f = Fraction(round(x * d), d)
    w, r = divmod(f.numerator, f.denominator)
    return f'{x:.3f} in (~{(str(w) + " ") if w else ""}{Fraction(r, f.denominator) if r else ""}")'.replace(' ")', '")')


def load():
    return json.load(open(LIB))["hinges"]


def find(q, H):
    q = q.lower().replace(" ", "")
    hits = [h for h in H if q in h["id"] or q in h["model"].lower().replace(" ", "")]
    exact = [h for h in hits if h["model"].lower().replace(" ", "") == q or h["id"].endswith(q)]
    return exact or hits


def plan(h, door, gap):
    t, out, warn = h["type"], [], []
    conf = h["source"]["confidence"]
    if not conf.startswith(("maker", "retailer")):
        warn.append("dimensions come from a secondary source: check them on the hinge in hand")
    if h.get("units") == "mm":
        out.append(json.dumps({k: v for k, v in h.items() if k not in ("source",)}, ensure_ascii=False))
        if t == "euro_cup":
            out.append(f"bore a {h['cup_dia']} mm cup, {h['cup_depth_min']} mm deep, {h['boring_distance_range'][0]}-"
                       f"{h['boring_distance_range'][1]} mm from the door edge; door at least about 16 mm thick")
        return out, warn
    if t in ("butt", "stop", "lift_off"):
        L, W = h.get("length"), h.get("open_width")
        b, lt = h.get("barrel_dia") or h.get("closed_thickness"), h.get("leaf_thickness")
        if b:
            depth = (b - gap) / 2
        elif lt:
            depth = lt - gap / 2 if lt > gap / 2 else lt
            warn.append("no barrel diameter on file: depth assumes the barrel is about two leaves thick")
        else:
            depth = None
            warn.append("no leaf or barrel size on file: take the depth from the hinge")
        out.append(f"mortise length {frac(L)}" if L else "length: measure")
        if W:
            out.append(f"mortise width (pin just proud) {frac(W / 2 - 1 / 32)}")
            if b:
                out.append(f"mortise width (whole barrel showing) {frac(W / 2 - b / 2)}")
        if depth is not None:
            out.append(f"depth per leaf, door and case alike {frac(depth)}  (for a {gap:g} in gap)")
        if door and W and W / 2 - 1 / 32 > door:
            warn.append(f"the mortise ({W / 2 - 1 / 32:.3f} in) is wider than the {door:g} in door edge: pick a narrower hinge")
        if t == "stop":
            out.append(f"lid stops at {h.get('opens_to_deg', 95)} degrees; mortise fully so the stop faces bear")
    elif t == "knife_intermediate":
        out.append(f"mortised into the hinge edge of the door and the case side, midway up; {frac(h['length'])} long, "
                   f"{frac(h['open_width'])} open; must sit on the same pivot axis as the top and bottom knife hinges")
        out.append("handed: order left or right to suit the door")
    elif t.startswith("knife"):
        w, L, lt = h.get("leaf_width") or h.get("offset"), h.get("length"), h.get("leaf_thickness")
        out.append(f"mortise in door top and bottom and in the case: {frac(L) if L else '?'} long x {frac(w) if w else '?'} wide"
                   f" x {frac(lt) if lt else 'leaf thickness'} deep")
        need = h.get("min_door_thickness") or (w + 0.125 if w else None)
        if need and door:
            (warn if door < need - 1e-6 else out).append(f"door {door:g} in vs at least {need:.3f} in needed")
        if t == "knife_double_offset":
            out.append("pivot sits outside door and case: door folds back to about 270 degrees")
        out.append("gap at top and bottom = the pivot washer; plane the door to that, not to the leaf")
    elif t == "concealed_barrel":
        need = h.get("min_door_thickness")
        if need and door:
            (warn if door < need - 1e-6 else out).append(f"door {door:g} in vs at least {need:.3f} in")
        for k in ("outline_mortise_depth", "mortise_depth", "body_width", "length"):
            if h.get(k):
                out.append(f"{k.replace('_', ' ')} {frac(h[k])}")
        out.append("bore with the maker's template; the edge must be dead square")
    elif t == "quadrant":
        out.append(f"stay mortise {frac(h['stay_mortise_depth'])} deep; wall at least {frac(h['min_wall'])}")
    else:
        out.append(json.dumps({k: v for k, v in h.items() if k != "source"}, ensure_ascii=False))
    return out, warn


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", nargs="?")
    ap.add_argument("--list", nargs="?", const="", metavar="TYPE|MAKER")
    ap.add_argument("--door", help="door or lid thickness, in")
    ap.add_argument("--gap", default="1/16", help="door gap at the hinge side, in (default 1/16)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    H = load()
    if a.list is not None:
        q = a.list.lower()
        for h in H:
            if q in h["type"] or q in h["maker"].lower() or not q:
                dims = " x ".join(f"{h[k]:g}" for k in ("length", "open_width", "leaf_width", "leaf_thickness") if isinstance(h.get(k), (int, float)))
                print(f"{h['maker']:<16} {h['model']:<38} {h['type']:<20} {dims}")
        return
    if not a.model:
        ap.print_help()
        return
    hits = find(a.model, H)
    if not hits:
        sys.exit(f"no hinge matches {a.model!r}; try --list")
    if len(hits) > 1:
        print("several match, using the first: " + ", ".join(h["model"] for h in hits))
    h = hits[0]
    if a.json:
        print(json.dumps(h, indent=1, ensure_ascii=False))
        return
    out, warn = plan(h, num(a.door), num(a.gap))
    print(f"{h['maker']} {h['model']} ({h['type'].replace('_', ' ')}), source: {h['source']['name']}")
    for o in out:
        print("  " + o)
    for w in warn:
        print("  CHECK: " + w)


if __name__ == "__main__":
    main()

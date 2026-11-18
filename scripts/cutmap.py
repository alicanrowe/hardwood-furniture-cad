#!/usr/bin/env python3
"""Board-by-board cut map: which logged board each part comes out of, and the cuts in shop order.

  python3 scripts/cutmap.py build/cutlist.json boards.json --out build/        # cutmap.json + cutmap.md
  python3 scripts/cutmap.py build/cutlist.json boards.json --board C           # one board, caveman line
  python3 scripts/cutmap.py build/cutlist.json boards.json --only 'post|rail'  # today's parts only

boards.json is the board log, measured off the user's own boards (inches):
  {"boards": [{"id": "A", "L": 48, "W": 8.5, "T": 1.25, "species": "walnut", "note": "knot 10 in from the end"}],
   "only": "carcass|post|rail"}            # optional: what is being built today (regex on part labels)

Rules it follows (the shop's, from references/drawings-and-printouts.md):
  - Blanks are finished + 1 in long and + 1/4 in wide. Anything that still goes over the jointer or planer stays
    at least 12 in long: short parts ride end to end in one strip and are cross-cut only after milling.
  - A board at least twice the part thickness plus 1/8 in (and a kerf) is resawn and both slices are used.
  - Chop positions are measured from the board's labelled end; rips from the jointed edge.
  - Rips in each section are listed widest first, so the fence only ever moves one way (fence order).
Every part in the cut list must land on a board exactly once. Parts that don't fit are listed as NEED WOOD and
the exit code is 1: say so to the user, never invent a board.

Caveman line, one per board, in cutting order (the default answer on the shop floor):
  A: chop at 23 1/2, 44. Rip (fence) 3 11/16, 2. Resaw 9/16. Then cross-cut: 4 posts (11), 2 top rails (10 7/32).
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from furnlib import frac

LEN_ALLOW, WID_ALLOW, KERF, MIN_BLANK, RESAW_ALLOW, PLANE_ALLOW = 1.0, 0.25, 0.125, 12.0, 0.125, 1 / 16


def instances(cl, only=None):
    out = []
    for r in cl["parts"]:
        if r["role"] not in ("wood", "floating", "insert"):
            continue
        if only and not re.search(only, r["label"], re.I):
            continue
        for k in range(int(r["qty"])):
            out.append(dict(letter=r["letter"], label=r["label"], T=float(r["T"]), W=float(r["W"]), L=float(r["L"]),
                            species=(r.get("species") or "").lower()))
    return out


def strips(parts):
    """Same thickness and width -> one strip; parts end to end; a strip is never shorter than MIN_BLANK."""
    groups = {}
    for p in sorted(parts, key=lambda p: -p["L"]):
        groups.setdefault((p["species"], round(p["T"] * 32), round(p["W"] * 32)), []).append(p)
    out = []
    for (sp, _, _), ps in groups.items():
        cur = []
        for p in ps:
            need = p["L"] + LEN_ALLOW + (KERF if cur else 0)
            if cur and sum(q["L"] + LEN_ALLOW for q in cur) + need > 2 * MIN_BLANK and sum(q["L"] + LEN_ALLOW for q in cur) >= MIN_BLANK:
                out.append(cur); cur = []
            cur.append(p)
        if cur: out.append(cur)
    res = []
    for s in out:
        L = sum(p["L"] + LEN_ALLOW for p in s) + KERF * (len(s) - 1)
        res.append(dict(parts=s, species=s[0]["species"], T=s[0]["T"], rip=s[0]["W"] + WID_ALLOW, L=max(L, MIN_BLANK)))
    return sorted(res, key=lambda s: (-s["T"], -s["L"], -s["rip"]))   # thickest first: they fit the fewest boards


def place(strs, boards):
    """Shelf packing: each board is chopped into sections along its length; strips are ripped side by side in a
    section. A board thick enough to resaw gets two layers per section."""
    for b in boards:
        b["sections"] = []; b["used_L"] = 0.0
    left = []
    for s in strs:
        ok = False
        for b in boards:
            if b.get("species") and s["species"] and b["species"].lower() not in s["species"] and s["species"] not in b["species"].lower():
                continue
            if s["T"] + PLANE_ALLOW > b["T"] + 1e-6:
                continue
            layers = 2 if b["T"] >= 2 * (s["T"] + RESAW_ALLOW) + KERF else 1
            for sec in b["sections"]:
                if sec["T"] == s["T"] and sec["L"] >= s["L"] - 1e-6 and (sec["used_W"] + s["rip"] + KERF <= b["W"] + 1e-6 or
                                                                         (sec["layers"] == 2 and sec["slice2"] is None)):
                    if sec["used_W"] + s["rip"] + KERF <= b["W"] + 1e-6:
                        sec["rips"].append(s); sec["used_W"] += s["rip"] + KERF
                    else:
                        sec["slice2"] = s
                    ok = True; break
            if ok: break
            if b["L"] - b["used_L"] >= s["L"] - 1e-6 and s["rip"] <= b["W"] + 1e-6:
                b["sections"].append(dict(L=s["L"], T=s["T"], layers=layers, rips=[s], used_W=s["rip"] + KERF, slice2=None))
                b["used_L"] += s["L"] + KERF
                ok = True; break
        if not ok: left.append(s)
    return left


def names(parts):
    by = {}
    for p in parts:
        k = (p["letter"], p["label"], p["L"]); by[k] = by.get(k, 0) + 1
    return ", ".join(f"{n} {lab} ({frac(L)})" + (f" [{let}]" if let else "") for (let, lab, L), n in by.items())


def board_line(b):
    if not b["sections"]:
        return f"{b['id']}: not needed today."
    chops = []; pos = 0.0
    for sec in b["sections"][:-1]:
        pos += sec["L"]; chops.append(frac(pos)); pos += KERF
    bits = [f"{b['id']}: " + (f"chop at {', '.join(chops)}." if chops else "no chop.")]
    for i, sec in enumerate(b["sections"], 1):
        rips = sorted(sec["rips"], key=lambda s: -s["rip"])
        tag = f" Piece {i}:" if len(b["sections"]) > 1 else ""
        r = f"{tag} Rip (fence) {', '.join(frac(s['rip']) for s in rips)}." if len(rips) > 1 or rips[0]["rip"] + 0.5 < b["W"] else f"{tag} No rip."
        if sec["layers"] == 2 and sec["slice2"] is not None:
            r += f" Resaw, slices {frac(sec['T'] + RESAW_ALLOW)}; second slice rip {frac(sec['slice2']['rip'])}."
        parts = [p for s in rips for p in s["parts"]] + (sec["slice2"]["parts"] if sec["slice2"] else [])
        long_ = len(parts) > len(rips) + (1 if sec["slice2"] else 0)
        r += (" Mill, then cross-cut: " if long_ else " Parts: ") + names(parts) + "."
        bits.append(r)
    return "".join(bits)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlist"); ap.add_argument("boards")
    ap.add_argument("--only", help="regex on part labels: only what is being built today")
    ap.add_argument("--board", help="print one board's line (a shop-floor answer)")
    ap.add_argument("--out")
    a = ap.parse_args()
    cl = json.load(open(a.cutlist)); bl = json.load(open(a.boards))
    boards = [dict(b) for b in bl["boards"]]
    only = a.only or bl.get("only")
    parts = instances(cl, only)
    left = place(strips(parts), boards)
    lines = [board_line(b) for b in boards]
    placed = sum(len(s["parts"]) for b in boards for sec in b["sections"] for s in sec["rips"] + ([sec["slice2"]] if sec["slice2"] else []))
    need = [p for s in left for p in s["parts"]]
    assert placed + len(need) == len(parts), "cut map lost a part"
    head = f"Cut map for {cl['meta'].get('title', '')} from {cl['meta'].get('model', '')} #{cl['meta'].get('sha256', '')}" + (f", today: {only}" if only else "")
    if a.board:
        for b, ln in zip(boards, lines):
            if b["id"].lower() == a.board.lower(): print(ln)
    else:
        print(head); print("\n".join(lines))
    if need:
        print("NEED WOOD: " + names(need) + ". No logged board fits these; ask for another board, don't guess one.")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(dict(meta=dict(cl["meta"], only=only), lines=lines, need=[dict(letter=p["letter"], label=p["label"], L=p["L"]) for p in need],
                       boards=[dict(id=b["id"], L=b["L"], W=b["W"], T=b["T"]) for b in boards]),
                  open(os.path.join(a.out, "cutmap.json"), "w"), indent=1)
        open(os.path.join(a.out, "cutmap.md"), "w").write(head + "\n\n" + "\n".join("- " + l for l in lines) + ("\n\nNEED WOOD: " + names(need) if need else "") + "\n")
    sys.exit(1 if need else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Cut list and milling plan from a furniture GLB/STL (one mesh node per part).

  python3 scripts/cutlist.py MODEL.glb --units m --spec piece.cadcheck.json --out build/

Writes to --out:
  cutlist.json   every group of identical parts, lettered A, B, C ... (the build book and printouts read it)
  cutlist.csv    letter, part, qty, T, W, L (finished, inches), material, species, members
  cutlist.md     the same as a table, plus the milling plan and a hardware list
The milling plan groups wood parts by species and finished thickness (one planer setting each), picks the
rough stock (4/4, 5/4, 6/4, 8/4 ... or a glue-up when nothing is thick enough), then rips strips by width
and lists the cross-cuts on each strip, longest first, with a length allowance and a kerf. Board feet are
rough stock, with a waste factor.

Sizes are the part's oriented bounding box: T is the thinnest side, L runs with the grain (from the spec's
grain, else the longest side). A tenon counts in L, so L is the length to cut, shoulder to shoulder plus
tenons. Curved or angled parts get their blank size; the full-size printouts give the shape.
"""
import argparse, csv, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import furnlib as F

ROUGH = [(13 / 16, "4/4"), (1 + 1 / 16, "5/4"), (1 + 5 / 16, "6/4"), (1 + 3 / 4, "8/4"), (2 + 1 / 4, "10/4"),
         (2 + 3 / 4, "12/4"), (3 + 3 / 4, "16/4")]


def rough_stock(t):
    for lim, name in ROUGH:
        if t <= lim + 1e-6:
            return name, int(name.split("/")[0]) / 4
    layers = math.ceil(t / 1.75)
    return f"{layers} layers of 8/4, glued face to face", layers * 2.0


def milling_plan(rows, len_allow=1.0, width_allow=0.25, kerf=0.125, max_strip=96.0, waste=1.3):
    """Batches (species + thickness) -> strips (width) -> cross-cuts. Floating parts (panels) are milled too."""
    batches = {}
    for r in rows:
        if r["role"] not in ("wood", "floating", "insert"):
            continue
        key = (r["species"] or "wood", round(r["T"] * 64))
        batches.setdefault(key, []).append(r)
    out = []
    for (sp, _), rs in sorted(batches.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
        T = rs[0]["T"]
        stock, rough_t = rough_stock(T)
        widths = {}
        for r in rs:
            widths.setdefault(round(r["W"] * 64), []).append(r)
        strips = []
        bf = 0.0
        for _, wr in sorted(widths.items(), key=lambda kv: -kv[0]):
            W = wr[0]["W"]
            cuts = []
            for r in sorted(wr, key=lambda r: -r["L"]):
                cuts += [(r["letter"], r["label"], r["L"])] * r["qty"]
            # split into strips no longer than max_strip
            cur, cur_len = [], 0.0
            for c in cuts:
                need = c[2] + len_allow + kerf
                if cur and cur_len + need > max_strip:
                    strips.append(dict(W=W, rip=W + width_allow, cuts=cur, length=cur_len))
                    cur, cur_len = [], 0.0
                cur.append(c)
                cur_len += need
            if cur:
                strips.append(dict(W=W, rip=W + width_allow, cuts=cur, length=cur_len))
        for s in strips:
            bf += rough_t * s["rip"] * s["length"] / 144
        out.append(dict(species=sp, T=T, stock=stock, strips=strips, board_feet=bf, board_feet_buy=bf * waste))
    return out


def sheet_goods(rows):
    out = []
    for r in rows:
        if r["role"] == "ply":
            out.append(dict(letter=r["letter"], label=r["label"], qty=r["qty"], T=r["T"], W=r["W"], L=r["L"],
                            material=r["material"], area=r["qty"] * r["W"] * r["L"] / 144))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--units", default="m", choices=["in", "mm", "m"])
    ap.add_argument("--up", default="auto", choices=["x", "y", "z", "auto"])
    ap.add_argument("--spec")
    ap.add_argument("--out", default="build")
    ap.add_argument("--title")
    ap.add_argument("--len-allow", type=float, default=1.0, help="added to each length before cross-cutting (in)")
    ap.add_argument("--width-allow", type=float, default=0.25, help="added to each strip width when ripping (in)")
    ap.add_argument("--kerf", type=float, default=0.125)
    ap.add_argument("--waste", type=float, default=1.3, help="board-feet multiplier for defects and yield")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    parts, spec = F.load(a.model, a.units, a.up, a.spec)
    rows = F.parts_table(parts)
    plan = milling_plan(rows, a.len_allow, a.width_allow, a.kerf, waste=a.waste)
    sheets = sheet_goods(rows)
    title = a.title or os.path.splitext(os.path.basename(a.model))[0]
    meta = dict(title=title, model=os.path.basename(a.model), sha256=F.sha_prefix(a.model),
                units="in", allowances=dict(length=a.len_allow, width=a.width_allow, kerf=a.kerf, waste=a.waste))
    json.dump(dict(meta=meta, parts=rows, milling=plan, sheet_goods=sheets), open(os.path.join(a.out, "cutlist.json"), "w"), indent=1)

    with open(os.path.join(a.out, "cutlist.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["letter", "part", "qty", "T", "W", "L", "T_in", "W_in", "L_in", "role", "material", "species", "cut", "members"])
        for r in rows:
            w.writerow([r["letter"], r["label"], r["qty"], F.frac(r["T"]), F.frac(r["W"]), F.frac(r["L"]),
                        f"{r['T']:.4f}", f"{r['W']:.4f}", f"{r['L']:.4f}", r["role"], r["material"], r["species"], r["cut"],
                        " ".join(r["names"])])

    L = [f"# {title}: cut list", "", f"Model `{meta['model']}`, sha256 `{meta['sha256']}`. Finished sizes in inches, T x W x L, L with the grain.", "",
         "| | Part | Qty | T | W | L | Material | Role |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["role"] == "hardware":
            continue
        mat = r["material"] or " ".join(x for x in (r["species"], r["cut"]) if x) or "wood"
        L.append(f"| {r['letter']} | {r['label']} | {r['qty']} | {F.frac(r['T'])} | {F.frac(r['W'])} | {F.frac(r['L'])} | {mat} | {r['role']} |")
    L += ["", "## Milling plan", "",
          f"One batch per species and finished thickness: plane the whole batch at one setting so mating parts match. "
          f"Rip each strip {F.frac(a.width_allow)} wide and joint and plane it while it is still long (keep anything going over the jointer or planer at least 12 in). "
          f"Only then cross-cut, longest first, with {F.frac(a.len_allow)} extra on each length.", ""]
    tot = 0
    for i, b in enumerate(plan, 1):
        L.append(f"### Batch {i}: {b['species']}, {F.frac(b['T'])} thick from {b['stock']}")
        L.append(f"About {b['board_feet']:.1f} bd ft in the strips; buy {b['board_feet_buy']:.1f}.")
        L.append("")
        for s in b["strips"]:
            cuts = ", ".join(f"{c[0]} {c[1]} {F.frac(c[2])}" for c in s["cuts"])
            L.append(f"- Strip {F.frac(s['W'])} finished (rip {F.frac(s['rip'])}), about {math.ceil(s['length'])} in long: {cuts}")
        L.append("")
        tot += b["board_feet_buy"]
    L.append(f"**Total to buy: about {tot:.0f} bd ft of rough lumber.**")
    if sheets:
        L += ["", "## Sheet goods", ""] + [f"- {s['letter']} {s['label']} x{s['qty']}: {F.frac(s['T'])} {s['material']}, {F.frac(s['W'])} x {F.frac(s['L'])}" for s in sheets]
    hw = [r for r in rows if r["role"] == "hardware"]
    if hw:
        L += ["", "## Hardware (from the model)", ""] + [f"- {r['label']} x{r['qty']}" for r in hw]
        L += ["", "Check how each item is sold before ordering (hinges such as Brusso's come by the pair: 4 hinges = 2 pairs)."]
    open(os.path.join(a.out, "cutlist.md"), "w").write("\n".join(L) + "\n")
    print(f"{len(rows)} groups, {sum(r['qty'] for r in rows)} parts -> {a.out}/cutlist.json, .csv, .md")


if __name__ == "__main__":
    main()

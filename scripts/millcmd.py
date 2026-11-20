#!/usr/bin/env python3
"""Shop-floor milling commands: one threshold line per part group, plus a fit check of the
strips the user actually has.

usage:
  python3 millcmd.py cutlist.json [--strips strips.json] [--names REGEX] [--kerf 0.125]

cutlist.json: {"rows": [{name, quantity, length_in, width_in, thickness_in}, ...]} (cutlist.py output)
strips.json:  [{"label": "23.5(D)", "length": 23.5, "width": 1.15625, "thickness": 1.1875}, ...]
              (what is pencilled on the wood; thickness optional)

Output, in shop order:
  1. THICKNESS: "Anything thicker than T, plane to T" per thickness, with what to keep OUT of that setting.
  2. WIDTH: per width bucket, which strips (by marked width) go to that part, "anything wider than W, rip to W".
  3. CROSSCUT: lengths and counts per part, and how many fit per strip.
  4. FIT CHECK: every strip that is too short for the cuts it is meant for, and every part with no strip
     wide/long enough (NEED WOOD).
Fractions are in 32nds reduced, never mixed denominators with decimals; odd 32nds get the decimal beside them.
"""
import sys, json, math, re, argparse
from collections import defaultdict


def frac(x, den=32):
    n = round(x * den); w, r = divmod(n, den)
    if not r: return f'{w}'
    g = math.gcd(r, den); s = (f'{w} ' if w else '') + f'{r // g}/{den // g}'
    if den // g == 32: s += f' ({x:.2f})'
    return s


def label(name):
    s = re.sub(r'\d+$', '', name)
    s = re.sub(r'_(L|R)_', '_', s)
    return s.replace('_', ' ').strip()


def groups(rows, rx=None):
    g = defaultdict(lambda: {'qty': 0})
    for r in rows:
        if rx and not re.search(rx, r['name']): continue
        T, W, L = (round(r[k] * 32) / 32 for k in ('thickness_in', 'width_in', 'length_in'))
        key = (T, W, L, label(r['name']))
        g[key]['qty'] += r.get('quantity', 1)
    return g


def plan(rows, strips=None, rx=None, kerf=0.125):
    g = groups(rows, rx)
    out = []
    byT = defaultdict(list)
    for (T, W, L, n), v in g.items(): byT[T].append((W, L, n, v['qty']))
    out.append('1. THICKNESS (plane all strips first, while they are long)')
    for T in sorted(byT):
        names = sorted({n for _, _, n, _ in byT[T]})
        out.append(f'   Anything thicker than {frac(T)}, plane to {frac(T)}: {", ".join(names)}.')
    out.append('   Keep stock for any other thickness out of each setting.')
    out.append('2. WIDTH (rip from the jointed edge, then plane the sawn edge)')
    widths = sorted({(T, W) for (T, W, L, n) in g}, key=lambda t: (t[0], -t[1]))
    for T, W in widths:
        names = sorted({n for (t, w, L, n) in g if t == T and w == W})
        out.append(f'   {frac(T)} thick: anything wider than {frac(W)}, rip to {frac(W)} -> {", ".join(names)}.')
    out.append('3. CROSSCUT LAST (square one end, stop block for repeats)')
    for (T, W, L, n), v in sorted(g.items(), key=lambda kv: (-kv[0][1], -kv[0][2])):
        per = lambda s: int((s + kerf) // (L + kerf))
        out.append(f'   {n} ({frac(T)} x {frac(W)}): {v["qty"]} at {frac(L)}.'
                   f' Two per strip needs {frac(2 * L + kerf)}+; three needs {frac(3 * L + 2 * kerf)}+.')
    if strips:
        out.append('4. FIT CHECK (strips as marked)')
        need = []
        for (T, W, L, n), v in g.items(): need += [(W, L, n, T)] * v['qty']
        need.sort(key=lambda p: (-p[0], -p[1]))
        free = [dict(s, left=s['length'], used=[]) for s in strips]
        for W, L, n, T in need:
            ok = [s for s in free if s['width'] >= W and s.get('thickness', T) >= T and s['left'] >= L]
            # narrowest strip that still fits, then the one with least length left over
            ok.sort(key=lambda s: (s['width'], s['left'] - L))
            if not ok:
                out.append(f'   NEED WOOD: {n} {frac(T)} x {frac(W)} x {frac(L)}: no strip that wide and long is left.')
                continue
            s = ok[0]; s['used'].append(f'{n} {frac(L)}'); s['left'] -= L + kerf
        for s in free:
            if s['used']:
                out.append(f'   {s["label"]} ({frac(s["width"])} wide, {frac(s["length"])} long): {", ".join(s["used"])}; {frac(max(s["left"], 0))} left.')
            else:
                out.append(f'   {s["label"]}: spare.')
    return '\n'.join(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cutlist'); ap.add_argument('--strips'); ap.add_argument('--names'); ap.add_argument('--kerf', type=float, default=0.125)
    a = ap.parse_args()
    rows = json.load(open(a.cutlist))['rows']
    strips = json.load(open(a.strips)) if a.strips else None
    print(plan(rows, strips, a.names, a.kerf))

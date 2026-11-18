"""Cut map: every part lands once, nothing is guessed, fence order runs one way, and milling blanks stay >= 12 in.
    python3 scripts/tests/test_cutmap.py"""
import json, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); CM = os.path.join(HERE, "..", "cutmap.py")


def frac2f(s):
    s = s.strip(); w = 0.0
    for t in s.split():
        if "/" in t: a, b = t.split("/"); w += int(a) / int(b)
        else: w += float(t)
    return w


def main():
    d = tempfile.mkdtemp()
    P = [("A", "post", 4, 1.25, 1.25, 11), ("B", "top rail", 2, 0.75, 1.5, 10.21875), ("C", "side panel", 8, 0.5, 3.5, 19.25),
         ("D", "apron", 4, 0.875, 3, 22), ("E", "drawer bottom", 1, 0.375, 10, 14)]
    parts = [dict(letter=l, label=n, qty=q, T=t, W=w, L=L, role="wood", species="walnut") for l, n, q, t, w, L in P]
    json.dump(dict(meta=dict(title="t", model="m.glb", sha256="x"), parts=parts), open(os.path.join(d, "cl.json"), "w"))
    B = [dict(id="A", L=20.25, W=8.5625, T=1.25, species="walnut"), dict(id="B", L=48, W=7, T=1.0, species="walnut"),
         dict(id="C", L=50, W=7.5, T=1.75, species="walnut")]
    json.dump(dict(boards=B), open(os.path.join(d, "b.json"), "w"))
    p = subprocess.run([sys.executable, CM, os.path.join(d, "cl.json"), os.path.join(d, "b.json"), "--out", d], capture_output=True, text=True)
    out = p.stdout; bad = 0
    def ok(name, cond):
        nonlocal bad; print("pass" if cond else "FAIL", name); bad += not cond
    ok("short of wood -> exit 1 and NEED WOOD", p.returncode == 1 and "NEED WOOD" in out)
    cm = json.load(open(os.path.join(d, "cutmap.json")))
    n = {}
    for ln in cm["lines"] + ["NEED WOOD: " + ", ".join(f"1 {x['label']} ({x['L']}) [{x['letter']}]" for x in cm["need"])]:
        for k, lab, let in re.findall(r"(\d+) ([a-z ]+) \([^)]*\) \[([A-Z])\]", ln):
            n[let] = n.get(let, 0) + int(k)
    ok("every part exactly once", all(n.get(l, 0) == q for l, _, q, *_ in P))
    fence = all(all(a >= b for a, b in zip(v, v[1:])) for ln in cm["lines"]
                for v in [[frac2f(x) for x in m.split(",")] for m in re.findall(r"Rip \(fence\) ([^.]+)\.", ln)])
    ok("fence order widest first", fence)
    ok("posts (1 1/4 thick) only on the 1 3/4 board", all("post" not in ln for ln in cm["lines"] if not ln.startswith("C:")))
    chops = [frac2f(x) for ln in cm["lines"] for m in re.findall(r"chop at ([^.]+)\.", ln) for x in m.split(",")]
    ok("milling blanks >= 12 in", all(c >= 12 for c in chops))
    p2 = subprocess.run([sys.executable, CM, os.path.join(d, "cl.json"), os.path.join(d, "b.json"), "--board", "C", "--only", "post"], capture_output=True, text=True)
    ok("--board gives one caveman line", p2.stdout.strip().startswith("C:") and p2.stdout.count("\n") == 1)
    print("cut map ok" if not bad else f"{bad} failed"); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

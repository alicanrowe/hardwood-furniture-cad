#!/usr/bin/env python3
"""Planted case for viewcheck.py: a build-book cover still drawn from the model before the stand's stretchers were
replaced by low aprons and a drawer. The drawer, low apron and runner must be flagged missing, the stretcher unknown and
the re-cut leg moved; the up-to-date record must pass clean."""
import json, os, subprocess, sys, tempfile
H = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(H, "views"); VC = os.path.join(H, "..", "viewcheck.py")


def run(views):
    with tempfile.TemporaryDirectory() as td:
        o = os.path.join(td, "o.json")
        r = subprocess.run([sys.executable, "-I", VC, "check", "--views", os.path.join(V, views), "--model", os.path.join(V, "model_now.json"),
                            "--cutlist", os.path.join(V, "cutlist.json"), "--json", o], capture_output=True, text=True)
        return r.returncode, {(f["check"], f["part"]) for f in json.load(open(o))}


ok = True
rc, got = run("views_good.json")
if rc or got:
    ok = False; print("FALSE ALARMS on the current cover:", got)
rc, got = run("views_old_cover.json")
want = {("missing_part", "Stand_Drawer_Front"), ("missing_part", "Stand_Drawer_Side_L"), ("missing_part", "Stand_Drawer_Runner_L"),
        ("missing_part", "Stand_Apron_Low_L"), ("unknown_part", "Stand_Stretcher_F"), ("moved_part", "Stand_Leg_FL")}
if rc != 1 or got != want:
    ok = False; print("old cover: missed", want - got, "extra", got - want)
print("viewcheck tests:", "all caught, no false alarms" if ok else "FAILED")
sys.exit(0 if ok else 1)

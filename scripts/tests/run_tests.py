#!/usr/bin/env python3
"""Runs cadcheck on every fixture and compares with expected.json. Prints caught / missed / false alarms."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
CC = os.path.join(HERE, "..", "cadcheck.py")
exp = json.load(open(os.path.join(HERE, "expected.json")))
specs = json.load(open(os.path.join(HERE, "specs.json")))
tot = dict(caught=0, missed=0, false=0)
for name, want in exp.items():
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "spec.json"); json.dump(specs.get(name, {}), open(sp, "w"))
        out = os.path.join(td, "o.json")
        subprocess.run([sys.executable, "-I", CC, os.path.join(HERE, "fixtures", name + ".glb"), "--units", "in", "--up", "z",
                        "--spec", sp, "--json", out], capture_output=True)
        got = [f for f in json.load(open(out)) if f["check"] != "skipped"]
    def match(w, f):
        return f["check"] in w[0].split("|") and ({f["part"], f.get("other")} >= set(w[1:]))
    caught = [w for w in want if any(match(w, f) for f in got)]
    missed = [w for w in want if w not in caught]
    false = [f for f in got if not any(match(w, f) for w in want)]
    tot["caught"] += len(caught); tot["missed"] += len(missed); tot["false"] += len(false)
    print(f"{name:12s} caught {len(caught)}/{len(want)}  false alarms {len(false)}")
    for w in missed:
        print("    MISSED", w)
    for f in false:
        print("    FALSE ", f["check"], f["part"], f.get("other", ""), f["detail"])
print(tot)

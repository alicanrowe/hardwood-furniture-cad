#!/usr/bin/env python3
"""Checks that every picture in a build book, drawing set or site page shows the piece as it is now.

A picture can be right when it is made and go wrong later: the model changes (a stretcher becomes a drawer) and an
old drawing stays on the cover. This check fails that. Every figure gets a record (views.json) saying which model it
was drawn from and which parts it draws; the check compares that with the current model and its cut list.

  # 1. record what each figure draws, when you render it (reads the render_drawings.js jobs file)
  python3 scripts/viewcheck.py record --jobs jobs.json --model MODEL.glb --units m --out views.json \\
          --page cover=1 --page stand=3 --kind cover=assembly
  # 2. check every record against the current model and cut list (and, with --pdf, that no page has an unrecorded figure)
  python3 scripts/viewcheck.py check --views views.json --model MODEL.glb --units m --cutlist build/cutlist.json \\
          [--pdf build/Build_book.pdf] [--json out.json]

Figure kinds:
  assembly   the whole piece or a sub-assembly, assembled. Every cut-list part inside its scope must be drawn.
  exploded   the same, pulled apart. Same rule.
  detail     a close-up of one joint or part. Only checks that what it draws still exists and hasn't moved.
  diagram    a 2-D set-up sketch (saw, fence, blade). Not drawn from the model; only needs a record.

Flags (each one fails):
  missing_part  a cut-list part inside an assembly or exploded figure's scope isn't in the figure
                (the drawer missing from the stand on the cover)
  unknown_part  the figure draws a part that is no longer in the model (the old stretchers)
  moved_part    a part the figure draws has a different size or place now (a re-cut leg)
  no_record     (--pdf) a page carries a picture with no record in views.json: nobody knows what it shows
Exit code 1 if anything is flagged.
"""
import argparse, json, os, re, sys, hashlib

TOL = 0.02   # inches


def sha12(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def model_parts(path, units="m"):
    """{name: [[x0,y0,z0],[x1,y1,z1]]} in inches. Takes a GLB, or a JSON of the same shape (for tests)."""
    if path.endswith(".json"):
        return json.load(open(path))["parts"]
    import trimesh
    k = {"m": 1 / 0.0254, "mm": 1 / 25.4, "in": 1.0}[units]
    s = trimesh.load(path, force="scene")
    out = {}
    for n in s.graph.nodes_geometry:
        T, g = s.graph[n]
        m = s.geometry[g].copy(); m.apply_transform(T)
        out[n] = (m.bounds * k).round(4).tolist()
    return out


def model_hash(path):
    if path.endswith(".json"):
        return json.load(open(path)).get("sha256", "")[:12]
    return sha12(path)


def bom_objects(cutlist):
    """every part name the cut list says exists, with its row label"""
    d = json.load(open(cutlist))
    rows = d.get("parts") or d.get("rows") or []
    out = {}
    for r in rows:
        for o in (r.get("members") or r.get("objects") or []):
            out[o] = r.get("label") or r.get("name") or o
    return out


def record(a):
    parts = model_parts(a.model, a.units)
    h = model_hash(a.model)
    pages = dict(p.split("=", 1) for p in a.page)
    kinds = dict(p.split("=", 1) for p in a.kind)
    views = json.load(open(a.out)) if os.path.exists(a.out) and a.append else []
    for j in json.load(open(a.jobs)):
        drawn = sorted(n for n in parts if any(re.search(p["re"], n) for p in j["parts"]))
        scope = j.get("scope") or "|".join("(?:%s)" % p["re"] for p in j["parts"])
        views = [v for v in views if v["id"] != j["id"]]
        views.append(dict(id=j["id"], page=pages.get(j["id"]), kind=kinds.get(j["id"], j.get("kind", "assembly")),
                          scope=scope, model_sha=h, drawn={n: parts[n] for n in drawn}))
    json.dump(views, open(a.out, "w"), indent=1)
    print(f"{len(views)} figure records -> {a.out} (model {h})")


def pdf_figure_pages(pdf, min_paths=40):
    """pages that carry a raster image or a vector drawing of more than min_paths paths"""
    import pymupdf
    d = pymupdf.open(pdf)
    out = []
    for i, p in enumerate(d):
        if p.get_images() or len(p.get_drawings()) > min_paths:
            out.append(i + 1)
    return out


def check(views, parts, bom, cur_sha, fig_pages=None, scope_all="^(?!$)"):
    flags = []
    for v in views:
        drawn = v.get("drawn") or {}
        tag = f"{v['id']} (page {v.get('page')})"
        if v["kind"] == "diagram":
            continue
        for n, b in drawn.items():
            if n not in parts:
                flags.append(dict(check="unknown_part", view=v["id"], page=v.get("page"), part=n,
                                  detail=f"{tag} draws {n}, which is no longer in the model (drawn from {v.get('model_sha')}, model is {cur_sha})"))
            elif b and max(abs(x - y) for p, q in zip(b, parts[n]) for x, y in zip(p, q)) > TOL:
                flags.append(dict(check="moved_part", view=v["id"], page=v.get("page"), part=n,
                                  detail=f"{tag} draws {n} at its old size or place; it has changed since {v.get('model_sha')}"))
        if v["kind"] in ("assembly", "exploded"):
            sc = re.compile(v.get("scope") or scope_all)
            for n, label in sorted(bom.items()):
                if sc.search(n) and n not in drawn:
                    flags.append(dict(check="missing_part", view=v["id"], page=v.get("page"), part=n,
                                      detail=f"{tag} should show {n} ({label}) but doesn't"))
    if fig_pages is not None:
        have = {int(v["page"]) for v in views if v.get("page") not in (None, "")}
        for pg in fig_pages:
            if pg not in have:
                flags.append(dict(check="no_record", view="", page=pg, part="",
                                  detail=f"page {pg} has a picture with no record in views.json: re-render it from the current model or record what it shows"))
    return flags


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("record")
    r.add_argument("--jobs", required=True); r.add_argument("--model", required=True); r.add_argument("--units", default="m")
    r.add_argument("--out", required=True); r.add_argument("--page", action="append", default=[]); r.add_argument("--kind", action="append", default=[])
    r.add_argument("--append", action="store_true", help="add to an existing views.json instead of starting over")
    c = sp.add_parser("check")
    c.add_argument("--views", required=True); c.add_argument("--model", required=True); c.add_argument("--units", default="m")
    c.add_argument("--cutlist", required=True); c.add_argument("--pdf"); c.add_argument("--json")
    a = ap.parse_args()
    if a.cmd == "record":
        return record(a)
    parts = model_parts(a.model, a.units)
    flags = check(json.load(open(a.views)), parts, bom_objects(a.cutlist), model_hash(a.model),
                  pdf_figure_pages(a.pdf) if a.pdf else None)
    for f in flags:
        print(f"[{f['check']}] {f['detail']}")
    print(f"{len(flags)} flags")
    if a.json:
        json.dump(flags, open(a.json, "w"), indent=1)
    sys.exit(1 if flags else 0)


if __name__ == "__main__":
    main()

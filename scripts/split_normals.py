#!/usr/bin/env python3
"""Re-export a GLB with split normals so flat CAD faces don't streak in web viewers and renderers.
SUPERSEDED for viewer GLBs by web_reshade.py (locks flat panels, refines coarse curves, 12-bit normals); always
finish with web_shading_check.py.

  python3 scripts/split_normals.py in.glb out.glb [--angle 30]

Meshes written with shared vertices (trimesh, many CAD exporters) get one averaged normal per corner, so a
box shades as if it were rounded: dark streaks run across flat faces. This splits vertices wherever two faces
meet at more than --angle degrees, so each flat face gets its own normals and curved surfaces stay smooth.
Node names, transforms and materials are kept.
"""
import argparse, math
import numpy as np
import trimesh
from trimesh.graph import smooth_shade

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--angle", type=float, default=30.0)
a = ap.parse_args()
sc = trimesh.load(a.src, force="scene")
for name, g in list(sc.geometry.items()):
    if not isinstance(g, trimesh.Trimesh):
        continue
    vis = g.visual
    s = smooth_shade(g, angle=math.radians(a.angle))
    if hasattr(vis, "material") and getattr(vis, "kind", None) != "texture":
        s.visual = trimesh.visual.TextureVisuals(material=vis.material)
    sc.geometry[name] = s
sc.export(a.dst)
print(f"{len(sc.geometry)} meshes, split at {a.angle} deg -> {a.dst}")

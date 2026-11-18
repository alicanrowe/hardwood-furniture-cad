"""Stills on white: hero (finished), process (raw wood), exploded (raw), and any named close-ups.

  blender -b -P scripts/blender/stills.py -- MODEL.glb --look look.json --out renders/
  python3 scripts/blender/stills.py MODEL.glb --look look.json --out renders/      (with pip install bpy)

look.json (all optional):
{"species": "walnut", "finish": "oil|char", "species_ply": "baltic birch",
 "parts": {"Side_Panel": {"figure": "cathedral"}, "Hinge|Screw": {"metal": "brass"}},
 "shots": [{"name": "hero", "finish": 1, "azimuth": 35, "elevation": 15},
           {"name": "process", "finish": 0, "azimuth": -30, "elevation": 25},
           {"name": "exploded", "finish": 0, "explode": 0.35, "azimuth": 35, "elevation": 22},
           {"name": "joint_FL", "finish": 0, "only": "^(Leg_FL|Apron_Front|Apron_L)$", "explode": 0.15}],
 "samples": 128, "size": [2400, 1600]}

Hero shots carry the finish (oil, or "char" for a charred or ebonised piece); process, joinery and exploded
shots are always plain wood. Every image is flattened onto pure white and saved as JPG. Exploded views move
each part out from the piece's centre along the direction it sits in, so joints open toward the camera.
"""
import json, math, os, re, sys

if sys.platform == "darwin" and not os.environ.get("ALLOW_LOCAL_RENDER"):   # never render on the owner's Mac
    sys.exit("refusing to render on a Mac: run this on a cloud machine or a render farm (ALLOW_LOCAL_RENDER=1 only if the owner asked).")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import look as LK

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("model"); ap.add_argument("--look"); ap.add_argument("--out", default="renders")
ap.add_argument("--samples", type=int); ap.add_argument("--size")
ap.add_argument("--up", default="auto", help="z for a Z-up GLB (trimesh/CAD export); Blender GLBs are Y up")
ap.add_argument("--units", default="m", choices=["m", "mm", "in"])
a = ap.parse_args(argv)
LOOK = json.load(open(a.look)) if a.look else {}
SHOTS = LOOK.get("shots") or [dict(name="hero", finish=1, azimuth=35, elevation=15),
                              dict(name="process", finish=0, azimuth=-35, elevation=24),
                              dict(name="exploded", finish=0, explode=0.35, azimuth=35, elevation=22)]
os.makedirs(a.out, exist_ok=True)
size = [int(x) for x in a.size.split("x")] if a.size else LOOK.get("size", [2400, 1600])

for shot in SHOTS:
    LK.reset()
    obs = LK.import_model(os.path.abspath(a.model), up=a.up, units=a.units)
    LK.assign(obs, LOOK)
    if shot.get("only"):
        for o in obs:
            if not re.search(shot["only"], o.name):
                bpy.data.objects.remove(o)
        obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo, hi = LK.bounds(obs); ctr = (lo + hi) / 2; rad = (hi - lo).length / 2
    for o in obs:
        o["finish"] = float(shot.get("finish", 0))
        if shot.get("explode"):
            c = sum((o.matrix_world @ Vector(b) for b in o.bound_box), Vector()) / 8
            d = c - ctr
            o.location += d * shot["explode"] * 2.0
    bpy.context.view_layer.update()
    LK.stage(obs)
    LK.camera(obs, shot.get("azimuth", 35), shot.get("elevation", 18), shot.get("lens", 70), aspect=tuple(size))
    LK.quality(a.samples or LOOK.get("samples", 96))
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = size
    png = os.path.join(a.out, f"_{shot['name']}.png")
    s.render.filepath = png; s.render.image_settings.file_format = "PNG"; s.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    jpg = os.path.join(a.out, f"{shot['name']}.jpg")
    LK.finish_white(png, jpg); os.remove(png)
    print("wrote", jpg)

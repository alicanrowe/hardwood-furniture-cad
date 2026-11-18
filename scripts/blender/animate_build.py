"""Build animation: the piece assembles group by group in shop order, opens into an exploded view to show
the joinery, gets its finish at the finishing step only, then turns.

  blender -b -P scripts/blender/animate_build.py -- MODEL.glb --anim anim.json --out build/anim.blend
  python3 scripts/blender/animate_build.py MODEL.glb --anim anim.json --out build/anim.blend --render build/frames
  python3 scripts/overlay.py build/frames build/anim.track.json --out build/build.mp4      # labels + encode

anim.json:
{"look": {...same as stills.py: species, finish (oil|char), parts figures...},
 "aspect": "16x9",                 # or "9x16" for reels
 "fps": 24,
 "groups": [                       # shop order: what gets built first comes in first
   {"match": "^Leg_", "title": "Legs", "note": "8/4 stock, mortised before tapering"},
   {"match": "^Apron_", "title": "Aprons", "note": "haunched tenons, mortises start 1/2 in down"},
   {"match": "Panel", "title": "Panels", "note": "float in their grooves, never glued"}],
 "seconds": {"group": 3.0, "explode": 4.0, "finish": 3.0, "turn": 4.0, "hold": 1.0}}

Rules built in (each one came from an animation that had to be re-rendered):
- Every part is raw wood until the finishing step; the finish is keyed per part at that step only (a sweep
  from the top down), so nothing shows oil or char early, however high it floats before then.
- White background, matte wood, split normals, grain along each part (see look.py).
- Parts arrive from outside the piece along the direction they sit in, then slide home along one axis, the
  way they would go together on the bench.
The script writes MODEL.track.json next to the .blend: the frame range and screen anchor of each step's
label, for overlay.py.
"""
import json, math, os, re, sys

if sys.platform == "darwin" and not os.environ.get("ALLOW_LOCAL_RENDER"):   # never render on the owner's Mac
    sys.exit("refusing to render on a Mac: run this on a cloud machine or a render farm (ALLOW_LOCAL_RENDER=1 only if the owner asked).")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import look as LK

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("model"); ap.add_argument("--anim"); ap.add_argument("--out", default="build/anim.blend")
ap.add_argument("--render", help="render frames (RGBA PNG) into this folder")
ap.add_argument("--samples", type=int, default=48); ap.add_argument("--scale", type=float, default=1.0, help="resolution scale for tests")
ap.add_argument("--every", type=int, default=1, help="render every Nth frame (tests)")
ap.add_argument("--up", default="auto"); ap.add_argument("--units", default="m", choices=["m", "mm", "in"])
a = ap.parse_args(argv)
A = json.load(open(a.anim)) if a.anim else {}
LOOK = A.get("look", {})
FPS = A.get("fps", 24)
SEC = dict(group=3.0, explode=4.0, finish=3.0, turn=4.0, hold=1.0); SEC.update(A.get("seconds", {}))
ASPECT = tuple(int(x) for x in A.get("aspect", "16x9").split("x"))

s = LK.reset()
obs = LK.import_model(os.path.abspath(a.model), up=a.up, units=a.units)
LK.assign(obs, LOOK)
GROUPS = A.get("groups") or [dict(match=".", title="Parts", note="")]
member = {}
for o in obs:
    for i, g in enumerate(GROUPS):
        if re.search(g["match"], o.name):
            member[o.name] = i; break
    else:
        member[o.name] = len(GROUPS) - 1
lo, hi = LK.bounds(obs); ctr = (lo + hi) / 2; size = (hi - lo).length
home = {o.name: o.location.copy() for o in obs}


def centre(o):
    return sum((o.matrix_world @ Vector(b) for b in o.bound_box), Vector()) / 8


pc = {o.name: centre(o) for o in obs}


def outward(o, k):
    d = pc[o.name] - ctr
    d.z = max(d.z, 0) + 0.15 * size          # come in from above and outside
    return d.normalized() * k * size if d.length > 1e-6 else Vector((0, 0, k * size))


def key_loc(o, f, loc, interp="BEZIER"):
    o.location = loc; o.keyframe_insert("location", frame=f)


def key_vis(o, f, show):
    o.hide_render = not show; o.hide_viewport = not show
    o.keyframe_insert("hide_render", frame=f); o.keyframe_insert("hide_viewport", frame=f)


def key_fin(o, f, v):
    o["finish"] = v; o.keyframe_insert('["finish"]', frame=f)


track = []
f = 1
for o in obs:
    key_vis(o, 1, False); key_fin(o, 1, 0.0)
# 1) groups arrive in shop order
for i, g in enumerate(GROUPS):
    g0 = f; g1 = f + int(SEC["group"] * FPS)
    arrive = g0 + int(0.25 * (g1 - g0)); seat = g0 + int(0.8 * (g1 - g0))
    mem = [o for o in obs if member[o.name] == i]
    for o in mem:
        key_vis(o, max(1, g0 - 1), False); key_vis(o, g0, True)
        start = home[o.name] + outward(o, 0.45)
        key_loc(o, g0, start); key_loc(o, arrive, start); key_loc(o, seat, home[o.name])
    if mem:
        gc = sum((pc[o.name] for o in mem), Vector()) / len(mem)
        track.append(dict(kind="step", title=g.get("title", ""), note=g.get("note", ""), start=g0, end=g1, world=list(gc)))
    f = g1
f += int(SEC["hold"] * FPS)
# 2) exploded view: everything opens out and closes again (raw wood)
e0 = f; e1 = e0 + int(SEC["explode"] * FPS * 0.35); e2 = e0 + int(SEC["explode"] * FPS * 0.65); e3 = e0 + int(SEC["explode"] * FPS)
for o in obs:
    key_loc(o, e0, home[o.name]); key_loc(o, e1, home[o.name] + outward(o, 0.3)); key_loc(o, e2, home[o.name] + outward(o, 0.3)); key_loc(o, e3, home[o.name])
track.append(dict(kind="step", title=A.get("explode_title", "Joinery"), note=A.get("explode_note", ""), start=e0, end=e3, world=list(ctr)))
f = e3 + int(SEC["hold"] * FPS * 0.5)
# 3) finishing step: the only time finish appears; sweeps down from the top
f0 = f; f1 = f0 + int(SEC["finish"] * FPS)
zmin, zmax = lo.z, hi.z
for o in obs:
    t = 1 - (pc[o.name].z - zmin) / max(1e-6, zmax - zmin)
    a0 = f0 + int(t * 0.6 * (f1 - f0)); a1 = a0 + int(0.4 * (f1 - f0))
    key_fin(o, f0 - 1, 0.0); key_fin(o, a0, 0.0); key_fin(o, a1, 1.0)
track.append(dict(kind="step", title=A.get("finish_title", "Finish"), note=A.get("finish_note", ""), start=f0, end=f1, world=list(ctr)))
f = f1 + int(SEC["hold"] * FPS)
# 4) turn
t0 = f; t1 = t0 + int(SEC["turn"] * FPS)
end = t1 + int(SEC["hold"] * FPS)
s.frame_start, s.frame_end = 1, end
s.render.fps = FPS

LK.stage(obs)
cam = LK.camera(obs, 25, 16, 60, margin=1.5, aspect=ASPECT)
s.render.resolution_x = int(s.render.resolution_x * a.scale); s.render.resolution_y = int(s.render.resolution_y * a.scale)
# slow orbit through the build, a wider turn at the end
piv = bpy.data.objects.new("CamPivot", None); s.collection.objects.link(piv); piv.location = ctr
bpy.context.view_layer.update()
mw = cam.matrix_world.copy(); cam.parent = piv; cam.matrix_world = mw
piv.rotation_euler = (0, 0, 0); piv.keyframe_insert("rotation_euler", frame=1)
piv.rotation_euler = (0, 0, math.radians(20)); piv.keyframe_insert("rotation_euler", frame=t0)
piv.rotation_euler = (0, 0, math.radians(140)); piv.keyframe_insert("rotation_euler", frame=t1)
for o in [*obs, piv]:
    if o.animation_data and o.animation_data.action:
        try:
            for fc in o.animation_data.action.fcurves:
                for k in fc.keyframe_points:
                    k.interpolation = "CONSTANT" if fc.data_path.startswith("hide") else "BEZIER"
        except Exception:
            pass
# screen anchors for the labels
for t in track:
    s.frame_set((t["start"] + t["end"]) // 2)
    p = world_to_camera_view(s, cam, Vector(t["world"]))
    t["anchor"] = [round(p.x, 3), round(1 - p.y, 3)]
LK.quality(a.samples)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))
tr = os.path.splitext(os.path.abspath(a.out))[0] + ".track.json"
json.dump(dict(fps=FPS, frames=end, aspect=list(ASPECT), steps=track), open(tr, "w"), indent=1)
print(f"{end} frames ({end / FPS:.1f} s), {len(track)} labelled steps -> {a.out}, {tr}")
if a.render:
    os.makedirs(a.render, exist_ok=True)
    s.render.image_settings.file_format = "PNG"; s.render.image_settings.color_mode = "RGBA"
    for fr in range(1, end + 1, a.every):
        s.frame_set(fr)
        s.render.filepath = os.path.join(os.path.abspath(a.render), f"f{fr:05d}.png")
        bpy.ops.render.render(write_still=True)
    print("frames ->", a.render)

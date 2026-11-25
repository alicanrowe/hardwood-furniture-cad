#!/usr/bin/env python3
"""Build the web viewer GLB for a furniture model, with the grain right on every part.

The site's 3D previews can't use the renders' procedural grain, so the viewer GLB carries a baked
texture on real UVs. Every way of getting there by hand has gone wrong at least twice (an auto-unwrap
laid the grain diagonally; a flat-sawn "figure" texture read as a contour map; parts merged into one
mesh per material so no check could see them; case sides ran their grain front to back because the
longest side won over the spec). This script does it one way:

- one mesh per part, never joined, named after the part;
- the grain axis comes from the cadcheck spec ("grain": "x|y|z") and only then from the longest side;
- long-grain faces get a straight (rift) texture with the lines along U; faces looking along the grain
  get a separate end-grain material (growth rings), and nothing else does;
- the textures are generated here (straight grain, end grain) from the species colour, so no flat-sawn,
  cathedral or swirly image can sneak in;
- metal parts (hinge, screw, pull...) get plain brass or steel.

  python3 scripts/web_glb.py MODEL.blend|MODEL.glb OUT.glb --spec PIECE.cadcheck.json --units in --up z \
      [--pose pose.json] [--drop 'REGEX'] [--repeat 0.45]

--units/--up describe the source model (a GLB is m, and Blender's glTF importer already turns it Z up, so
--up is ignored for a .glb; most CAD-in-inches blends are in / z). Shrine bench, 24 Nov: --up y on a GLB laid every
wood part on its back in the viewer while the grain check still passed.
--pose moves parts before export, in source units, Z up, e.g. an open door and a pulled drawer:
  [{"match": "^(Door_|Hinge_|HScrew_D_)", "rotate_deg": -100, "axis": "z", "point": [-8.31, -7.07, 0]},
   {"match": "^Drawer_", "translate": [0, -5.9, 0]}]
This only lays flat 2D grain, which is right for flat boards and turned parts (straight along their grain). Any part
that twists, sweeps or bends along its grain, or is glued up (stack lamination, staves, edge-glued panel), must
then be baked in 3D, or the viewer shows one board bent into shape (Shrine bench plank, 25 Nov 2026):
  python3 scripts/web_laminate.py OUT.glb BAKED.glb --spec PIECE.cadcheck.json --auto     (spec "lamination" per part)
Then run, all must pass before the GLB goes on the site:
  python3 scripts/web_grain_check.py BAKED.glb --spec PIECE.cadcheck.json --sheet grain_sheet.jpg
and look at the sheet. Compress afterwards with `gltf-transform prune` then `gltf-transform meshopt` (never gltfpack, which
merged parts and dropped names, and never `join`/`optimize` defaults).
Needs the bpy module (pip install bpy) or run inside Blender: blender -b -P web_glb.py -- ARGS
"""
import sys as _s
if '--' in _s.argv: _s.argv = [_s.argv[0]] + _s.argv[_s.argv.index('--') + 1:]
import argparse, json, math, os, re, random, tempfile
import numpy as np
from PIL import Image

SPECIES = {   # oiled colour (sRGB 0..1), the colour the renders' hero finish lands on
    "walnut": (0.40, 0.29, 0.22), "cherry": (0.62, 0.38, 0.25), "white oak": (0.70, 0.56, 0.39),
    "red oak": (0.74, 0.55, 0.40), "ash": (0.80, 0.70, 0.54), "hard maple": (0.85, 0.74, 0.58),
    "mahogany": (0.55, 0.30, 0.20), "sapele": (0.52, 0.30, 0.20), "pine": (0.82, 0.68, 0.46),
    "cedar": (0.66, 0.43, 0.30), "baltic birch": (0.84, 0.74, 0.58),
}
METAL = re.compile(r"(?i)(screw|bolt|hinge|steel|brass|bronze|stainless|iron|plate|pin\b|_pin|knob|pull|leaf)")


def _smooth(a, s, axis):
    k = np.exp(-0.5 * (np.arange(-3 * s, 3 * s + 1) / s) ** 2); k /= k.sum()
    return np.apply_along_axis(lambda r: np.convolve(np.pad(r, 3 * s, mode='wrap'), k, 'valid'), axis, a)


def _noise1(n, s, rng):
    return _smooth(rng.standard_normal(n), s, 0)


def straight_grain(rgb, W=1024, H=512, seed=1):
    """Rift / quartered long grain: parallel lines along U (x), tiling, slight wander, open pores."""
    rng = np.random.default_rng(seed)
    y = np.arange(H)[:, None].astype(float); x = np.arange(W)[None, :].astype(float)
    # ring lines across V: irregular spacing, lines drift a little along U (tileable)
    wander = sum(a * np.sin(2 * np.pi * (k * x / W + rng.random())) for k, a in ((1, 3.0), (2, 1.6), (5, .5)))
    v = y + wander
    spacing = 1 + 0.6 * _noise1(H, 6, rng) / (np.abs(_noise1(H, 6, rng)).max() + 1e-9)
    phase = np.cumsum(np.tile(1 / (7.5 * spacing), 1))  # rings per pixel, varying
    phase *= round(phase[-1]) / phase[-1]                 # whole number of rings so V tiles
    ring = np.interp(v % H, np.arange(H), phase) % 1.0
    late = np.clip((ring - 0.55) / 0.45, 0, 1) ** 1.5      # latewood: darker band
    tone = 1 - 0.28 * late
    streak = _smooth(_smooth(rng.standard_normal((H, W)), 1, 0), 40, 1)  # long pore streaks along U
    tone *= 1 + 0.10 * streak / (np.abs(streak).max() + 1e-9)
    band = _noise1(H, 25, rng)[:, None]; tone *= 1 + 0.08 * band / (np.abs(band).max() + 1e-9)
    img = np.clip(np.array(rgb)[None, None, :] * tone[..., None], 0, 1)
    return Image.fromarray((img * 255).astype(np.uint8))


def end_grain(rgb, N=512, seed=2):
    """End grain: growth-ring arcs from a pith off the board (rift: rings about 45 deg), pores, darker."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(float)
    cx, cy = -1.6 * N, -1.6 * N
    r = np.hypot(x - cx, y - cy)
    r += 2.5 * np.sin(2 * np.pi * (x / N + y / N) * 2 + 1)
    rings = (r / 11.0) % 1.0
    late = np.clip((rings - 0.6) / 0.4, 0, 1)
    tone = 0.78 - 0.22 * late
    pores = rng.random((N, N)) < 0.035 * (1 - late)
    tone[pores] *= 0.7
    img = np.clip(np.array(rgb)[None, None, :] * tone[..., None], 0, 1)
    return Image.fromarray((img * 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--spec'); ap.add_argument('--units', default='m', choices=['m', 'mm', 'in'])
    ap.add_argument('--up', default='y', choices=['y', 'z']); ap.add_argument('--pose')
    ap.add_argument('--drop', help='regex of parts a visitor never sees (screws inside, waste)')
    ap.add_argument('--repeat', type=float, default=0.45, help='metres of grain per texture repeat along U')
    a = ap.parse_args()
    import bpy, bmesh, mathutils
    spec = json.load(open(a.spec)) if a.spec else {}
    base_species = spec.get('species', 'walnut')

    def part_spec(name):
        out = {}
        for rx, d in spec.get('parts', {}).items():
            if re.search(rx, name): out.update(d)
        return out

    if a.src.endswith('.blend'):
        bpy.ops.wm.open_mainfile(filepath=a.src)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=a.src)
    if not a.src.endswith('.blend') and a.up != 'z':
        print('note: a GLB comes in Z up from the importer; ignoring --up', a.up); a.up = 'z'
    scale = {'m': 1.0, 'mm': 0.001, 'in': 0.0254}[a.units]
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.visible_get()]
    if a.drop: obs = [o for o in obs if not re.search(a.drop, o.name)]
    # bake world transforms into a fresh copy of each part, in metres, Z up
    up = mathutils.Matrix.Identity(4) if a.up == 'z' else mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
    S = mathutils.Matrix.Scale(scale, 4) @ up
    pose = json.load(open(a.pose)) if a.pose else []
    texdir = tempfile.mkdtemp()
    mats = {}

    def wood_mats(sp):
        if sp in mats: return mats[sp]
        rgb = SPECIES.get(sp, SPECIES['walnut'])
        out = []
        for kind, im in (('long', straight_grain(rgb, seed=len(sp) * 7 + 1)), ('end', end_grain(rgb, seed=len(sp) * 5 + 2))):
            p = os.path.join(texdir, f'{sp}_{kind}.png'.replace(' ', '_')); im.save(p)
            m = bpy.data.materials.new(f'{sp} {"long grain" if kind == "long" else "end grain"}')
            m.use_nodes = True; nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
            tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(p)
            nt.links.new(tx.outputs['Color'], bsdf.inputs['Base Color'])
            bsdf.inputs['Roughness'].default_value = 0.55 if kind == 'long' else 0.7
            out.append(m)
        mats[sp] = out; return out

    def metal_mat(name):
        key = 'steel' if re.search(r'(?i)steel|stainless|iron', name) else 'brass'
        if key in mats: return mats[key]
        m = bpy.data.materials.new(key); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.80, 0.58, 0.25, 1) if key == 'brass' else (0.6, 0.6, 0.62, 1)
        b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.35
        mats[key] = m; return m

    rnd = random.Random(7); built = []
    for o in obs:
        me = o.data.copy(); me.materials.clear()
        M = o.matrix_world.copy(); M0 = M.copy()
        for p in pose:
            if not re.search(p['match'], o.name): continue
            if 'rotate_deg' in p:
                c = mathutils.Vector(p['point'])
                M = (mathutils.Matrix.Translation(c) @ mathutils.Matrix.Rotation(math.radians(p['rotate_deg']), 4, p.get('axis', 'z').upper())
                     @ mathutils.Matrix.Translation(-c) @ M)
            if 'translate' in p: M = mathutils.Matrix.Translation(mathutils.Vector(p['translate'])) @ M
        me.transform(S @ M)
        n = bpy.data.objects.new(o.name + '__web', me); n['part'] = o.name; built.append((n, part_spec(o.name)))
        # the spec's grain axes are for the assembled model (Z up): turn them with the part's pose
        n['pose_rot'] = [list(r) for r in (up @ M @ M0.inverted() @ up.inverted()).to_3x3()]
    # keep only the built parts in the scene (cameras, lights, rigs and waste bodies all go)
    keep = {n.name for n, _ in built}
    for o in list(bpy.data.objects):
        if o.name not in keep: bpy.data.objects.remove(o, do_unlink=True)
    for n, _ in built:
        bpy.context.scene.collection.objects.link(n); n.name = n['part']; n.data.name = n['part']
    for n, ps in built:
        me = n.data
        if METAL.search(n.name) and not ps.get('species'):
            me.materials.append(metal_mat(n.name)); continue
        sp = ps.get('species', base_species)
        long_m, end_m = wood_mats(sp)
        me.materials.append(long_m); me.materials.append(end_m)
        P = np.array([v.co[:] for v in me.vertices])
        g_ax = ps.get('grain')
        if g_ax in ('x', 'y', 'z'):
            g = mathutils.Matrix(n['pose_rot']) @ mathutils.Vector([1.0 if g_ax == c else 0.0 for c in 'xyz'])
            g.normalize()
        else:
            C = P - P.mean(0); w, v = np.linalg.eigh(np.cov(C.T))
            e = [np.ptp(C @ v[:, k]) for k in range(3)]; g = mathutils.Vector(v[:, int(np.argmax(e))]).normalized()
        n['grain_axis'] = [g.x, g.z, -g.y]   # in the GLB's frame (Y up); web_grain_check.py reads it
        del n['pose_rot']
        bm = bmesh.new(); bm.from_mesh(me)
        uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new('UVMap')
        ou, ov = rnd.random(), rnd.random()
        L = a.repeat; asp = 2.0   # straight-grain texture is 2:1, grain along U
        for f in bm.faces:
            nrm = f.normal
            if abs(nrm.dot(g)) > 0.7:          # looking along the grain: end grain
                f.material_index = 1
                ax = mathutils.Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else mathutils.Vector((1, 0, 0))
                ax = (ax - nrm * ax.dot(nrm)).normalized(); bx = nrm.cross(ax).normalized()
                for l in f.loops:
                    q = l.vert.co; l[uvl].uv = (q.dot(ax) / 0.15 + ou, q.dot(bx) / 0.15 + ov)
            else:
                f.material_index = 0
                ax = (g - nrm * g.dot(nrm)).normalized(); bx = nrm.cross(ax).normalized()
                for l in f.loops:
                    q = l.vert.co; l[uvl].uv = (q.dot(ax) / L + ou, q.dot(bx) / (L / asp) + ov)
        bm.to_mesh(me); bm.free()
        # flat CAD faces: split normals at 30 deg so boards don't shade like pillows
        me.shade_smooth()
        if hasattr(me, 'set_sharp_from_angle'): me.set_sharp_from_angle(angle=math.radians(30))
    # the glTF exporter turns Z up into Y up itself
    bpy.ops.export_scene.gltf(filepath=a.dst, export_format='GLB', export_image_format='AUTO',
                              export_extras=True, export_yup=True)
    print(f'{len(built)} parts, {len(mats)} materials -> {a.dst}')


if __name__ == '__main__':
    main()

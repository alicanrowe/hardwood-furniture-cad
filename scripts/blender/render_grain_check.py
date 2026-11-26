"""Grain-direction check for a Blender render scene (procedural or image wood, any shader).

It doesn't trust the node graph. Each wood part is rendered alone, flat (its own base colour as emission, no
lights), straight down its thinnest axis. The grain angle is measured from the pixels with a structure tensor and
compared with the direction the grain must run. Run it before any sample still or animation goes out.

Where the grain must run:
- default: along the part's longest side;
- drawer bottoms (name has "Drawer_Bottom"): side to side, parallel to the drawer front, so the bottom moves front to
  back in its groove (rip-and-flip strips run across the drawer, never front to back);
- casework: a mitered or dovetailed case's grain wraps the box (the top runs left to right, so the sides run
  vertical). Say so in the spec, e.g. {"parts": {"Side_*": "z"}};
- square-ish blocks (keys, plugs) are skipped unless the spec names an axis;
- spec overrides: {"parts": {"<fnmatch pattern>": "x"|"y"|"z"|"longest"|"skip"}} (local axes), first match wins.
A part fails when its measured grain is more than --tol degrees (default 20) off, or when the figure is too weak to
read (coherence under 0.08, so a flat-colour "wood" can't pass). Ends are not checked here (see rendering-wood.md).

usage: blender -b scene.blend -P render_grain_check.py -- [--frame F] [--spec spec.json] [--only PATTERN]
                 [--mat-prefix W_] [--tol 20] [--sheet out.jpg] [--json out.json]
exit 1 on any fail. Prints one line per part: PASS/FAIL name measured expected coherence."""
import bpy, sys, json, math, fnmatch, os, tempfile
import numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def opt(k, d=None):
    return a[a.index(k) + 1] if k in a else d
FRAME = int(opt('--frame', bpy.context.scene.frame_end)); TOL = float(opt('--tol', 20))
SPEC = json.load(open(opt('--spec'))) if opt('--spec') else {}
ONLY = opt('--only'); PREFIX = opt('--mat-prefix', 'W_'); SHEET = opt('--sheet'); JOUT = opt('--json')
src = bpy.context.scene; src.frame_set(FRAME)
SKIP = ('Chalk', 'Waste', 'EndCap', 'Sap_', 'Log', 'Floor')

def wood_parts():
    for o in src.objects:
        if o.type != 'MESH' or o.hide_render or o.name.startswith(SKIP): continue
        if ONLY and not fnmatch.fnmatch(o.name, ONLY): continue
        m = [s for s in o.data.materials if s]
        if m and m[0].name.startswith(PREFIX): yield o

def world_axes(o):
    R = o.matrix_world.to_3x3(); d = list(o.dimensions)
    return [(R @ Vector(v)).normalized() for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1))], d

def expected(o):
    ax, d = world_axes(o)
    for pat, rule in (SPEC.get('parts') or {}).items():
        if fnmatch.fnmatch(o.name, pat):
            if rule == 'skip': return None, 'skip'
            if rule in 'xyz': return ax['xyz'.index(rule)], 'spec ' + rule
            break
    if sorted(d)[2] < sorted(d)[1] * 1.10: return None, 'skip'        # square-ish block (key, plug): no long side to judge
    if 'Drawer_Bottom' in o.name:
        fr = src.objects.get('Drawer_Front')
        if fr:
            fa, fd = world_axes(fr); return fa[int(np.argmax(fd))], 'parallel to drawer front'
    return ax[int(np.argmax(d))], 'longest side'

def flat_material(m):
    """copy of m whose surface is its own base colour as emission (no lights, no sheen, no shading)."""
    c = m.copy(); nt = c.node_tree; N = nt.nodes
    out = [n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output] or [n for n in N if n.type == 'OUTPUT_MATERIAL']
    b = [n for n in N if n.type == 'BSDF_PRINCIPLED']
    if not out or not b: return None
    em = N.new('ShaderNodeEmission'); bc = b[0].inputs['Base Color']
    if bc.is_linked: nt.links.new(bc.links[0].from_socket, em.inputs['Color'])
    else: em.inputs['Color'].default_value = bc.default_value
    nt.links.new(em.outputs[0], out[0].inputs['Surface']); return c

chk = bpy.data.scenes.new('grain_chk'); chk.render.engine = 'CYCLES'; chk.cycles.samples = 4
chk.cycles.use_denoising = False; chk.render.film_transparent = True
chk.view_settings.view_transform = 'Standard'; chk.render.resolution_x = chk.render.resolution_y = 320
w = bpy.data.worlds.new('k'); w.color = (0, 0, 0); chk.world = w
cd = bpy.data.cameras.new('gc'); cd.type = 'ORTHO'; cam = bpy.data.objects.new('gc', cd); chk.collection.objects.link(cam); chk.camera = cam
tmp = tempfile.mkdtemp(); rows = []; fails = 0; thumbs = []
for o in wood_parts():
    exp, why = expected(o)
    if why == 'skip': continue
    ax, d = world_axes(o); thin = ax[int(np.argmin(d))]
    if sorted(d)[1] < 1e-3: continue
    c = o.copy(); c.data = o.data; c.parent = None; c.animation_data_clear(); c.matrix_world = o.matrix_world.copy()
    fm = flat_material(o.data.materials[0])
    if fm is None: continue
    c.data = o.data.copy(); c.data.materials.clear(); c.data.materials.append(fm)
    chk.collection.objects.link(c)
    ctr = o.matrix_world @ (sum((Vector(b) for b in o.bound_box), Vector()) / 8)
    cd.ortho_scale = max(d) * 1.08
    sd = sorted(d); chk.render.resolution_x = chk.render.resolution_y = int(min(1600, max(320, 60 * sd[2] / max(sd[1], 1e-3))))
    up = exp if abs(exp.dot(thin)) < 0.9 else ax[int(np.argsort(d)[1])]
    z = thin; x = up.cross(z).normalized(); y = z.cross(x)
    cam.matrix_world = Matrix.Translation(ctr + z * (max(d) * 2 + 10)) @ Matrix((x, y, z)).transposed().to_4x4()
    cd.clip_end = max(d) * 4 + 40
    chk.render.filepath = os.path.join(tmp, o.name + '.png'); bpy.ops.render.render(write_still=True, scene=chk.name)
    chk.collection.objects.unlink(c)
    img = bpy.data.images.load(chk.render.filepath); px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4); bpy.data.images.remove(img)
    g = px[..., :3].mean(2); al = px[..., 3] > 0.99
    gy, gx = np.gradient(g); m = al.copy()
    for s in (1, 2, 3): m[s:] &= al[:-s]; m[:-s] &= al[s:]; m[:, s:] &= al[:, :-s]; m[:, :-s] &= al[:, s:]
    jxx, jyy, jxy = (gx * gx)[m].sum(), (gy * gy)[m].sum(), (gx * gy)[m].sum()
    coh = math.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-12)
    ang_g = 0.5 * math.atan2(2 * jxy, jxx - jyy)              # dominant gradient direction (image coords, y up)
    grain = math.degrees(ang_g) + 90                           # grain runs across the gradient
    p0 = world_to_camera_view(chk, cam, ctr); p1 = world_to_camera_view(chk, cam, ctr + exp * max(d) * 0.3)
    want = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
    err = abs((grain - want + 90) % 180 - 90)
    ok = bool(err <= TOL and coh >= 0.08); fails += (not ok)
    rows.append(dict(part=o.name, measured=round(grain % 180, 1), expected=round(want % 180, 1), off=round(err, 1), coherence=round(coh, 3), rule=why, ok=ok))
    print(('PASS' if ok else 'FAIL'), o.name, f'off {err:.0f} deg', f'coh {coh:.2f}', f'({why})')
    thumbs.append((o.name, chk.render.filepath, ok))
if SHEET and thumbs:
    from PIL import Image, ImageDraw
    n = len(thumbs); cols = 8; rws = (n + cols - 1) // cols; S = Image.new('RGB', (cols * 170, rws * 190), (255, 255, 255)); dr = ImageDraw.Draw(S)
    for i, (nm, f, ok) in enumerate(thumbs):
        t = Image.open(f).convert('RGBA').resize((160, 160)); bg = Image.new('RGBA', t.size, (255, 255, 255, 255)); bg.alpha_composite(t)
        x, y = (i % cols) * 170 + 5, (i // cols) * 190 + 5; S.paste(bg.convert('RGB'), (x, y))
        dr.text((x, y + 162), ('ok ' if ok else 'FAIL ') + nm[:24], fill=(0, 0, 0) if ok else (200, 0, 0))
    S.save(SHEET, quality=88)
if JOUT: json.dump(rows, open(JOUT, 'w'), indent=1)
print(f'GRAIN {len(rows) - fails}/{len(rows)} pass')
sys.exit(1 if fails else 0)

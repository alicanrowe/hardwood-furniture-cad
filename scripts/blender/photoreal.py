"""Photoreal product stills: a real room, real light falloff, worn materials, a real lens, AgX, film finish.
Built from a study of an all-CAD Instagram account whose renders pass as photos (24 Nov 2026); see
references/photoreal.md for the gap list. Our old furniture stills were cut-outs: Standard view, a white world,
a shadow catcher flattened onto 255 white, factory-clean procedural metal, 64 samples. This replaces that look
for hero shots. Catalogue squares on pure white can still use look.py.

blender -b -P photoreal.py -- MODEL.glb OUTDIR SHOTS_JSON [--room gallery|pool] [--samples 384] [--scale 1.0]
   or  python3 photoreal.py -- ...   (pip install bpy==5.3.0)

SHOTS_JSON: [{"name":"hero","az":30,"el":6,"lens":50,"size":[1600,2000],"fstop":4,"focus":[x,y,z] mm (optional),
              "height":1.15 (camera height m, optional), "margin":1.25}]
Materials come from each GLB material name (ss_*, al_*, steel*, gfrc_*, walnut, acrylic, leather ...); unknown names
fall back to brushed stainless. Every metal gets: brushed streaks along the part's long axis, smudge-driven
roughness variation, and a rolled-edge bevel normal. Nothing in this file changes geometry.
"""
import re, sys, os, json, math
import bpy
import os as _os, sys as _sys
_sys.path[:0] = [_os.path.dirname(_os.path.abspath(__file__)), _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))]
from mathutils import Vector

# ----------------------------------------------------------------------------------------------- helpers
def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def N(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def reset(samples=384, threads=0, device="CPU"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    c = s.cycles
    c.device = device
    if device == "GPU":
        try:
            p = bpy.context.preferences.addons["cycles"].preferences
            p.compute_device_type = "OPTIX"; p.get_devices()
            for d in p.devices: d.use = True
        except Exception as e:
            print("GPU setup failed, CPU:", e); c.device = "CPU"
    c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.008
    c.use_denoising = True
    try: c.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    c.max_bounces = 10; c.glossy_bounces = 6; c.diffuse_bounces = 4; c.transmission_bounces = 10
    c.caustics_reflective = False; c.caustics_refractive = False
    c.blur_glossy = 0.4                      # filter glossy: kills fireflies from the small hot lights
    c.sample_clamp_indirect = 8
    if threads: s.render.threads_mode = "FIXED"; s.render.threads = threads
    # AgX, a contrasty look: real blacks, highlights that roll off instead of clipping to flat white
    s.view_settings.view_transform = "AgX"
    for lk in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try: s.view_settings.look = lk; break
        except Exception: pass
    s.render.film_transparent = False
    s.view_settings.exposure = float(os.environ.get("EXPO", "0"))
    return s


def import_glb(path, smooth_angle=35):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    obs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in obs:   # CAD facets: flat faces flat, round parts smooth
        o.data.shade_smooth_by_angle(angle=math.radians(smooth_angle)) if hasattr(o.data, "shade_smooth_by_angle") else None
    return obs


def bounds(obs):
    lo = Vector((1e9,) * 3); hi = -lo
    for o in obs:
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return lo, hi


def long_axis(o):
    d = Vector(o.dimensions)
    return max(range(3), key=lambda i: d[i])

# ----------------------------------------------------------------------------------------------- materials
def _edge_and_bump(nt, height=None, strength=0.0, dist=0.0003, bevel=0.0008):
    """Rolled edges (Bevel node: real machined and cast parts never have a knife edge; the bright line on every
    edge is most of what reads 'manufactured') + optional micro bump. Returns the Normal socket."""
    bv = N(nt, "ShaderNodeBevel", Radius=bevel); bv.samples = 8
    if height is None:
        return bv.outputs["Normal"]
    bp = N(nt, "ShaderNodeBump", Strength=strength, Distance=dist)
    nt.links.new(height, bp.inputs["Height"]); nt.links.new(bv.outputs["Normal"], bp.inputs["Normal"])
    return bp.outputs["Normal"]


def metal(name, col=(0.62, 0.62, 0.63), rough=(0.18, 0.42), axis=2, brush=1.0, bevel=0.0008, smudge=1.0):
    """Brushed/satin metal with life in it: streaks along `axis`, cloudy smudges (fingerprints, polishing
    swirl) driving roughness, and a bevel normal. rough=(min,max) is the range the smudges move between."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Metallic"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # streaks: noise squashed along the brushing axis so it only varies across it
    mp = nt.nodes.new("ShaderNodeMapping"); sc = [1.0, 1.0, 1.0]; sc[axis] = 0.006; mp.inputs["Scale"].default_value = sc
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    st = N(nt, "ShaderNodeTexNoise", Scale=1400.0, Detail=6.0, Roughness=0.7)
    nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    # smudges: slow cloudy noise
    sm = N(nt, "ShaderNodeTexNoise", Scale=28.0, Detail=10.0, Roughness=0.55)
    nt.links.new(tc.outputs["Object"], sm.inputs["Vector"])
    smr = nt.nodes.new("ShaderNodeValToRGB"); smr.color_ramp.elements[0].position = 0.30; smr.color_ramp.elements[1].position = 0.80
    nt.links.new(sm.outputs["Fac"], smr.inputs["Fac"])
    mix = N(nt, "ShaderNodeMix"); mix.data_type = "FLOAT"
    mix.inputs[0].default_value = 0.35 * brush               # streak share of the roughness signal
    nt.links.new(smr.outputs["Color"], mix.inputs[2]); nt.links.new(st.outputs["Fac"], mix.inputs[3])
    rr = N(nt, "ShaderNodeMapRange"); rr.inputs["To Min"].default_value = rough[0]; rr.inputs["To Max"].default_value = rough[0] + (rough[1] - rough[0]) * smudge
    nt.links.new(mix.outputs[0], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    # colour: tiny drift so big faces aren't one flat value
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*lin(tuple(x * 0.965 for x in col)), 1); cr.color_ramp.elements[1].color = (*lin(col), 1)
    nt.links.new(sm.outputs["Fac"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(_edge_and_bump(nt, st.outputs["Fac"], 0.04 * brush, 0.0002, bevel), b.inputs["Normal"])
    return m


def gfrc(name, col=(0.045, 0.045, 0.05), rough=0.8, var=0.10, bevel=0.0025):
    """Cast GFRC/concrete: cloudy pigment drift, pinholes, sand bump, matte sealer, soft cast arris."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = N(nt, "ShaderNodeTexNoise", Scale=6.0, Detail=10.0); nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*lin(tuple(x * (1 - var) for x in col)), 1); ramp.color_ramp.elements[1].color = (*lin(tuple(min(1, x * (1 + 2 * var)) for x in col)), 1)
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    rr = N(nt, "ShaderNodeMapRange"); rr.inputs["To Min"].default_value = rough - 0.18; rr.inputs["To Max"].default_value = rough
    nt.links.new(n1.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.18
    n2 = N(nt, "ShaderNodeTexNoise", Scale=900.0, Detail=2.0); nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    v = N(nt, "ShaderNodeTexVoronoi", Scale=220.0); nt.links.new(tc.outputs["Object"], v.inputs["Vector"])
    mr = N(nt, "ShaderNodeMapRange"); mr.inputs["From Max"].default_value = 0.07
    nt.links.new(v.outputs["Distance"], mr.inputs["Value"])
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY"
    nt.links.new(n2.outputs["Fac"], mx.inputs[0]); nt.links.new(mr.outputs["Result"], mx.inputs[1])
    nt.links.new(_edge_and_bump(nt, mx.outputs["Value"], 0.45, 0.0005, bevel), b.inputs["Normal"])
    return m


def floor_concrete(name="Floor", col=(0.52, 0.515, 0.505), rough=(0.32, 0.72)):
    """Troweled studio concrete: big soft mottling, darker stains, satin patches that give a blurred
    reflection of the piece (the single biggest 'it is standing somewhere real' cue after the contact shadow)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    a = N(nt, "ShaderNodeTexNoise", Scale=0.9, Detail=12.0, Roughness=0.6); nt.links.new(tc.outputs["Object"], a.inputs["Vector"])
    c = N(nt, "ShaderNodeTexNoise", Scale=7.0, Detail=8.0, Roughness=0.55); nt.links.new(tc.outputs["Object"], c.inputs["Vector"])
    mixc = N(nt, "ShaderNodeMix"); mixc.data_type = "FLOAT"; mixc.inputs[0].default_value = 0.4
    nt.links.new(a.outputs["Fac"], mixc.inputs[2]); nt.links.new(c.outputs["Fac"], mixc.inputs[3])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[0].color = (*lin(tuple(x * 0.82 for x in col)), 1); ramp.color_ramp.elements[1].color = (*lin(tuple(min(1, x * 1.06) for x in col)), 1)
    nt.links.new(mixc.outputs[0], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    rr = N(nt, "ShaderNodeMapRange"); rr.inputs["To Min"].default_value = rough[0]; rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(a.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    f = N(nt, "ShaderNodeTexNoise", Scale=1800.0, Detail=2.0); nt.links.new(tc.outputs["Object"], f.inputs["Vector"])
    bp = N(nt, "ShaderNodeBump", Strength=0.12, Distance=0.0004); nt.links.new(f.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def matte(name, col, rough=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(col), 1); b.inputs["Roughness"].default_value = rough
    return m


METALS = {   # name prefix -> (srgb colour, roughness range, brush strength)
    "ss_brushed": ((0.58, 0.58, 0.59), (0.13, 0.25), 1.0),
    "al_brushed": ((0.66, 0.66, 0.67), (0.16, 0.36), 1.0),
    "al_bead": ((0.62, 0.62, 0.63), (0.45, 0.62), 0.2),
    "al_clear": ((0.66, 0.66, 0.67), (0.36, 0.55), 0.5),
    "steel_black": ((0.07, 0.068, 0.066), (0.32, 0.5), 0.6),
    "al_black": ((0.045, 0.045, 0.048), (0.3, 0.5), 0.5),
    "steel": ((0.66, 0.66, 0.67), (0.12, 0.3), 0.6),
}
GFRC = {"gfrc_ink": (0.045, 0.045, 0.05), "gfrc_black": (0.075, 0.072, 0.07), "gfrc_charcoal": (0.2, 0.195, 0.19),
        "gfrc_pale": (0.52, 0.515, 0.5), "gfrc_bone": (0.7, 0.67, 0.61), "gfrc_oxblood": (0.3, 0.075, 0.065)}


WOOD = re.compile(r"(?i)walnut|oak|\bash\b|ash[ _]|maple|cherry|cedar|wood|birch|mahogany|sapele|pine")


def dress(obs):
    cache = {}
    for o in obs:
        nm = (o.active_material.name.split(".")[0] if o.active_material else "ss_brushed")
        if (o.active_material is not None and o.active_material.get("woodlib")) or WOOD.search(nm):
            # wood comes from the wood library only (woodlib_bl): species from the stamp or the material name
            import woodlib_bl as WB
            st = WB.W.parse_stamp(o.active_material.get("woodlib")) if o.active_material is not None else None
            sp = st[0] if st else next((k for k in sorted(WB.W.LIB["species"], key=len, reverse=True) if k.split()[-1] in nm.lower()), "walnut")
            WB.apply(o, sp, cut=st[1] if st and st[1] in WB.W.CUTS else "auto", finish=st[2] if st else "oil", studio="photoreal" if WB.W.LIB.get("house", {}).get("photoreal") else None)
            continue
        ax = long_axis(o)
        key = (nm, ax)
        if key not in cache:
            if nm in GFRC:
                cache[key] = gfrc(nm + "_P", GFRC[nm])
            else:
                col, rg, br = METALS.get(nm, METALS["ss_brushed"])
                cache[key] = metal(f"{nm}_{ax}_P", col, rg, ax, br)
        o.data.materials.clear(); o.data.materials.append(cache[key])

# ----------------------------------------------------------------------------------------------- rooms
def _plane(name, size, loc, rot=(0, 0, 0), mat=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = (size[0], size[1], 1)
    if mat: o.data.materials.append(mat)
    return o


def _area(name, loc, target, size, energy, spread_deg=180, color=(1, 1, 1), shape="RECTANGLE", visible=False):
    d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.color = color; d.shape = shape
    if shape in ("RECTANGLE", "ELLIPSE"): d.size, d.size_y = size
    else: d.size = size[0]
    d.spread = math.radians(spread_deg)
    L = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(L)
    L.location = Vector(loc); L.rotation_euler = (Vector(target) - L.location).to_track_quat("-Z", "Y").to_euler()
    L.visible_camera = visible
    return L


def _world_gradient(top=0.25, horizon=0.02, cam=0.0):
    """Dim top-lit dome for reflections; camera rays see `cam` (so the backdrop stays the room/black)."""
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True; nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    mr = N(nt, "ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = horizon; mr.inputs["To Max"].default_value = top
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    lp = nt.nodes.new("ShaderNodeLightPath")
    mx = N(nt, "ShaderNodeMix"); mx.data_type = "FLOAT"
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); nt.links.new(mr.outputs["Result"], mx.inputs[2]); mx.inputs[3].default_value = cam
    nt.links.new(mx.outputs[0], bg.inputs["Strength"])
    bg.inputs["Color"].default_value = (1, 1, 1, 1)


def strips(ctr, h, energy, cool=(0.92, 0.96, 1.0)):
    """Two tall strip boxes either side of the camera axis, invisible to camera. Metal is only as bright as what
    it reflects: without these, brushed steel in a dark room reflects black and reads as dark plastic."""
    for sx in (-1, 1):
        L = _area("Strip%+d" % sx, (ctr.x + sx * 1.5, ctr.y - 0.9, h * 0.6), (ctr.x, ctr.y, h * 0.45), (0.35, 2.2), energy, 90, cool)
        L.visible_diffuse = False   # reflections only, so they don't flatten the key's falloff


def link_strips(obs):
    """Light-link the strip boxes to the piece only: the satin floor would otherwise mirror them as hot blobs."""
    col = bpy.data.collections.new("PieceOnly")
    for o in obs: col.objects.link(o)
    for L in bpy.data.objects:
        if L.type == "LIGHT" and L.name.startswith("Strip"):
            L.light_linking.receiver_collection = col


def room(kind, ctr, size):
    """gallery: pale concrete floor, pale walls, one big overhead softbox (light room, keeps the site's white).
    pool: dark room, one overhead spot throwing a pool on the floor that dies off before the frame edge."""
    if kind == "gallery":
        fl = _plane("Floor", (30, 30), (ctr.x, ctr.y, 0), mat=floor_concrete("Floor", (0.50, 0.495, 0.485), (0.30, 0.68)))
        wall = matte("Wall", (0.80, 0.80, 0.79), 0.92)
        _plane("BackWall", (30, 8), (ctr.x, ctr.y + 3.2 * max(1, size), 4), (math.radians(90), 0, 0), wall)
        _plane("SideWall", (30, 8), (ctr.x + 3.6 * max(1, size), ctr.y, 4), (0, math.radians(90), 0), wall)
        _plane("SideWallL", (30, 8), (ctr.x - 3.6 * max(1, size), ctr.y, 4), (0, math.radians(90), 0), wall)
        _area("Softbox", (ctr.x - 0.3, ctr.y - 0.4, 3.4), (ctr.x, ctr.y, 0.2), (4.0, 4.0), 520, 120, (1.0, 0.97, 0.93))
        _area("Rim", (ctr.x + 1.6, ctr.y + 2.2, 1.9), (ctr.x, ctr.y, 0.7), (1.2, 0.5), 60, 60, (0.9, 0.95, 1.0))
        _area("Bounce", (ctr.x, ctr.y - 4.0, 1.3), (ctr.x, ctr.y, 0.6), (3.0, 1.6), 12, 180)
        strips(ctr, 1.4, 90)
        _world_gradient(0.35, 0.05, 0.0)
    else:
        fl = _plane("Floor", (30, 30), (ctr.x, ctr.y, 0), mat=floor_concrete("Floor", (0.24, 0.238, 0.235), (0.22, 0.58)))
        _area("Spot", (ctr.x - 0.15, ctr.y - 0.25, 3.3), (ctr.x, ctr.y - 0.05, 0.0), (0.9, 0.9), 330, 24, (1.0, 0.96, 0.9), "DISK")
        _area("Rim", (ctr.x + 1.2, ctr.y + 2.4, 2.2), (ctr.x, ctr.y, 0.8), (0.8, 0.3), 40, 35, (0.85, 0.92, 1.0))
        strips(ctr, 1.4, 70)
        _world_gradient(0.12, 0.0, 0.0)
    return fl

# ----------------------------------------------------------------------------------------------- camera
def camera(obs, sh, W, H):
    s = bpy.context.scene
    lo, hi = bounds(obs); ctr = (lo + hi) / 2; rad = (hi - lo).length / 2
    lens = sh.get("lens", 50)
    cd = bpy.data.cameras.new(sh["name"]); cd.lens = lens; cd.sensor_width = 36; cd.sensor_fit = "AUTO"
    cam = bpy.data.objects.new(sh["name"], cd); s.collection.objects.link(cam); s.camera = cam
    fov = 2 * math.atan(18 / lens * (min(W, H) / max(W, H) if W < H else 1))
    dist = sh.get("dist", rad * sh.get("margin", 1.25) / math.sin(fov / 2))
    az, el = math.radians(sh.get("az", 30)), math.radians(sh.get("el", 6))
    aim = Vector(sh["aim"]) * 0.001 if "aim" in sh else ctr
    cam.location = aim + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    if "height" in sh: cam.location.z = sh["height"]
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    # a real lens: focus on the piece's front third, shallow enough that the room softens
    cd.dof.use_dof = True; cd.dof.aperture_fstop = sh.get("fstop", 4.0); cd.dof.aperture_blades = 7
    f = Vector(sh["focus"]) * 0.001 if "focus" in sh else ctr
    cd.dof.focus_distance = (f - cam.location).length
    return cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    glb, outdir, shots = argv[0], argv[1], argv[2]
    opt = {argv[i][2:]: argv[i + 1] for i in range(3, len(argv) - 1, 2) if argv[i].startswith("--")}
    shots = json.load(open(shots)) if os.path.exists(shots) else json.loads(shots)
    os.makedirs(outdir, exist_ok=True)
    s = reset(int(opt.get("samples", 384)), device=opt.get("device", "CPU"))
    obs = import_glb(glb)
    lo, hi = bounds(obs)
    dz = -lo.z                                   # sit on the floor, never under it
    for o in obs:
        if o.parent is None: o.location.z += dz
    bpy.context.view_layer.update()
    dress(obs)
    lo, hi = bounds(obs); ctr = (lo + hi) / 2
    room(opt.get("room", "gallery"), ctr, max(1.0, (hi - lo).length))
    link_strips(obs)
    scale = float(opt.get("scale", 1.0))
    for sh in shots:
        W, H = sh.get("size", [1600, 2000]); W, H = int(W * scale), int(H * scale)
        s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = W, H, 100
        camera(obs, sh, W, H)
        s.render.image_settings.file_format = "PNG"; s.render.image_settings.color_mode = "RGB"
        s.render.filepath = os.path.join(outdir, f"{sh['name']}_{opt.get('room', 'gallery')}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", s.render.filepath)


if __name__ == "__main__":
    main()

"""Shared Blender look for stills and build animations: white world, matte PBR wood with grain that follows
each part, split normals, finish switched per part, camera framing.

Runs inside Blender (`blender -b -P script.py -- args`) or with the `bpy` Python module (`pip install bpy`).

Rules this file enforces (each one came from a render that had to be redone):
- Solid white background in every output. Never a transparent PNG or a keyed cut-out: contact shadows are
  rendered on a shadow catcher and composited onto pure white before saving (see finish_white()).
- Matte wood: principled BSDF, roughness 0.55 to 0.7 raw and about 0.45 oiled, no clearcoat or coat sheen.
- Split normals: imported CAD meshes get their custom normals cleared and are shaded smooth by angle (30 deg),
  so flat faces stay flat and don't streak, and curved parts stay smooth.
- Grain follows each part: stripes run along the part's length (its longest side, or the spec's grain).
  Panels marked "cathedral" get plain-sawn figure with the cathedral centred and straight grain at both edges;
  rails, stiles, aprons and legs get straight grain.
- Finish is a per-part value 0..1 (custom property "finish"): process and joinery shots render raw (0),
  hero shots finished (1), and an animation only turns it on at its finishing step.
"""
import math, re
import bpy
from mathutils import Vector, Matrix

SPECIES = {   # raw (planed) colour, oiled colour, linear-ish sRGB 0..1
    "walnut": ((0.47, 0.36, 0.27), (0.22, 0.13, 0.08)),
    "cherry": ((0.72, 0.48, 0.33), (0.45, 0.20, 0.10)),
    "white oak": ((0.78, 0.66, 0.48), (0.55, 0.40, 0.24)),
    "red oak": ((0.80, 0.62, 0.48), (0.58, 0.36, 0.22)),
    "ash": ((0.85, 0.77, 0.62), (0.66, 0.54, 0.38)),
    "hard maple": ((0.90, 0.82, 0.68), (0.74, 0.60, 0.40)),
    "mahogany": ((0.62, 0.36, 0.25), (0.38, 0.16, 0.08)),
    "sapele": ((0.60, 0.36, 0.24), (0.36, 0.16, 0.08)),
    "pine": ((0.88, 0.76, 0.56), (0.70, 0.52, 0.30)),
    "baltic birch": ((0.88, 0.80, 0.64), (0.72, 0.60, 0.42)),
}
CHAR = (0.035, 0.032, 0.030)     # charred / ebonised hero finish (shou sugi ban, ebonised ash)
HARDWARE = re.compile(r"(screw|bolt|hinge|steel|brass|bronze|stainless|iron|sheet|plate|pin\b|_pin|knob|pull|glass|leaf|grille)", re.I)


def srgb_to_lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    try:
        s.view_settings.view_transform = "Standard"    # white stays 255 white; Filmic/AgX grey it out
        s.view_settings.look = "None"
    except Exception:
        pass
    return s


def import_model(path, flat_angle=30.0, up="auto", units="m"):
    """Import a GLB/glTF/STL/blend. up/units describe the FILE: a Blender GLB is metres, Y up (the default);
    a GLB written with Z up in inches (trimesh, some CAD exports) needs up='z', units='in'."""
    if path.lower().endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=path)
    elif path.lower().endswith(".stl"):
        bpy.ops.wm.stl_import(filepath=path)
    elif path.lower().endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    k = {"m": 1.0, "mm": 0.001, "in": 0.0254}[units]
    rot = Matrix.Identity(4)
    if up == "z" and path.lower().endswith((".glb", ".gltf")):
        rot = Matrix.Rotation(math.radians(-90), 4, "X")     # undo the importer's Y-up conversion
    if k != 1.0 or rot != Matrix.Identity(4):
        M = Matrix.Scale(k, 4) @ rot
        roots = [o for o in bpy.context.scene.objects if o.parent is None]
        for o in roots:
            o.matrix_world = M @ o.matrix_world
        bpy.context.view_layer.update()
        for o in obs:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        bpy.context.view_layer.update()
        for o in obs:
            o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    split_normals(obs, flat_angle)
    return obs


def split_normals(obs, angle=30.0):
    """Clear imported custom normals, then smooth by angle: flat CAD faces stop streaking."""
    for o in obs:
        me = o.data
        try:
            if me.has_custom_normals:
                with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except Exception:
            pass
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    if obs:
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle), keep_sharp_edges=True)
    bpy.ops.object.select_all(action="DESELECT")


def obb_axes(o):
    """World-space length, width, thickness axes of a part from its vertices (PCA), and its centre."""
    import numpy as np
    mw = o.matrix_world
    vs = np.array([tuple(mw @ v.co) for v in o.data.vertices])
    if len(vs) < 4:
        return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), Vector(vs.mean(0)) if len(vs) else Vector()
    c = vs.mean(0)
    w, V = np.linalg.eigh(np.cov((vs - c).T))
    ax = [Vector(V[:, i]) for i in np.argsort(w)[::-1]]
    return ax[0], ax[1], ax[2], Vector(c)


def wood_material(name, species="walnut", figure="straight", finish_kind="oil"):
    """One node tree per species/figure/finish. Grain direction and finish amount come from per-object
    custom properties: 'g_len' (vector along the grain), 'g_across' (across the face), 'finish' (0..1)."""
    key = f"WOOD_{species}_{figure}_{finish_kind}"
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    raw, oiled = SPECIES.get(species, SPECIES["walnut"])
    fin = CHAR if finish_kind == "char" else oiled
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    bs = N.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Specular IOR Level"].default_value = 0.35
    for k in ("Coat Weight", "Sheen Weight"):
        if k in bs.inputs:
            bs.inputs[k].default_value = 0.0
    Lk.new(bs.outputs[0], out.inputs[0])
    tc = N.new("ShaderNodeTexCoord")
    a_len = N.new("ShaderNodeAttribute"); a_len.attribute_type = "OBJECT"; a_len.attribute_name = "g_len"
    a_acr = N.new("ShaderNodeAttribute"); a_acr.attribute_type = "OBJECT"; a_acr.attribute_name = "g_across"
    a_ctr = N.new("ShaderNodeAttribute"); a_ctr.attribute_type = "OBJECT"; a_ctr.attribute_name = "g_centre"
    a_fin = N.new("ShaderNodeAttribute"); a_fin.attribute_type = "OBJECT"; a_fin.attribute_name = "finish"
    rel = N.new("ShaderNodeVectorMath"); rel.operation = "SUBTRACT"
    Lk.new(tc.outputs["Object"], rel.inputs[0]); Lk.new(a_ctr.outputs["Vector"], rel.inputs[1])
    dl = N.new("ShaderNodeVectorMath"); dl.operation = "DOT_PRODUCT"
    Lk.new(rel.outputs[0], dl.inputs[0]); Lk.new(a_len.outputs["Vector"], dl.inputs[1])
    da = N.new("ShaderNodeVectorMath"); da.operation = "DOT_PRODUCT"
    Lk.new(rel.outputs[0], da.inputs[0]); Lk.new(a_acr.outputs["Vector"], da.inputs[1])
    # band coordinate: straight grain = across distance; cathedral = |x| + k * l * exp(-(x/s)^2)
    if figure == "cathedral":
        ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; Lk.new(da.outputs["Value"], ab.inputs[0])
        sq = N.new("ShaderNodeMath"); sq.operation = "DIVIDE"; Lk.new(da.outputs["Value"], sq.inputs[0]); sq.inputs[1].default_value = 0.05
        p2 = N.new("ShaderNodeMath"); p2.operation = "POWER"; Lk.new(sq.outputs[0], p2.inputs[0]); p2.inputs[1].default_value = 2.0
        ng = N.new("ShaderNodeMath"); ng.operation = "MULTIPLY"; Lk.new(p2.outputs[0], ng.inputs[0]); ng.inputs[1].default_value = -1.0
        ex = N.new("ShaderNodeMath"); ex.operation = "EXPONENT"; Lk.new(ng.outputs[0], ex.inputs[0])
        ml = N.new("ShaderNodeMath"); ml.operation = "MULTIPLY"; Lk.new(ex.outputs[0], ml.inputs[0]); Lk.new(dl.outputs["Value"], ml.inputs[1])
        ml2 = N.new("ShaderNodeMath"); ml2.operation = "MULTIPLY"; Lk.new(ml.outputs[0], ml2.inputs[0]); ml2.inputs[1].default_value = 0.35
        band = N.new("ShaderNodeMath"); band.operation = "ADD"; Lk.new(ab.outputs[0], band.inputs[0]); Lk.new(ml2.outputs[0], band.inputs[1])
        bandv = band.outputs[0]
    else:
        bandv = da.outputs["Value"]
    cmb = N.new("ShaderNodeCombineXYZ")
    sc1 = N.new("ShaderNodeMath"); sc1.operation = "MULTIPLY"; sc1.inputs[1].default_value = 1.0
    Lk.new(bandv, sc1.inputs[0]); Lk.new(sc1.outputs[0], cmb.inputs[0])
    sc2 = N.new("ShaderNodeMath"); sc2.operation = "MULTIPLY"; sc2.inputs[1].default_value = 0.04
    Lk.new(dl.outputs["Value"], sc2.inputs[0]); Lk.new(sc2.outputs[0], cmb.inputs[1])
    wave = N.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 45.0; wave.inputs["Distortion"].default_value = 5.0
    wave.inputs["Detail"].default_value = 3.0; wave.inputs["Detail Scale"].default_value = 1.2
    Lk.new(cmb.outputs[0], wave.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 60.0
    Lk.new(cmb.outputs[0], noise.inputs["Vector"])
    mixg = N.new("ShaderNodeMix"); mixg.data_type = "FLOAT"; mixg.inputs["Factor"].default_value = 0.35
    Lk.new(wave.outputs["Fac"], mixg.inputs["A"]); Lk.new(noise.outputs["Fac"], mixg.inputs["B"])
    ramp = N.new("ShaderNodeValToRGB")
    lr, lf = srgb_to_lin(raw), srgb_to_lin(fin)
    # raw colour ramp, then a finished one, mixed by the per-object finish value
    ramp.color_ramp.elements[0].color = (*[x * 0.6 for x in lr], 1)
    ramp.color_ramp.elements[1].color = (*lr, 1)
    Lk.new(mixg.outputs[0], ramp.inputs[0])
    ramp2 = N.new("ShaderNodeValToRGB")
    ramp2.color_ramp.elements[0].color = (*[x * (0.55 if finish_kind != "char" else 0.8) for x in lf], 1)
    ramp2.color_ramp.elements[1].color = (*lf, 1)
    Lk.new(mixg.outputs[0], ramp2.inputs[0])
    mixc = N.new("ShaderNodeMix"); mixc.data_type = "RGBA"
    Lk.new(a_fin.outputs["Fac"], mixc.inputs["Factor"]); Lk.new(ramp.outputs[0], mixc.inputs[6]); Lk.new(ramp2.outputs[0], mixc.inputs[7])
    Lk.new(mixc.outputs[2], bs.inputs["Base Color"])
    rough = N.new("ShaderNodeMapRange"); rough.inputs[3].default_value = 0.65; rough.inputs[4].default_value = 0.72 if finish_kind == "char" else 0.45
    Lk.new(a_fin.outputs["Fac"], rough.inputs[0]); Lk.new(rough.outputs[0], bs.inputs["Roughness"])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.04
    Lk.new(wave.outputs["Fac"], bump.inputs["Height"]); Lk.new(bump.outputs[0], bs.inputs["Normal"])
    return m


def metal_material(kind="steel"):
    key = f"METAL_{kind}"
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    col = {"brass": (0.72, 0.52, 0.22), "steel": (0.55, 0.56, 0.57), "blacksteel": (0.06, 0.06, 0.065)}.get(kind, (0.55, 0.56, 0.57))
    bs.inputs["Base Color"].default_value = (*srgb_to_lin(col), 1)
    bs.inputs["Metallic"].default_value = 1.0
    bs.inputs["Roughness"].default_value = 0.38
    return m


def assign(obs, look):
    """look: {"species": "walnut", "finish": "oil|char", "parts": {"REGEX": {"species", "figure", "finish", "metal"}}}"""
    for o in obs:
        sp, fig, fk, metal = look.get("species", "walnut"), "straight", look.get("finish", "oil"), None
        if HARDWARE.search(o.name):
            metal = "brass" if re.search("brass|hinge", o.name, re.I) else "steel"
        if re.search(r"ply|bottom", o.name, re.I) and "species_ply" in look:
            sp = look["species_ply"]
        for rx, v in look.get("parts", {}).items():
            if re.search(rx, o.name):
                sp, fig, fk, metal = v.get("species", sp), v.get("figure", fig), v.get("finish", fk), v.get("metal", metal)
        o.data.materials.clear()
        if metal:
            o.data.materials.append(metal_material(metal))
        else:
            o.data.materials.append(wood_material("m", sp, fig, fk))
        L, W, T, c = obb_axes(o)
        inv = o.matrix_world.inverted().to_3x3()
        o["g_len"] = list((inv @ L).normalized())
        o["g_across"] = list((inv @ W).normalized())
        o["g_centre"] = list(o.matrix_world.inverted() @ c)
        o["finish"] = 0.0


def bounds(obs):
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in obs:
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return lo, hi


def stage(obs, up="Z"):
    """White world, soft key + fill, shadow-catcher floor under the piece."""
    s = bpy.context.scene
    w = bpy.data.worlds.new("white"); s.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 0.35
    lo, hi = bounds(obs); size = (hi - lo).length; ctr = (lo + hi) / 2
    bpy.ops.mesh.primitive_plane_add(size=size * 8, location=(ctr.x, ctr.y, lo.z))
    fl = bpy.context.active_object; fl.name = "ShadowCatcher"; fl.is_shadow_catcher = True
    for nm, loc, energy, sz in (("Key", (-0.8, -1.0, 1.6), 90, 1.2), ("Fill", (1.2, -0.6, 0.9), 25, 2.0), ("Rim", (0.4, 1.4, 1.3), 40, 1.0)):
        d = bpy.data.lights.new(nm, "AREA"); d.energy = energy * size ** 2; d.size = sz * size
        L = bpy.data.objects.new(nm, d); s.collection.objects.link(L)
        L.location = ctr + Vector(loc) * size
        L.rotation_euler = (ctr - L.location).to_track_quat("-Z", "Y").to_euler()
    s.render.film_transparent = True     # only so the shadow catcher works; finish_white() flattens onto white
    return ctr, size


def camera(obs, azimuth=35.0, elevation=18.0, lens=70.0, margin=1.12, aspect=(16, 9), name="Cam"):
    s = bpy.context.scene
    lo, hi = bounds(obs); ctr = (lo + hi) / 2; rad = (hi - lo).length / 2
    cd = bpy.data.cameras.new(name); cd.lens = lens
    cam = bpy.data.objects.new(name, cd); s.collection.objects.link(cam); s.camera = cam
    s.render.resolution_x, s.render.resolution_y = (1920, 1080) if aspect == (16, 9) else (1080, 1920) if aspect == (9, 16) else aspect
    fov = 2 * math.atan(18 / lens) if aspect[0] >= aspect[1] else 2 * math.atan(18 / lens * aspect[0] / aspect[1])
    dist = rad * margin / math.sin(fov / 2)
    az, el = math.radians(azimuth), math.radians(elevation)
    cam.location = ctr + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam["target"] = list(ctr); cam["dist"] = dist
    return cam


def finish_white(png_in, jpg_out, quality=92):
    """Flatten an RGBA render onto pure white (255) and save a JPG. Never ship the transparent PNG."""
    from PIL import Image
    im = Image.open(png_in).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    Image.alpha_composite(bg, im).convert("RGB").save(jpg_out, quality=quality)


def quality(samples=64, denoise=True, device="CPU"):
    s = bpy.context.scene
    s.cycles.samples = samples
    s.cycles.use_denoising = denoise
    s.cycles.device = device

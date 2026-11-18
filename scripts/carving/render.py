import os
# blender -b -P render.py -- scene.json out.png
import bpy, json, sys, math, mathutils
argv = sys.argv[sys.argv.index('--')+1:]
sc = json.load(open(argv[0])); outp = argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
scene.cycles.samples = sc.get('samples', 64); scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = sc.get('res', [1000, 750])
scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = sc.get('look', 'AgX - Medium High Contrast')
scene.view_settings.exposure = sc.get('exposure', 0)

def nodes_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; [nt.nodes.remove(n) for n in list(nt.nodes)]
    out = nt.nodes.new('ShaderNodeOutputMaterial'); return m, nt, out

def walnut(name, dark=1.0, rough=0.32, ringscale=40.0, axis='X', carved=False):
    m, nt, out = nodes_mat(name); N = nt.nodes; Lk = nt.links.new
    bsdf = N.new('ShaderNodeBsdfPrincipled'); Lk(bsdf.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    Lk(tc.outputs['Object'], mp.inputs[0])
    # stretch along grain axis
    s = {'X': (0.08, 1, 1), 'Y': (1, 0.08, 1), 'Z': (1, 1, 0.08)}[axis]
    mp.inputs['Scale'].default_value = s
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; nz.inputs['Detail'].default_value = 6
    Lk(mp.outputs[0], nz.inputs[0])
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.inputs['Scale'].default_value = ringscale
    wv.inputs['Distortion'].default_value = 10; wv.inputs['Detail'].default_value = 3
    mix = N.new('ShaderNodeMix'); mix.data_type = 'VECTOR'; mix.inputs[0].default_value = 0.15
    Lk(mp.outputs[0], mix.inputs[4]); Lk(nz.outputs['Color'], mix.inputs[5]); Lk(mix.outputs[1], wv.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); Lk(wv.outputs['Fac'], ramp.inputs[0])
    c1 = [0.058*dark, 0.025*dark, 0.012*dark, 1]; c2 = [0.080*dark, 0.036*dark, 0.018*dark, 1]
    ramp.color_ramp.elements[0].color = c1; ramp.color_ramp.elements[1].color = c2
    ramp.color_ramp.elements[0].position = 0.25; ramp.color_ramp.elements[1].position = 0.85
    # large scale tone variation
    nz2 = N.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 1.2; Lk(tc.outputs['Object'], nz2.inputs[0])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 0.35
    Lk(ramp.outputs[0], mul.inputs[6]); Lk(nz2.outputs['Color'], mul.inputs[7])
    col = mul.outputs[2]
    if carved:
        geo = N.new('ShaderNodeNewGeometry'); pr = N.new('ShaderNodeMapRange')
        Lk(geo.outputs['Pointiness'], pr.inputs[0]); pr.inputs[1].default_value = 0.48; pr.inputs[2].default_value = 0.53
        pr.inputs[3].default_value = 0.8; pr.inputs[4].default_value = 1.6
        hm = N.new('ShaderNodeMix'); hm.data_type = 'RGBA'; hm.blend_type = 'MULTIPLY'; hm.inputs[0].default_value = 1
        Lk(col, hm.inputs[6]); Lk(pr.outputs[0], hm.inputs[7]); col = hm.outputs[2]
        # cavities darker: ambient occlusion
        ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.02
        mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs[0].default_value = 1
        aor = N.new('ShaderNodeMapRange'); Lk(ao.outputs['AO'], aor.inputs[0]); aor.inputs[3].default_value = 0.35
        Lk(col, mm.inputs[6]); Lk(aor.outputs[0], mm.inputs[7]); col = mm.outputs[2]
    Lk(col, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Specular IOR Level'].default_value = 0.55
    bsdf.inputs['Coat Weight'].default_value = sc.get('coat', 0.12); bsdf.inputs['Coat Roughness'].default_value = 0.12
    bmp = N.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.05; bmp.inputs['Distance'].default_value = 0.001
    Lk(wv.outputs['Fac'], bmp.inputs['Height']); Lk(bmp.outputs[0], bsdf.inputs['Normal'])
    return m

def simple(name, rgb, rough=0.6, spec=0.5, coat=0):
    m, nt, out = nodes_mat(name); b = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs['Base Color'].default_value = list(rgb) + [1]; b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = spec; b.inputs['Coat Weight'].default_value = coat
    return m

def floor_mat(name, rgb, strip=0.057, coat=0.6):
    m, nt, out = nodes_mat(name); N = nt.nodes; Lk = nt.links.new
    b = N.new('ShaderNodeBsdfPrincipled'); Lk(b.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); br = N.new('ShaderNodeTexBrick')
    br.inputs['Scale'].default_value = 1.0; br.inputs['Brick Width'].default_value = 0.6; br.inputs['Row Height'].default_value = strip
    br.inputs['Mortar Size'].default_value = 0.0008; br.offset = 0.37
    c = rgb; br.inputs['Color1'].default_value = list(c)+[1]; br.inputs['Color2'].default_value = [c[0]*0.8, c[1]*0.8, c[2]*0.8, 1]
    br.inputs['Mortar'].default_value = [c[0]*0.4, c[1]*0.4, c[2]*0.4, 1]
    Lk(tc.outputs['Object'], br.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9; nz.inputs['Detail'].default_value = 8
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.15, 3.0, 1); Lk(tc.outputs['Object'], mp.inputs[0]); Lk(mp.outputs[0], nz.inputs[0])
    mr = N.new('ShaderNodeMapRange'); Lk(nz.outputs['Fac'], mr.inputs[0]); mr.inputs[3].default_value = 0.6; mr.inputs[4].default_value = 1.35
    mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs[0].default_value = 1
    Lk(br.outputs['Color'], mm.inputs[6]); Lk(mr.outputs[0], mm.inputs[7]); Lk(mm.outputs[2], b.inputs['Base Color'])
    rr_ = N.new('ShaderNodeMapRange'); Lk(nz.outputs['Fac'], rr_.inputs[0]); rr_.inputs[3].default_value = 0.3; rr_.inputs[4].default_value = 0.65
    Lk(rr_.outputs[0], b.inputs['Roughness'])
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.05
    return m

MATS = {}
def getmat(spec):
    key = json.dumps(spec, sort_keys=True)
    if key in MATS: return MATS[key]
    t = spec['type']
    if t == 'walnut': m = walnut('walnut', spec.get('dark', 1), spec.get('rough', 0.32), spec.get('rings', 40), spec.get('axis', 'X'), spec.get('carved', False))
    elif t == 'floor': m = floor_mat('floor', spec['rgb'], coat=spec.get('coat', 0.6))
    else: m = simple('m', spec['rgb'], spec.get('rough', 0.6), spec.get('spec', 0.5), spec.get('coat', 0))
    MATS[key] = m; return m

for o in sc['objects']:
    if 'ply' in o:
        bpy.ops.wm.ply_import(filepath=o['ply']); ob = bpy.context.selected_objects[0]
        if sc.get('decimate'):
            f = len(ob.data.polygons); tgt = sc['decimate'] * (3 if 'log' in o['ply'] else 1 if any(k in o['ply'] for k in ('arch', 'knob', 'throne', 'slab', 'blockA')) else 0.3)
            if f > tgt:
                md = ob.modifiers.new('dec', 'DECIMATE'); md.ratio = tgt / f
                bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='dec')
            ob.name = os.path.splitext(os.path.basename(o['ply']))[0]
        if o.get('smooth', True): bpy.ops.object.shade_smooth()
    elif o.get('prim') == 'plane':
        bpy.ops.mesh.primitive_plane_add(size=o.get('size', 20)); ob = bpy.context.object
    ob.location = o.get('loc', [0, 0, 0]); ob.rotation_euler = [math.radians(a) for a in o.get('rot', [0, 0, 0])]
    ob.scale = [o.get('scale', 1)]*3 if not isinstance(o.get('scale', 1), list) else o['scale']
    ob.data.materials.append(getmat(o['mat']))

# lighting
w = bpy.data.worlds.new('w'); scene.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = sc.get('world', [0.8, 0.82, 0.85, 1]); bg.inputs[1].default_value = sc.get('world_strength', 1.0)
for L in sc.get('lights', []):
    ld = bpy.data.lights.new('l', L['type']); ld.energy = L['energy']
    if L['type'] == 'AREA': ld.size = L.get('size', 2)
    if L['type'] == 'SUN': ld.angle = math.radians(L.get('angle', 5))
    lo = bpy.data.objects.new('l', ld); scene.collection.objects.link(lo); lo.location = L['loc']
    d = mathutils.Vector(L.get('target', [0, 0, 0])) - mathutils.Vector(L['loc'])
    lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cd = bpy.data.cameras.new('c'); cd.lens = sc['cam'].get('lens', 26); cd.sensor_width = sc['cam'].get('sensor', 36)
cam = bpy.data.objects.new('c', cd); scene.collection.objects.link(cam); scene.camera = cam
cam.location = sc['cam']['loc']
if 'quat' in sc['cam']:
    cam.rotation_mode = 'QUATERNION'; cam.rotation_quaternion = sc['cam']['quat']
else:
    d = mathutils.Vector(sc['cam']['target']) - mathutils.Vector(sc['cam']['loc'])
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = outp
if sc.get('save_blend'): bpy.ops.wm.save_as_mainfile(filepath=sc['save_blend'], compress=True)
if not sc.get('no_render'): bpy.ops.render.render(write_still=True)

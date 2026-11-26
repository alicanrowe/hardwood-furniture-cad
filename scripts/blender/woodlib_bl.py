"""woodlib for Blender: the library's wood (scripts/woodlib.py + references/woods.json) as one Cycles/EEVEE node
material per species and finish. Same maths as woodlib.color() (rings from a pith line in each part's own frame,
flat / quarter / rift cuts, sapwood beyond the heart radius, end grain from the same rings, pores, streaks, ray
fleck), built from plain nodes (no OSL, so it runs in pip bpy and on the tower).

Never build a wood node tree in a project script. Do this instead:

    import sys; sys.path.insert(0, '<skill>/scripts'); sys.path.insert(0, '<skill>/scripts/blender')
    import woodlib_bl as WB
    WB.apply(obj, 'walnut', cut='flat', seed=4)              # one part; cut auto|flat|quarter|rift; grain='x'|'y'|'z'|vector
    WB.apply_all(objs, look)                                  # look.py-style dict: {"species", "finish", "parts": {REGEX: {...}}}
    WB.house(studio='card')                                   # optional: the studio gain woodlib_calibrate.py measured

Each material carries mat["woodlib"] = woodlib.stamp(...) and each part obj["woodlib_board"] = the board JSON, so
woodlib_lint.py / the site gate can tell library wood from a local shader, and a GLB baked from the scene
(web_glb.py) gets the same boards.
"""
import json, math, os, re, sys
import bpy, mathutils
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import woodlib as W  # noqa: E402

M_PER_IN = 0.0254


class _G:
    """Tiny node-expression builder: every op returns an output socket."""

    def __init__(s, nt):
        s.nt, s.N, s.L = nt, nt.nodes, nt.links

    def _in(s, sock, v):
        if isinstance(v, (int, float)): sock.default_value = v
        else: s.L.new(v, sock)

    def m(s, op, a, b=0.0, c=None):
        n = s.N.new('ShaderNodeMath'); n.operation = op
        s._in(n.inputs[0], a); s._in(n.inputs[1], b)
        if c is not None: s._in(n.inputs[2], c)
        return n.outputs[0]

    def add(s, *xs):
        o = xs[0]
        for x in xs[1:]: o = s.m('ADD', o, x)
        return o

    def mul(s, a, b): return s.m('MULTIPLY', a, b)

    def sub(s, a, b): return s.m('SUBTRACT', a, b)

    def attr(s, name):
        n = s.N.new('ShaderNodeAttribute'); n.attribute_type = 'OBJECT'; n.attribute_name = name
        return n.outputs['Vector']

    def sep(s, v):
        n = s.N.new('ShaderNodeSeparateXYZ'); s.L.new(v, n.inputs[0]); return n.outputs[0], n.outputs[1], n.outputs[2]

    def comb(s, x, y, z):
        n = s.N.new('ShaderNodeCombineXYZ'); s._in(n.inputs[0], x); s._in(n.inputs[1], y); s._in(n.inputs[2], z)
        return n.outputs[0]

    def vm(s, op, a, b=None):
        n = s.N.new('ShaderNodeVectorMath'); n.operation = op; s.L.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, (tuple, list)): n.inputs[1].default_value = b
            else: s.L.new(b, n.inputs[1])
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']

    def noise(s, x, y, z):
        """Signed Perlin, about -1..1 (Blender noise, no fBm)."""
        n = s.N.new('ShaderNodeTexNoise'); n.noise_dimensions = '3D'
        n.inputs['Scale'].default_value = 1.0; n.inputs['Detail'].default_value = 0.0
        if 'Normalize' in n: n.normalize = True
        s.L.new(s.comb(x, y, z), n.inputs['Vector'])
        return s.mul(s.sub(n.outputs["Fac"], 0.5), 2.0)

    def smooth(s, a, b, x):
        n = s.N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        s._in(n.inputs['Value'], x); n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
        return n.outputs['Result']

    def rgb(s, c):
        n = s.N.new('ShaderNodeRGB'); n.outputs[0].default_value = (*[float(x) for x in c], 1.0); return n.outputs[0]

    def mix(s, fac, a, b):
        n = s.N.new('ShaderNodeMix'); n.data_type = 'RGBA'; s._in(n.inputs['Factor'], fac)
        s.L.new(a, n.inputs[6]); s.L.new(b, n.inputs[7]); return n.outputs[2]

    def cmul(s, c, f):
        n = s.N.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MULTIPLY'; n.inputs['Factor'].default_value = 1.0
        s.L.new(c, n.inputs[6])
        if isinstance(f, (int, float)): n.inputs[7].default_value = (f, f, f, 1)
        else: s.L.new(s.comb(f, f, f), n.inputs[7])
        return n.outputs[2]


def material(sp='walnut', finish='oil', studio=None, animated=False):
    """The library material for a species + finish (shared by every part; the board lives on the object)."""
    sk, S = W.species(sp)
    key = f'woodlib {sk} {finish}' + (f' [{studio}]' if studio else '') + (' animated' if animated else '')
    if key in bpy.data.materials: return bpy.data.materials[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); G = _G(nt)
    out = G.N.new('ShaderNodeOutputMaterial'); bs = G.N.new('ShaderNodeBsdfPrincipled')
    G.L.new(bs.outputs[0], out.inputs[0])
    for k in ('Coat Weight', 'Sheen Weight'):
        if k in bs.inputs: bs.inputs[k].default_value = 0.0
    bs.inputs['Specular IOR Level'].default_value = S['specular']
    bs.inputs['Roughness'].default_value = W.roughness(sk, finish)
    tc = G.N.new('ShaderNodeTexCoord')
    A = G.attr('wl_a')                       # (inches per object unit, u0, seed)
    k_, u0, seed = G.sep(A)
    p0, p1, rh = G.sep(G.attr('wl_p'))
    t0, t1, _ = G.sep(G.attr('wl_t'))
    Pin = G.vm('SCALE', tc.outputs['Object']) if False else None
    sc = G.N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; G.L.new(tc.outputs['Object'], sc.inputs[0]); G.L.new(k_, sc.inputs['Scale'])
    Q = G.vm('SUBTRACT', sc.outputs['Vector'], G.attr('wl_o'))
    g = G.vm('DOT_PRODUCT', Q, G.attr('wl_u')); a = G.vm('DOT_PRODUCT', Q, G.attr('wl_v')); b = G.vm('DOT_PRODUCT', Q, G.attr('wl_w'))
    gu = G.sub(g, u0)
    dv = G.sub(a, G.add(p0, G.mul(t0, gu))); dw = G.sub(b, G.add(p1, G.mul(t1, gu)))
    r = G.m('SQRT', G.add(G.mul(dv, dv), G.mul(dw, dw)))
    th = G.m('ARCTAN2', dw, dv)
    wa = S.get('wander', 1.0)
    rw = G.add(r, G.mul(0.20 * wa, G.noise(G.add(G.mul(g, 0.035), G.mul(seed, 7.1)), G.mul(th, 1.3), G.mul(r, 0.12))),
               G.mul(0.07 * wa, G.noise(G.mul(g, 0.11), G.add(G.mul(th, 4.0), seed), G.mul(r, 0.4))),
               G.mul(S.get('ring_jag', 0.015), G.noise(G.mul(g, 0.6), G.mul(th, 20.0), G.mul(r, 2.0))))
    rpi = S['rings_per_in']
    ring0 = G.mul(rw, rpi)
    ring = G.add(ring0, G.mul(0.45, G.noise(G.mul(ring0, 0.23), G.mul(th, 0.6), G.mul(seed, 0.37))),
                 G.mul(0.12, G.noise(G.mul(ring0, 0.9), G.mul(th, 1.5), G.add(seed, 5.0))))
    f = G.m('FRACT', ring)
    lf, ls = S['late_frac'], S['late_soft']
    edge = G.sub(1.0, G.smooth(0.975, 1.0, f))
    late_l = G.mul(G.m('POWER', G.smooth(1 - lf - ls, 1 - 0.25 * lf, f), 1.3), edge)
    late_e = G.mul(G.smooth(1 - lf - 0.3 * ls, 1 - lf + 0.1 * ls, f), G.sub(1.0, G.smooth(0.985, 1.0, f)))
    geo = G.N.new('ShaderNodeNewGeometry')
    vt = G.N.new('ShaderNodeVectorTransform'); vt.vector_type = 'NORMAL'; vt.convert_from = 'WORLD'; vt.convert_to = 'OBJECT'
    G.L.new(geo.outputs['Normal'], vt.inputs[0])
    nrm = G.vm('NORMALIZE', vt.outputs[0])
    e = G.smooth(0.55, 0.92, G.m('ABSOLUTE', G.vm('DOT_PRODUCT', nrm, G.attr('wl_u'))))
    late = G.add(G.mul(late_l, G.sub(1.0, e)), G.mul(late_e, e))
    rb = S.get('ring_break', 0.45)
    late = G.mul(late, G.add(1 - rb, G.mul(rb, G.smooth(-0.4, 0.5, G.noise(G.add(G.mul(G.m('FLOOR', ring), 0.37), seed), G.mul(g, S.get('ring_fade', 0.0)), G.mul(th, 0.3))))))
    asf = S.get('apex_soft', 0.0)
    if asf > 0:   # soft flat-sawn apex (woodlib.color)
        tg = G.m('ABSOLUTE', G.add(G.mul(G.m('COSINE', th), G.vm('DOT_PRODUCT', nrm, G.attr('wl_v'))),
                                   G.mul(G.m('SINE', th), G.vm('DOT_PRODUCT', nrm, G.attr('wl_w')))))
        late = G.mul(late, G.sub(1.0, G.mul(G.mul(asf, G.smooth(0.9, 0.995, tg)), G.sub(1.0, e))))
    Al = S['albedo']
    col = G.mix(late, G.rgb(W.srgb2lin(Al['early'])), G.rgb(W.srgb2lin(Al['late'])))
    fib = G.add(1.0, G.mul(S.get('fibre', 0.07), G.noise(G.add(G.mul(g, 0.25), seed), G.mul(a, 9.0), G.mul(b, 9.0))),
                G.mul(0.09, G.noise(G.mul(g, 0.06), G.add(G.mul(a, 1.6), seed), G.mul(b, 1.6))))
    col = G.cmul(col, fib)
    # sapwood beyond the heart radius
    sm = G.smooth(-0.2, 0.25, G.sub(G.add(rw, G.mul(0.25, G.noise(G.add(G.mul(g, 0.05), 3.3), G.mul(th, 2.0), seed))), rh))
    sap = G.mix(late, G.rgb(W.srgb2lin(Al['sap'])), G.rgb(W.srgb2lin(Al['sap_late'])))
    col = G.mix(sm, col, sap)
    ps = S['pore_scale']
    pm = G.smooth(0.15, 0.6, G.noise(G.add(G.mul(g, 0.9 / ps), seed), G.mul(a, 22 / ps), G.mul(b, 22 / ps)))
    if S['porosity'] == 'ring': zone = G.sub(1.0, G.smooth(0.0, 0.22, f))
    elif S['porosity'] == 'semi': zone = G.add(0.55, G.mul(0.45, G.sub(1.0, G.smooth(0.0, 0.4, f))))
    else: zone = 0.5
    pore = G.sub(1.0, G.mul(G.mul(G.mul(S['pores'], zone), pm), G.sub(1.0, G.mul(0.5, e))))
    st = G.add(1.0, G.mul(S['streak'], G.noise(G.add(G.mul(g, 0.025), seed), G.mul(a, 0.7), G.mul(b, 0.7))),
               G.mul(S.get('streak_fine', 0.0), G.noise(G.add(G.mul(g, 0.04), G.mul(seed, 2.0)), G.mul(a, 3.2), G.mul(b, 3.2))))
    # one tone per board: +-board_tone from the seed (a hash, like woodlib.h1)
    bt = G.add(1.0, G.mul(S['board_tone'] * 2, G.sub(G.m('FRACT', G.mul(G.m('SINE', G.mul(seed, 12.9898)), 43758.5453)), 0.5)))
    shade = G.mul(G.mul(G.mul(pore, st), bt), G.sub(1.0, G.mul(S['end_dark'], e)))
    col = G.cmul(col, shade)
    if S.get('rays', 0) > 0:
        tang = G.m('ABSOLUTE', G.add(G.mul(G.vm('DOT_PRODUCT', nrm, G.attr('wl_v')), G.mul(-1.0, G.m('SINE', th))),
                                     G.mul(G.vm('DOT_PRODUCT', nrm, G.attr('wl_w')), G.m('COSINE', th))))
        fl = G.mul(G.mul(G.smooth(0.45, 0.7, G.noise(G.add(G.mul(g, 1.1), seed), G.mul(th, 140.0), G.mul(rw, 0.9))),
                         G.smooth(0.6, 0.95, tang)), G.sub(1.0, e))
        col = G.cmul(col, G.add(1.0, G.mul(S['rays'] * 0.45, fl)))
    fz = W.LIB['finishes'].get(finish, {})
    fr = W.LIB['finishes']['raw']

    def raw_of(c):
        hs = G.N.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 1 - fr.get('desat', 0.25)
        hs.inputs['Value'].default_value = fr.get('albedo_gain', 1.12); G.L.new(c, hs.inputs['Color']); return hs.outputs['Color']
    oiled = col
    if finish == 'char':
        col = G.cmul(G.rgb(W.srgb2lin(fz['albedo'])), G.add(0.85, G.mul(0.15, pm)))
    elif finish == 'raw':
        col = raw_of(col)
    if animated:      # per-object "finish" 0..1: raw wood until the finishing step (look.py / animate_build.py)
        af = G.N.new('ShaderNodeAttribute'); af.attribute_type = 'OBJECT'; af.attribute_name = 'finish'
        col = G.mix(af.outputs['Fac'], raw_of(oiled), col)
        rr = G.N.new('ShaderNodeMapRange'); G.L.new(af.outputs['Fac'], rr.inputs['Value'])
        rr.inputs['To Min'].default_value = W.roughness(sk, 'raw'); rr.inputs['To Max'].default_value = W.roughness(sk, finish)
        G.L.new(rr.outputs['Result'], bs.inputs['Roughness'])
    if studio:
        gn = G.N.new('ShaderNodeMix'); gn.data_type = 'RGBA'; gn.blend_type = 'MULTIPLY'; gn.inputs['Factor'].default_value = 1.0
        G.L.new(col, gn.inputs[6]); gn.inputs[7].default_value = (*W.house_gain(sk, studio), 1.0); col = gn.outputs[2]
    G.L.new(col, bs.inputs['Base Color'])
    bump = G.N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08 if finish != 'char' else 0.4
    bump.inputs['Distance'].default_value = 0.00015
    G.L.new(G.add(G.mul(late, 0.6), G.mul(G.sub(1.0, pore), 2.0)), bump.inputs['Height']); G.L.new(bump.outputs[0], bs.inputs['Normal'])
    m['woodlib'] = W.stamp(sk, 'board', finish)
    return m


def _obj_points_in(o, units_in):
    """Object-space vertex positions in inches (units_in = inches per object unit)."""
    return np.array([v.co[:] for v in o.data.vertices]) * units_in


def apply(o, sp='walnut', cut='auto', seed=None, grain=None, finish='oil', sap=None, units='m', studio=None, animated=False):
    """Give one part the library wood. grain is in the object's own axes (or None = longest side)."""
    k = {'m': 1 / M_PER_IN, 'mm': 1 / 25.4, 'in': 1.0}[units] if isinstance(units, str) else float(units)
    k *= max(o.scale)      # object scale: the board is measured in world inches
    P = _obj_points_in(o, k)
    if seed is None: seed = sum(map(ord, o.name)) % 997
    up = o.matrix_world.to_3x3().inverted() @ mathutils.Vector((0, 0, 1))      # world up in the object's axes
    lam = W.board(P, grain=grain, cut=cut, species_name=sp, seed=seed, sap=sap, finish=finish, name=o.name, up=tuple(up.normalized()))
    _write(o, lam, k)
    mat = material(sp, finish, studio, animated)
    if o.data.materials:
        for i in range(len(o.data.materials)): o.data.materials[i] = mat
    else: o.data.materials.append(mat)
    return lam


def _write(o, lam, k):
    o['wl_a'] = [k, lam['u0'], float(lam['seed'])]
    o['wl_o'] = lam['origin']; o['wl_u'] = lam['u']; o['wl_v'] = lam['v']; o['wl_w'] = lam['w']
    o['wl_p'] = [lam['pith'][0], lam['pith'][1], lam['rh']]; o['wl_t'] = [lam['tilt'][0], lam['tilt'][1], 0.0]
    o['woodlib_board'] = json.dumps(lam)


def bookmatch(oa, ob):
    """Give part ob part oa's board mirrored across the joint between them (a bookmatched pair, e.g. Door_Board_L/R).
    Both must already have library wood (apply). Works in world space, so the two objects may have any transforms."""
    la = json.loads(oa['woodlib_board']); ka, kb = oa['wl_a'][0], ob['wl_a'][0]
    Ma, Mb = oa.matrix_world, ob.matrix_world; Ra, Rb = Ma.to_3x3(), Mb.to_3x3()
    V = mathutils.Vector
    to_w = dict(la)
    to_w['origin'] = list(Ma @ (V(la['origin']) / ka)); kw = ka / max(oa.scale)      # world units -> inches
    for x in ('u', 'v', 'w'): to_w[x] = list((Ra @ V(la[x])).normalized())
    to_w['origin'] = [c * kw for c in to_w['origin']]
    PA = np.array([list(Ma @ v.co) for v in oa.data.vertices]) * kw
    PB = np.array([list(Mb @ v.co) for v in ob.data.vertices]) * kw
    lw = W.bookmatch(to_w, PA, PB, name=ob.name)
    if lw is None: return None
    lb = dict(lw); Rbi = Rb.inverted()
    lb['origin'] = list(Mb.inverted() @ (V(lw['origin']) / kw) * kb)
    for x in ('u', 'v', 'w'): lb[x] = list((Rbi @ V(lw[x])).normalized())
    _write(ob, lb, kb)
    return lb


HARDWARE = re.compile(r"(screw|bolt|hinge|steel|brass|bronze|stainless|iron|sheet|plate|pin\b|_pin|knob|pull|glass|leaf|grille)", re.I)


def apply_all(obs, look, units='m', studio=None):
    """look: {"species": "walnut", "finish": "oil|char|raw", "cut": "auto", "parts": {REGEX: {species, cut, grain, finish, sap, skip}}}.
    Parts matching HARDWARE (or with "skip") are left alone. Returns {name: board}."""
    out = {}
    for o in obs:
        if o.type != 'MESH': continue
        d = dict(species=look.get('species', 'walnut'), cut=look.get('cut', 'auto'), finish=look.get('finish', 'oil'))
        for rx, v in look.get('parts', {}).items():
            if re.search(rx, o.name): d.update(v)
        if d.get('skip') or (HARDWARE.search(o.name) and 'species' not in look.get('parts', {}).get(o.name, {})):
            continue
        out[o.name] = apply(o, d['species'], d.get('cut', 'auto'), d.get('seed'), d.get('grain'), d.get('finish', 'oil'), d.get('sap'), units, studio)
    # bookmatch: ..._L / ..._R door leaves and panels are one board opened like a book (look "bookmatch": false to skip)
    if look.get('bookmatch', True):
        byname = {o.name: o for o in obs}
        for n in sorted(out):
            m = W.pair_name(n)
            if m and m in out and n < m and out[n].get('cut') == 'flat':
                out[m] = bookmatch(byname[n], byname[m]) or out[m]
    return out


def house_glb(mat, studio):
    """A material imported from a library GLB (extras "woodlib", which the glTF importer keeps as a custom property):
    set the library's specular and roughness and multiply the baked texture by the studio's calibrated gain.
    Returns True if it was library wood. Card loops and reels call this on every imported material."""
    st = W.parse_stamp(mat.get('woodlib')) if mat else None
    if not st or not mat.use_nodes: return False
    sk, S = W.species(st[0])
    nt = mat.node_tree; bs = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs is None: return False
    bs.inputs['Specular IOR Level'].default_value = S['specular']
    bs.inputs['Roughness'].default_value = W.roughness(sk, st[2])
    if mat.get('woodlib_house') == studio: return True
    lk = bs.inputs['Base Color'].links
    if lk:
        src = lk[0].from_socket; nt.links.remove(lk[0])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        nt.links.new(src, mx.inputs[6]); mx.inputs[7].default_value = (*W.house_gain(sk, studio), 1.0)
        nt.links.new(mx.outputs[2], bs.inputs['Base Color'])
    mat['woodlib_house'] = studio
    return True

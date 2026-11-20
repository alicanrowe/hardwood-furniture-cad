"""Gem colour check: every part named after a stone must carry that stone's colour from the project spec.
  python3 gemcheck.py MODEL.glb projects/moth.spec.json
  blender -b SCENE.blend -P gemcheck.py -- projects/moth.spec.json      (checks the render file itself)
Fails (exit 1) when a garnet/aquamarine/amethyst part's material is off-hue, washed out (too little saturation) or
too light/dark, e.g. a near-white 'clear glass' tint left on the lancet drops (v7e/v7f, e.g. the Moth v7f lancet drops).
Colour read: glTF baseColorFactor; in Blender the Principled Base Color, or its Transmission/volume colour if that is
what gives the stone its colour. A texture-driven colour is reported as 'unchecked'."""
import sys, json, re, colorsys
STONES = ('garnet', 'aquamarine', 'amethyst')
HUE_TOL, SAT_MIN, VAL_TOL = 20 / 360, 0.6, 0.25


def judge(stone, rgb, spec):
    h, s, v = colorsys.rgb_to_hsv(*rgb[:3]); H, S, V = colorsys.rgb_to_hsv(*spec[stone])
    dh = min(abs(h - H), 1 - abs(h - H))
    bad = []
    if dh > HUE_TOL: bad.append('hue off by %d deg' % round(dh * 360))
    if s < SAT_MIN * S: bad.append('washed out (saturation %.2f, spec %.2f)' % (s, S))
    if abs(v - V) > VAL_TOL: bad.append('value %.2f vs spec %.2f' % (v, V))
    return bad


def stone_of(name):
    m = re.search('|'.join(STONES), name, re.I)
    return m.group(0).lower() if m else None


def from_glb(path):
    import struct
    b = open(path, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
    mats = j.get('materials', []); out = []
    for nd in j.get('nodes', []):
        if 'mesh' not in nd: continue
        st = stone_of(nd.get('name', ''))
        if not st: continue
        for pr in j['meshes'][nd['mesh']]['primitives']:
            m = mats[pr['material']] if 'material' in pr else {'name': '(none)'}
            pb = m.get('pbrMetallicRoughness', {})
            col = None if 'baseColorTexture' in pb else pb.get('baseColorFactor', [1, 1, 1, 1])
            out.append((nd['name'], st, m.get('name'), col))
    return out


def from_blend():
    import bpy
    out = []
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        st = stone_of(o.name)
        if not st: continue
        for sl in o.material_slots:
            m = sl.material; col = None
            if m and m.node_tree:
                for nd in m.node_tree.nodes:
                    if nd.type == 'BSDF_PRINCIPLED':
                        sock = nd.inputs['Base Color']
                        tw = nd.inputs.get('Transmission Weight')
                        if tw is not None and tw.default_value > 0.5 and not sock.is_linked:
                            col = list(sock.default_value)   # transmissive: base colour tints the stone
                        elif not sock.is_linked: col = list(sock.default_value)
                        break
                    if nd.type in ('BSDF_GLASS', 'BSDF_REFRACTION') and not nd.inputs['Color'].is_linked:
                        col = list(nd.inputs['Color'].default_value); break
            out.append((o.name, st, m.name if m else '(none)', col))
    return out


def main(spec_path, rows):
    spec = json.load(open(spec_path))['materials']['gem']['colors']
    fails = unchecked = 0
    for name, st, mat, col in rows:
        if col is None: unchecked += 1; print('UNCHECKED', name, mat); continue
        bad = judge(st, col, spec)
        if bad: fails += 1; print('FAIL', name, st, mat, [round(c, 3) for c in col[:3]], '; '.join(bad))
    print('GEMCHECK parts', len(rows), 'fails', fails, 'unchecked', unchecked)
    return 1 if fails else 0


if __name__ == '__main__':
    if '--' in sys.argv:       # inside Blender
        a = sys.argv[sys.argv.index('--') + 1:]
        sys.exit(main(a[0], from_blend()))
    sys.exit(main(sys.argv[2], from_glb(sys.argv[1])))

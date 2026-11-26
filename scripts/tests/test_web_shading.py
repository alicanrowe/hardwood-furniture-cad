#!/usr/bin/env python3
"""Planted shading defects must fail web_shading_check.py, and web_reshade.py must fix them.

  python3 scripts/tests/test_web_shading.py        (needs numpy, scipy; npx for the compress step)
Builds small GLBs in a temp folder: a lid with normals averaged round its edges (the Moth case defect), the same lid
split right, a turned handle shaded flat, a coarse 16-sided handle, a panel with flipped normals, a mesh with no
normals, and a cut gem (meant to be faceted). Each defect must fail on the rule named, the good ones must pass, and
every reshaded copy must pass.
"""
import json, os, struct, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from web_shading_check import check_glb  # noqa: E402


def glb(path, V, F, N=None, mat='Black_French_Polish', clearcoat=True):
    V = np.asarray(V, np.float32); F = np.asarray(F, np.uint32)
    bins, views, accs = bytearray(), [], []
    def add(a, comp, typ, mm=False):
        while len(bins) % 4:
            bins.append(0)
        views.append({'buffer': 0, 'byteOffset': len(bins), 'byteLength': a.nbytes}); bins.extend(a.tobytes())
        acc = {'bufferView': len(views) - 1, 'componentType': comp, 'count': len(a), 'type': typ}
        if mm:
            acc['min'] = a.min(0).tolist(); acc['max'] = a.max(0).tolist()
        accs.append(acc); return len(accs) - 1
    attrs = {'POSITION': add(V, 5126, 'VEC3', True)}
    if N is not None:
        attrs['NORMAL'] = add(np.asarray(N, np.float32), 5126, 'VEC3')
    ind = add(F.ravel(), 5125, 'SCALAR')
    m = {'name': mat, 'pbrMetallicRoughness': {'baseColorFactor': [0.02, 0.02, 0.02, 1], 'metallicFactor': 0, 'roughnessFactor': 0.15}}
    if clearcoat:
        m['extensions'] = {'KHR_materials_clearcoat': {'clearcoatFactor': 1}}
    j = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0, 'name': 'part'}],
         'meshes': [{'primitives': [{'attributes': attrs, 'indices': ind, 'material': 0}]}], 'materials': [m],
         'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(bins)}]}
    if clearcoat:
        j['extensionsUsed'] = ['KHR_materials_clearcoat']
    js = json.dumps(j).encode(); js += b' ' * (-len(js) % 4); bins += b'\0' * (-len(bins) % 4)
    with open(path, 'wb') as fh:
        fh.write(struct.pack('<III', 0x46546C67, 2, 28 + len(js) + len(bins)))
        fh.write(struct.pack('<II', len(js), 0x4E4F534A)); fh.write(js)
        fh.write(struct.pack('<II', len(bins), 0x004E4942)); fh.write(bins)


def box(w=0.6, d=0.4, h=0.03, split=True):
    c = np.array([[x, y, z] for x in (-w / 2, w / 2) for y in (-d / 2, d / 2) for z in (0, h)])
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    if not split:   # 8 shared corners, normals averaged: the Moth lid
        F = [t for q in quads for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))]
        N = c - c.mean(0); N /= np.linalg.norm(N, axis=1, keepdims=True)
        return c, F, N
    V, F, N = [], [], []
    for q in quads:
        p = c[list(q)]; n = np.cross(p[1] - p[0], p[2] - p[0]); n /= np.linalg.norm(n)
        b = len(V); V += list(p); N += [n] * 4; F += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    return np.array(V), F, np.array(N)


def cyl(seg, smooth=True, r=0.015, L=0.12):
    V, F, N = [], [], []
    for i in range(seg):
        a0, a1 = 2 * np.pi * i / seg, 2 * np.pi * (i + 1) / seg
        p = [[r * np.cos(a0), r * np.sin(a0), 0], [r * np.cos(a1), r * np.sin(a1), 0],
             [r * np.cos(a1), r * np.sin(a1), L], [r * np.cos(a0), r * np.sin(a0), L]]
        if smooth:
            n = [[np.cos(a0), np.sin(a0), 0], [np.cos(a1), np.sin(a1), 0], [np.cos(a1), np.sin(a1), 0], [np.cos(a0), np.sin(a0), 0]]
        else:
            am = (a0 + a1) / 2; n = [[np.cos(am), np.sin(am), 0]] * 4
        b = len(V); V += p; N += n; F += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    return np.array(V), F, np.array(N)


def gem():
    t = np.linspace(0, 2 * np.pi, 9)[:-1]
    ring = np.c_[np.cos(t) * .004, np.sin(t) * .004, np.zeros(8)]
    V, F, N = [], [], []
    for i in range(8):
        for tip in ([0, 0, .003], [0, 0, -.004]):
            p = np.array([ring[i], ring[(i + 1) % 8], tip]) if tip[2] > 0 else np.array([ring[(i + 1) % 8], ring[i], tip])
            n = np.cross(p[1] - p[0], p[2] - p[0]); n /= np.linalg.norm(n)
            b = len(V); V += list(p); N += [n] * 3; F.append((b, b + 1, b + 2))
    return np.array(V), F, np.array(N)


CASES = [  # name, builder, material, expected rules (empty = must pass)
    ('lid_averaged', lambda: box(split=False), 'Black_French_Polish', {'smeared', 'softedge'}),
    ('lid_split', lambda: box(split=True), 'Black_French_Polish', set()),
    ('handle_flat', lambda: cyl(48, smooth=False), 'walnut solid', {'facets'}),
    ('handle_coarse', lambda: cyl(16, smooth=True), 'walnut solid', {'coarse'}),
    ('handle_good', lambda: cyl(64, smooth=True), 'walnut solid', set()),
    ('lid_flipped', lambda: (lambda V, F, N: (V, F, -N))(*box()), 'Black_French_Polish', {'flipped'}),
    ('no_normals', lambda: (lambda V, F, N: (V, F, None))(*box()), 'Black_French_Polish', {'nonormals'}),
    ('gem', gem, 'Gem_Garnet', set()),
]


def main():
    bad = 0
    reshade = os.path.join(os.path.dirname(HERE), 'web_reshade.py')
    with tempfile.TemporaryDirectory() as tmp:
        for name, build, mat, want in CASES:
            V, F, N = build()
            p = os.path.join(tmp, name + '.glb'); glb(p, V, F, N, mat=mat, clearcoat='Polish' in mat)
            got = {k for k, *_ in check_glb(p, quiet=True)[0]}
            ok = (want <= got) if want else not got
            print(f"{'ok  ' if ok else 'MISS'} {name}: want {sorted(want) or 'pass'}, got {sorted(got) or 'pass'}")
            bad += not ok
            if want:
                o = os.path.join(tmp, name + '_fixed.glb')
                r = subprocess.run([sys.executable, reshade, p, o], capture_output=True, text=True)
                got2 = {k for k, *_ in check_glb(o, quiet=True)[0]} if r.returncode == 0 else {'reshade failed: ' + r.stderr[-200:]}
                ok2 = not got2
                print(f"{'ok  ' if ok2 else 'MISS'} {name} reshaded: got {sorted(got2) or 'pass'}")
                bad += not ok2
    print('PASS' if not bad else f'{bad} FAILED')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

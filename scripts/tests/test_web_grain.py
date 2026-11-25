#!/usr/bin/env python3
"""Planted-mistake test for web_grain_check.py (and web_laminate.py): good GLBs must pass, bad ones must be caught.

Curved cases (25 Nov, Shrine bench plank): a twisted ribbon whose texture follows the twist must fail ("curved");
the same ribbon baked in 3D by web_laminate.py must pass; a straight turned dowel with its grain wrapped round it
must pass (turning round the grain is fine); the ribbon declared "bent" in the spec passes (a steam-bent board).

  python3 scripts/tests/test_web_grain.py
"""
import os, subprocess, sys, tempfile
import numpy as np, trimesh
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, '..', 'web_grain_check.py')


def tex(kind):
    y, x = np.mgrid[0:256, 0:512].astype(float)
    if kind == 'straight': v = np.sin(y / 3.0)
    else: v = np.sin(np.hypot(x - 256, (y - 128) * 2) / 6.0 + 3 * np.sin(x / 40))   # swirl / contour figure
    a = (0.5 + 0.25 * v)[..., None] * np.array([0.40, 0.29, 0.22])
    return Image.fromarray((a * 255).astype(np.uint8))


def board(name, ext, grain, uv_angle=0.0, end_mat=True, image=None):
    """A box with UVs: U along `grain` (an axis index) on the long faces, turned by uv_angle degrees."""
    m = trimesh.creation.box(extents=ext); m = m.subdivide()
    m = trimesh.Trimesh(m.vertices[m.faces].reshape(-1, 3), np.arange(len(m.faces) * 3).reshape(-1, 3), process=False)
    n = m.face_normals; g = np.eye(3)[grain]
    is_end = np.abs(n @ g) > 0.7
    parts = []
    for flag in (False, True):
        sel = np.where(is_end == flag)[0]
        if not len(sel): continue
        sub = m.submesh([sel], append=True)
        uv = np.zeros((len(sub.vertices), 2))
        for fi, f in enumerate(sub.faces):
            nn = sub.face_normals[fi]
            a = g if not flag else (np.array([0, 0, 1.0]) if abs(nn[2]) < .9 else np.array([1.0, 0, 0]))
            a = a - nn * a.dot(nn); a /= np.linalg.norm(a); b = np.cross(nn, a)
            t = np.radians(uv_angle); a, b = np.cos(t) * a + np.sin(t) * b, -np.sin(t) * a + np.cos(t) * b
            for vi in f: uv[vi] = (sub.vertices[vi] @ a / 0.4, sub.vertices[vi] @ b / 0.2)
        mat_name = 'walnut end grain' if flag and end_mat else 'walnut long grain'
        img = image if not (flag and end_mat) else tex('straight')
        sub.visual = trimesh.visual.TextureVisuals(uv=uv, material=trimesh.visual.material.PBRMaterial(name=mat_name, baseColorTexture=img))
        parts.append(sub)
    return parts


def ribbon(turns=0.5, L=1.2, W=0.25, T=0.03, nx=80, ny=8):
    """A board twisted about its length (x): a closed strip, UVs following the surface (one board bent into shape)."""
    V, UV = [], []
    ring = [(-W / 2, -T / 2), (W / 2, -T / 2), (W / 2, T / 2), (-W / 2, T / 2)]
    for i in range(nx + 1):
        x = -L / 2 + L * i / nx; th = np.pi * 2 * turns * i / nx
        c, s_ = np.cos(th), np.sin(th)
        for j in range(4 * ny):
            k, f = divmod(j, ny); (y0, z0), (y1, z1) = ring[k], ring[(k + 1) % 4]
            y, z = y0 + (y1 - y0) * f / ny, z0 + (z1 - z0) * f / ny
            V.append((x, c * y - s_ * z, s_ * y + c * z)); UV.append((x / 0.4, j / (4 * ny) * (2 * W + 2 * T) / 0.2))
    V = np.array(V); UV = np.array(UV); n = 4 * ny; F = []
    for i in range(nx):
        for j in range(n):
            a, b, c2, d = i * n + j, i * n + (j + 1) % n, (i + 1) * n + j, (i + 1) * n + (j + 1) % n
            F += [(a, c2, b), (b, c2, d)]
    m = trimesh.Trimesh(V, np.array(F), process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=UV, material=trimesh.visual.material.PBRMaterial(name='walnut long grain', baseColorTexture=tex('straight')))
    return [m]


def dowel(L=0.5, R=0.02, nx=20, na=24):
    """A straight turned dowel along x, grain texture wrapped round it with U along the length (right)."""
    V, UV, F = [], [], []
    for i in range(nx + 1):
        for j in range(na + 1):
            t = 2 * np.pi * j / na; x = -L / 2 + L * i / nx
            V.append((x, R * np.cos(t), R * np.sin(t))); UV.append((x / 0.4, j / na * 2 * np.pi * R / 0.2))
    for i in range(nx):
        for j in range(na):
            a, b, c, d = i * (na + 1) + j, i * (na + 1) + j + 1, (i + 1) * (na + 1) + j, (i + 1) * (na + 1) + j + 1
            F += [(a, c, b), (b, c, d)]
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=np.array(UV), material=trimesh.visual.material.PBRMaterial(name='walnut long grain', baseColorTexture=tex('straight')))
    return [m]


def scene(boards):
    sc = trimesh.Scene()
    for name, parts in boards:
        for i, p in enumerate(parts): sc.add_geometry(p, node_name=f'{name}_{i:06x}', geom_name=f'{name}_{i}')
    return sc


CASES = {   # name: (boards, should fail)
    'good':      ([('Leg', board('Leg', (0.04, 0.6, 0.04), 1, image=tex('straight'))),
                   ('Rail', board('Rail', (0.4, 0.06, 0.02), 0, image=tex('straight')))], False),
    'diagonal':  ([('Leg', board('Leg', (0.04, 0.6, 0.04), 1, uv_angle=40, image=tex('straight')))], True),
    'across':    ([('Rail', board('Rail', (0.4, 0.06, 0.02), 0, uv_angle=90, image=tex('straight')))], True),
    'swirl':     ([('Leg', board('Leg', (0.04, 0.6, 0.04), 1, image=tex('swirl')))], True),
    'end_on_long': ([('Leg', board('Leg', (0.04, 0.6, 0.04), 0, image=tex('straight')))], True),  # grain set across: end texture lands on long faces
    'twist_2d':  ([('Plank', ribbon())], True),        # Shrine bench, 25 Nov: grain wraps the twist
    'dowel':     ([('Dowel', dowel())], False),        # turned round the grain: a wrapped 2D texture is right
}
LAMINATE = os.path.join(HERE, '..', 'web_laminate.py')
SPEC_STACK = {'parts': {'^Plank': {'grain': 'x', 'lamination': {'mode': 'stack', 't': 0.875, 'z0': 0.0, 'axis': 'x', 'seed': 3}}}}
SPEC_BENT = {'parts': {'^Plank': {'grain': 'x', 'bent': True}}}

if __name__ == '__main__':
    d = tempfile.mkdtemp(); bad = 0
    for name, (boards, should_fail) in CASES.items():
        p = os.path.join(d, name + '.glb'); scene(boards).export(p)
        r = subprocess.run([sys.executable, '-W', 'ignore', CHECK, p], capture_output=True, text=True)
        failed = r.returncode != 0
        ok = failed == should_fail; bad += not ok
        print(f'{"ok  " if ok else "MISS"} {name}: check {"failed" if failed else "passed"} (expected {"fail" if should_fail else "pass"})')
        if not ok: print(r.stdout[-800:])
    # the twisted ribbon baked in 3D must pass; declared bent must pass; an edited bake must fail
    import json
    src = os.path.join(d, 'twist_2d.glb')
    extra = []
    for name, spec, prep, should_fail in (('twist_baked', SPEC_STACK, 'bake', False), ('twist_bent', SPEC_BENT, None, False),
                                          ('twist_wrong_bake', {'parts': {'^Plank': {'lamination': dict(SPEC_STACK['parts']['^Plank']['lamination'], mode='stave')}}}, 'bake', True)):
        sp = os.path.join(d, name + '.json'); json.dump(spec if name != 'twist_wrong_bake' else SPEC_STACK, open(sp, 'w'))
        p = src
        if prep == 'bake':
            p = os.path.join(d, name + '.glb')
            r = subprocess.run([sys.executable, '-W', 'ignore', LAMINATE, src, p, '--spec', sp, '--texel', '0.08'], capture_output=True, text=True)
            if r.returncode: print(r.stdout[-400:], r.stderr[-800:])
        if name == 'twist_wrong_bake': json.dump(spec, open(sp, 'w'))   # spec now disagrees with how it was baked
        r = subprocess.run([sys.executable, '-W', 'ignore', CHECK, p, '--spec', sp], capture_output=True, text=True)
        failed = r.returncode != 0; ok = failed == should_fail; bad += not ok
        print(f'{"ok  " if ok else "MISS"} {name}: check {"failed" if failed else "passed"} (expected {"fail" if should_fail else "pass"})')
        if not ok: print(r.stdout[-800:])
        extra.append(name)
    n = len(CASES) + len(extra)
    print(f'{n - bad} of {n} right'); sys.exit(1 if bad else 0)

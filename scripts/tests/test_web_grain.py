#!/usr/bin/env python3
"""Planted-mistake test for web_grain_check.py: one good GLB and four bad ones, each must be caught.

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
}

if __name__ == '__main__':
    d = tempfile.mkdtemp(); bad = 0
    for name, (boards, should_fail) in CASES.items():
        p = os.path.join(d, name + '.glb'); scene(boards).export(p)
        r = subprocess.run([sys.executable, '-W', 'ignore', CHECK, p], capture_output=True, text=True)
        failed = r.returncode != 0
        ok = failed == should_fail; bad += not ok
        print(f'{"ok  " if ok else "MISS"} {name}: check {"failed" if failed else "passed"} (expected {"fail" if should_fail else "pass"})')
        if not ok: print(r.stdout[-800:])
    print(f'{len(CASES) - bad} of {len(CASES)} right'); sys.exit(1 if bad else 0)

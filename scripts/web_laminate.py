#!/usr/bin/env python3
"""Bake real 3D wood onto the curved, twisted, swept, turned or glued-up parts of a web viewer GLB.

web_glb.py lays one straight-grain texture along each part. That is right for a flat board and wrong for anything
curved: on a twisted plank the grain follows the twist like one board bent into shape (Shrine bench viewer,
25 Nov: "grain is wrong again"). A glue-up is many boards, and the surface of a ground or turned part cuts
through them; the only honest texture is the wood evaluated in 3D at each surface point (solid_wood.py, the same
model as the Cycles shader scripts/blender/laminated_wood.py, so the viewer matches the renders).

For every part the spec gives a "lamination" (or a part named on the command line), this:
  1. welds the part's mesh and unwraps it fresh with xatlas (no overlaps, even texel density),
  2. rasterises every texel back to its 3D point and normal and evaluates the wood there,
  3. replaces the part's primitives with one primitive and one baked material ("<species> solid <part>"),
  4. writes the bake parameters to the node's extras "grain_bake", which web_grain_check.py re-evaluates.

Spec (the cadcheck spec's parts, model frame inches Z up, same keys as laminated_wood.material()):
  "parts": {"^Plank$": {"grain": "x", "lamination": {"mode": "stack", "t": 0.875, "z0": 17.6, "axis": "x", "seed": 3}},
            "^Post_L$": {"grain": "z", "lamination": {"mode": "stave", "n": 16, "cx": -60, "cy": 0, "rm": 9.75, "seed": 10}},
            "^Peg_": {"grain": "z", "lamination": {"mode": "solid", "axis": "z"}}}

  python3 scripts/web_laminate.py IN.glb OUT.glb --spec PIECE.cadcheck.json [--auto] [--units-in 0.0254] [--texel 0.045] [--max-res 2048]
--auto catches what the spec doesn't name: any textured wood part that bends along its grain is baked as one solid
board along its long axis in its own texture's tone (the Moth case's turned ash parts, 25 Nov).
IN must be plain (no meshopt/draco, no quantization): `npx @gltf-transform/cli copy in.glb a.glb && npx
@gltf-transform/cli dequantize a.glb plain.glb`. Then check and compress:
  python3 scripts/web_grain_check.py OUT.glb --spec PIECE.cadcheck.json --sheet sheet.jpg
  npx @gltf-transform/cli prune OUT.glb p.glb && npx @gltf-transform/cli meshopt p.glb site.glb
Needs: pip install numpy pillow pygltflib xatlas
"""
import argparse, io, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw
import pygltflib as gl
import xatlas

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solid_wood import wood_color  # noqa: E402
import woodlib as W  # noqa: E402

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def read_acc(g, blob, i):
    a = g.accessors[i]; bv = g.bufferViews[a.bufferView]
    dt = np.dtype(CT[a.componentType]); n = NC[a.type]
    off = (bv.byteOffset or 0) + (a.byteOffset or 0)
    stride = bv.byteStride or dt.itemsize * n
    raw = np.frombuffer(blob, np.uint8, count=stride * (a.count - 1) + dt.itemsize * n, offset=off)
    if stride == dt.itemsize * n:
        arr = raw.view(dt).reshape(a.count, n)
    else:
        arr = np.lib.stride_tricks.as_strided(raw, (a.count, dt.itemsize * n), (stride, 1)).copy().view(dt).reshape(a.count, n)
    if a.normalized: raise SystemExit('quantized GLB: run gltf-transform dequantize first')
    return arr.astype(np.float64 if dt == np.float32 else np.int64)


class Out:
    def __init__(s, g, blob): s.g, s.buf = g, bytearray(blob)

    def add(s, data, target=None):
        while len(s.buf) % 4: s.buf.append(0)
        off = len(s.buf); s.buf += data
        s.g.bufferViews.append(gl.BufferView(buffer=0, byteOffset=off, byteLength=len(data), target=target))
        return len(s.g.bufferViews) - 1

    def acc(s, arr, typ, target):
        arr = np.ascontiguousarray(arr)
        ct = {np.dtype(np.float32): 5126, np.dtype(np.uint32): 5125}[arr.dtype]
        bv = s.add(arr.tobytes(), target)
        a = gl.Accessor(bufferView=bv, componentType=ct, count=len(arr), type=typ)
        if typ == 'VEC3' and ct == 5126: a.min = arr.min(0).tolist(); a.max = arr.max(0).tolist()
        s.g.accessors.append(a); return len(s.g.accessors) - 1


def node_world(g, idx):
    """4x4 world matrix of node idx (walks parents)."""
    parent = {c: i for i, n in enumerate(g.nodes) for c in (n.children or [])}
    M = np.eye(4); i = idx
    while i is not None:
        n = g.nodes[i]
        if n.matrix: L = np.array(n.matrix, float).reshape(4, 4).T
        else:
            T = np.eye(4); T[:3, 3] = n.translation or [0, 0, 0]
            x, y, z, w = n.rotation or [0, 0, 0, 1]
            R = np.eye(4); R[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                                        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                                        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
            S = np.diag(list(n.scale or [1, 1, 1]) + [1])
            L = T @ R @ S
        M = L @ M; i = parent.get(i)
    return M


def to_model(Pw, units_in):
    """GLB world (Y up, metres) -> model frame (Z up, inches)."""
    return np.stack([Pw[:, 0], -Pw[:, 2], Pw[:, 1]], 1) / units_in


WOOD = re.compile(r'(?i)walnut|oak|ash|maple|cherry|cedar|wood|ply|birch|mahogany|sapele|pine|grain|rift|flat')
SOLID = re.compile(r'(?i)\bsolid\b')


def image_rgb(g, blob, mat):
    """Mean sRGB of a material's base colour texture (to keep a model's own tone), or None."""
    pb = g.materials[mat].pbrMetallicRoughness
    if pb is None or pb.baseColorTexture is None: return None
    im = g.images[g.textures[pb.baseColorTexture.index].source]
    bv = g.bufferViews[im.bufferView]; data = blob[(bv.byteOffset or 0):(bv.byteOffset or 0) + bv.byteLength]
    return np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), float).reshape(-1, 3).mean(0) / 255


def auto_solid(g, blob, ni, woodp, units_in, force=False, a_rings=6.0):
    """--auto: a textured wood part (one board) that bends along its grain gets a solid bake along its long axis."""
    from web_grain_check import grain_bend, vertex_faces
    if any(image_rgb(g, blob, pr.material) is None for pr in woodp): return None
    Ps, Fs, UVs, Ws, off = [], [], [], [], 0
    for pr in woodp:
        P = read_acc(g, blob, pr.attributes.POSITION)
        I = read_acc(g, blob, pr.indices).reshape(-1, 3) if pr.indices is not None else np.arange(len(P)).reshape(-1, 3)
        UVs.append(read_acc(g, blob, pr.attributes.TEXCOORD_0))
        im = g.images[g.textures[g.materials[pr.material].pbrMetallicRoughness.baseColorTexture.index].source]
        bv = g.bufferViews[im.bufferView]; sz = Image.open(io.BytesIO(blob[(bv.byteOffset or 0):(bv.byteOffset or 0) + bv.byteLength])).size
        Ps.append(P); Fs.append(I + off); Ws.append(np.full(len(I), sz[0] >= sz[1])); off += len(P)
    P0, F0, UV, wide = np.vstack(Ps), np.vstack(Fs), np.vstack(UVs), np.concatenate(Ws)
    M = node_world(g, ni); Pm0 = to_model((np.c_[P0, np.ones(len(P0))] @ M.T)[:, :3], units_in)
    # the grain the texture shows, per face (same as web_grain_check.py)
    p0, p1, p2 = Pm0[F0[:, 0]], Pm0[F0[:, 1]], Pm0[F0[:, 2]]; t0, t1, t2 = UV[F0[:, 0]], UV[F0[:, 1]], UV[F0[:, 2]]
    e1, e2, d1, d2 = p1 - p0, p2 - p0, t1 - t0, t2 - t0
    det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]; sd = np.where(np.abs(det) > 1e-14, det, 1)[:, None]
    dU = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / sd; dV = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / sd
    t = np.where(wide[:, None], dU, dV); t /= (np.linalg.norm(t, axis=1, keepdims=True) + 1e-15)
    _, first, inv = np.unique(np.round(Pm0 * 1e4), axis=0, return_index=True, return_inverse=True)
    Pm, F = Pm0[first], inv.reshape(-1)[F0]
    C = Pm - Pm.mean(0); w, v = np.linalg.eigh(np.cov(C.T)); e = [np.ptp(C @ v[:, k]) for k in range(3)]
    if sorted(e)[-1] < 1.15 * sorted(e)[-2]: return None
    u = v[:, int(np.argmax(e))]
    n = np.cross(Pm[F[:, 1]] - Pm[F[:, 0]], Pm[F[:, 2]] - Pm[F[:, 0]]); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-15)
    keep = (np.abs(n @ u) <= 0.7) & (np.abs(det) > 1e-14)
    share = grain_bend(Pm, F, vertex_faces(F, len(Pm)), np.where(keep)[0], t[keep], np.ptp(C @ u))
    if share <= 0.05 and not force: return None      # half the check's limit: borderline parts get baked too
    rgb = np.mean([image_rgb(g, blob, pr.material) for pr in woodp], 0)
    print(f'node {ni}: bends along its grain ({"flagged by web_grain_check" if force else f"{100 * share:.0f}% of its faces"}) -> solid bake along its long axis')
    return dict(mode='solid', axis=[round(x, 5) for x in u], origin=[round(x, 3) for x in Pm.mean(0)], rgb=[round(x, 4) for x in rgb],
                rings=a_rings, contrast=1.8, pores=0.2, pore_freq=30.0)   # open-pored streaks like the model's own texture


def unwrap(P, N, F, texel, max_res, pad):
    """One xatlas page no bigger than max_res: coarsen the texel until it fits."""
    while True:
        atlas = xatlas.Atlas(); atlas.add_mesh(P.astype(np.float32), F.astype(np.uint32), N.astype(np.float32))
        co = xatlas.ChartOptions(); co.max_cost = 4.0
        po = xatlas.PackOptions(); po.padding = pad; po.bilinear = True; po.texels_per_unit = 1.0 / texel
        atlas.generate(co, po)
        if atlas.atlas_count == 1 and max(atlas.width, atlas.height) <= max_res:
            vmap, faces, uv = atlas[0]; return vmap, faces, uv, atlas.width, atlas.height, texel
        texel *= 1.15 * max(atlas.width, atlas.height) / max_res if atlas.atlas_count == 1 else 1.3


def bake_part(P, N, F, lam, species, max_res, texel, pad=4):
    """xatlas unwrap + per-texel solid wood. P, N: model frame inches. Returns (vmap, faces, uv, image, texel)."""
    vmap, faces, uv, W, H, texel = unwrap(P, N, F, texel, max_res, pad)
    # triangle id per texel
    ids = Image.new('I', (W, H), -1); dr = ImageDraw.Draw(ids)
    px = uv * [W, H]
    for i, f in enumerate(faces):
        dr.polygon([tuple(px[f[0]]), tuple(px[f[1]]), tuple(px[f[2]])], fill=i)
    tid = np.asarray(ids, np.int64)
    yy, xx = np.nonzero(tid >= 0); t = tid[yy, xx]
    q = np.stack([xx + 0.5, yy + 0.5], 1)
    a, b, c = px[faces[t, 0]], px[faces[t, 1]], px[faces[t, 2]]
    v0, v1, v2 = b - a, c - a, q - a
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]; den = np.where(np.abs(den) < 1e-12, 1e-12, den)
    l1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den; l2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
    l1, l2 = np.clip(l1, 0, 1), np.clip(l2, 0, 1); s = np.maximum(l1 + l2, 1); l1, l2 = l1 / s, l2 / s; l0 = 1 - l1 - l2
    Pv, Nv = P[vmap], N[vmap]
    X = l0[:, None] * Pv[faces[t, 0]] + l1[:, None] * Pv[faces[t, 1]] + l2[:, None] * Pv[faces[t, 2]]
    Nn = l0[:, None] * Nv[faces[t, 0]] + l1[:, None] * Nv[faces[t, 1]] + l2[:, None] * Nv[faces[t, 2]]
    img = np.zeros((H, W, 3)); filled = np.zeros((H, W), bool)
    img[yy, xx] = wood_color(X, Nn, lam, species); filled[yy, xx] = True
    for _ in range(pad + 2):      # bleed into the gutters so mipmaps don't pull in black
        if filled.all(): break
        acc = np.zeros_like(img); cnt = np.zeros((H, W))
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            acc += np.roll(np.roll(img * filled[..., None], dy, 0), dx, 1); cnt += np.roll(np.roll(filled, dy, 0), dx, 1)
        new = ~filled & (cnt > 0); img[new] = acc[new] / cnt[new][:, None]; filled |= new
    img[~filled] = img[filled].mean(0)
    return vmap, faces, uv, Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)), texel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('--spec')
    ap.add_argument('--auto', action='store_true', help='also bake, as one solid board along its long axis, every textured wood part '
                    'that bends along its grain and has no lamination in the spec (unnamed parts, turned handles, carved feet)')
    ap.add_argument('--all', action='store_true', help='bake EVERY wood part from the wood library (woodlib boards: '
                    'flat-sawn cathedrals on panels, rift on frame parts, sapwood, end grain from the same rings). Spec per part: '
                    '"cut": flat|quarter|rift|auto, "grain": x|y|z, "sap": "edge", "seed". This is the default way to build a viewer GLB.')
    ap.add_argument('--units-in', type=float, default=0.0254, help='GLB metres per model unit (inch)')
    ap.add_argument('--texel', type=float, default=0.045, help='inches per texel when --res is 0')
    ap.add_argument('--max-res', type=int, default=2048)
    ap.add_argument('--quality', type=int, default=88)
    ap.add_argument('--rings', type=float, default=6.0, help='--auto parts: growth rings per inch (ash, oak ~6; walnut ~3)')
    a = ap.parse_args()
    spec = json.load(open(a.spec)) if a.spec else {}; species0 = spec.get('species', 'walnut')
    g = gl.GLTF2().load(a.src)
    if any(e in (g.extensionsRequired or []) for e in ('EXT_meshopt_compression', 'KHR_draco_mesh_compression', 'KHR_mesh_quantization')):
        sys.exit('decode and dequantize first (see the docstring)')
    flagged = set()
    if a.auto:     # what the check itself fails as 'curved' gets baked, so the two never disagree
        import subprocess, tempfile
        jf = os.path.join(tempfile.mkdtemp(), 'fails.json')
        subprocess.run([sys.executable, '-W', 'ignore', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_grain_check.py'),
                        a.src, '--json', jf] + (['--spec', a.spec] if a.spec else []), capture_output=True)
        if os.path.exists(jf): flagged = {f['node'] for f in json.load(open(jf)) if f['kind'] == 'curved'}
    out = Out(g, g.binary_blob()); blob = bytes(out.buf); done = []
    users = {}
    BOARDS = {}
    for ni, node in enumerate(g.nodes):
        if node.mesh is not None: users.setdefault(node.mesh, []).append(ni)
    for ni, node in enumerate(g.nodes):
        if node.mesh is None: continue
        name = re.sub(r'\.\d+$', '', node.name or '')
        ps = {}
        for rx, d in spec.get('parts', {}).items():
            if re.search(rx, name): ps.update(d)
        lam = ps.get('lamination')
        mesh = g.meshes[node.mesh]
        woodp = [pr for pr in mesh.primitives if pr.material is not None
                 and WOOD.search(g.materials[pr.material].name or '') and not SOLID.search(g.materials[pr.material].name or '')]
        if not woodp: continue
        if not lam and a.auto:
            lam = auto_solid(g, blob, ni, woodp, a.units_in, force=(node.name or str(ni)) in flagged, a_rings=a.rings)
            if lam: lam['seed'] = 100 + ni
        if not lam and a.all:
            lam = {'mode': 'board_pending'}
        if not lam: continue
        if not node.name: node.name = f'wood_{ni}'; name = node.name
        if len(users[node.mesh]) > 1:     # instanced mesh: give this node its own copy before baking it in place
            g.meshes.append(gl.Mesh(name=f'{name}_mesh', primitives=list(mesh.primitives))); node.mesh = len(g.meshes) - 1
            mesh = g.meshes[node.mesh]
        species = ps.get('species', species0)
        Ps, Ns, Fs, off = [], [], [], 0
        for pr in woodp:
            P = read_acc(g, blob, pr.attributes.POSITION)
            Nl = read_acc(g, blob, pr.attributes.NORMAL) if pr.attributes.NORMAL is not None else None
            I = read_acc(g, blob, pr.indices).reshape(-1, 3) if pr.indices is not None else np.arange(len(P)).reshape(-1, 3)
            if Nl is None:      # smooth normals from the faces (welded by position)
                _, fi, iv = np.unique(np.round(P * 1e5), axis=0, return_index=True, return_inverse=True); iv = iv.reshape(-1)
                fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]]); acc = np.zeros((len(fi), 3))
                for k in range(3): np.add.at(acc, iv[I[:, k]], fn)
                Nl = acc[iv] / (np.linalg.norm(acc[iv], axis=1, keepdims=True) + 1e-15)
            Ps.append(P); Ns.append(Nl); Fs.append(I + off); off += len(P)
        P, Nl, F = np.vstack(Ps), np.vstack(Ns), np.vstack(Fs)
        # weld by position + normal (the old UV seams go; the split normals at real edges stay)
        key = np.round(np.hstack([P * 1e5, Nl * 50]))
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        P, Nl, F = P[first], Nl[first], inv.reshape(-1)[F]
        M = node_world(g, ni)
        Pm = to_model((np.c_[P, np.ones(len(P))] @ M.T)[:, :3], a.units_in)
        Nw = Nl @ np.linalg.inv(M[:3, :3])
        Nm = np.stack([Nw[:, 0], -Nw[:, 2], Nw[:, 1]], 1); Nm /= np.linalg.norm(Nm, axis=1, keepdims=True) + 1e-12
        if lam.get('mode') == 'board_pending':     # woodlib board from the part's own geometry (model frame inches)
            seed = ps.get('seed', sum(map(ord, name)) % 997)
            lam = W.board(Pm, grain=ps.get('grain'), cut=ps.get('cut', 'auto'), species_name=species, seed=seed,
                          sap=ps.get('sap'), finish=ps.get('finish', spec.get('finish', 'oil')), lod=a.texel, name=name)
            mate = W.pair_name(name)      # bookmatched pair (Door_Board_L / _R): the second leaf mirrors the first
            if mate in BOARDS and BOARDS[mate][0].get('cut') == 'flat' == lam.get('cut') and spec.get('bookmatch', True):
                lam = W.bookmatch(BOARDS[mate][0], BOARDS[mate][1], Pm, name=name) or lam
            BOARDS[name] = (lam, Pm)
        texel0 = a.texel
        if lam.get('mode') == 'board':     # at least 5 texels per growth ring, or the rings alias into mush
            texel0 = min(a.texel, 1.0 / (5.0 * W.species(species)[1]['rings_per_in'])); lam['lod'] = texel0
        vmap, faces, uv, img, texel = bake_part(Pm, Nm, F, lam, species, a.max_res, texel0)
        bio = io.BytesIO(); img.save(bio, 'JPEG', quality=a.quality); bv = out.add(bio.getvalue())
        g.images.append(gl.Image(bufferView=bv, mimeType='image/jpeg', name=f'{name}_solid'))
        if not g.samplers: g.samplers.append(gl.Sampler(magFilter=9729, minFilter=9987, wrapS=33071, wrapT=33071))
        g.textures.append(gl.Texture(source=len(g.images) - 1, sampler=0))
        sk = W.species(species)[0]
        g.materials.append(gl.Material(name=f'{species} solid {name}', doubleSided=False, pbrMetallicRoughness=gl.PbrMetallicRoughness(
            baseColorTexture=gl.TextureInfo(index=len(g.textures) - 1), metallicFactor=0.0, roughnessFactor=W.roughness(sk, lam.get('finish', 'oil'))),
            extras=W.board_extras(lam, sk)))
        prim = gl.Primitive(attributes=gl.Attributes(
            POSITION=out.acc(P[vmap].astype(np.float32), 'VEC3', 34962),
            NORMAL=out.acc(Nl[vmap].astype(np.float32), 'VEC3', 34962),
            TEXCOORD_0=out.acc(uv.astype(np.float32), 'VEC2', 34962)),
            indices=out.acc(faces.astype(np.uint32).ravel(), 'SCALAR', 34963), material=len(g.materials) - 1)
        mesh.primitives = [pr for pr in mesh.primitives if pr not in woodp] + [prim]
        ex = dict(node.extras or {}); ex['part'] = ex.get('part', name)
        ex['grain_bake'] = dict(lam, species=species, frame='model inches, Z up', units_in=a.units_in, texel=round(texel, 4))
        node.extras = ex
        done.append((name, lam.get('mode'), img.size))
        print(f'{name}: {lam.get("mode")} baked, {len(faces)} tris, {img.size[0]}x{img.size[1]} texture, {texel:.3f} in/texel')
    g.buffers[0].byteLength = len(out.buf); g.set_binary_blob(bytes(out.buf))
    g.save_binary(a.dst)
    print(f'{len(done)} parts baked -> {a.dst}')


if __name__ == '__main__':
    main()

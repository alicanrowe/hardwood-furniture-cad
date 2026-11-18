# Fawn Orchard SDF toolkit. Units: metres, Z up.
import numpy as np, cv2
from scipy.spatial import cKDTree
from scipy import ndimage
from skimage import measure
IN = 0.0254

def grid(bmin, bmax, h):
    xs = [np.arange(a, b + h, h) for a, b in zip(bmin, bmax)]
    X, Y, Z = np.meshgrid(*xs, indexing='ij')
    return xs, X, Y, Z

def mesh_sdf(F, xs, path, smooth=0):
    if smooth: F = ndimage.gaussian_filter(F, smooth)
    h = xs[0][1] - xs[0][0]
    v, f, n, _ = measure.marching_cubes(F, 0.0, spacing=(h, h, h))
    v += np.array([xs[0][0], xs[1][0], xs[2][0]])
    write_ply(path, v, f[:, ::-1])  # outward normals
    return v, f

def write_ply(path, v, f):
    with open(path, 'wb') as fh:
        fh.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(v)}\nproperty float x\nproperty float y\nproperty float z\n"
                  f"element face {len(f)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
        fh.write(v.astype('<f4').tobytes())
        ff = np.empty(len(f), dtype=[('n', 'u1'), ('a', '<i4', 3)]); ff['n'] = 3; ff['a'] = f
        fh.write(ff.tobytes())

def mask_sdf2d(mask, px_per_m):
    """Signed distance (m) of a binary mask, negative inside."""
    m = mask > 0
    di = ndimage.distance_transform_edt(m); do = ndimage.distance_transform_edt(~m)
    return (do - di) / px_per_m

def sample2d(img, u, v, fill):
    """Bilinear sample 2D array at fractional pixel coords (u=col, v=row)."""
    H, W = img.shape
    out = ndimage.map_coordinates(img, [v.ravel(), u.ravel()], order=1, mode='constant', cval=fill)
    return out.reshape(u.shape)

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def smax(a, b, k):
    return -smin(-a, -b, k)

def gouge(X, Y, Z, cell=0.02, depth=0.002, aniso=(1, 1, 1), seed=0, rot=None):
    """Power-carver scallops: Voronoi F1 cups. Returns +displacement (add to SDF to cut in)."""
    rng = np.random.default_rng(seed)
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    if rot is not None: P = P @ rot.T
    P = P / np.array(aniso)
    lo, hi = P.min(0) - cell, P.max(0) + cell
    xs = [np.arange(a, b, cell) for a, b in zip(lo, hi)]
    G = np.stack(np.meshgrid(*xs, indexing='ij'), -1).reshape(-1, 3)
    G = G + (rng.random(G.shape) - 0.5) * cell * 0.9
    d, _ = cKDTree(G).query(P, k=1, workers=-1)
    d = (d / (cell * 0.75)).clip(0, 1.3)
    return (depth * (1 - d ** 2)).reshape(X.shape)  # deepest at cell centre

def fbm(X, Y, Z, scale, octaves=3, seed=0):
    rng = np.random.default_rng(seed); out = np.zeros_like(X); amp = 1.0
    for o in range(octaves):
        k = rng.normal(size=(6, 3)) * (2 ** o) / scale
        ph = rng.random(6) * 6.283
        for i in range(6):
            out += amp / 6 * np.sin(X * k[i, 0] + Y * k[i, 1] + Z * k[i, 2] + ph[i])
        amp *= 0.5
    return out

def carve_scoops(F, xs, scoops, mode='cut', k=0.0):
    """scoops: list of (center(3), axes R(3x3) columns = local axes, radii(3)). Cuts ellipsoids out of F (in place)."""
    h = xs[0][1] - xs[0][0]
    for c, R, r in scoops:
        ext = np.abs(R) @ np.array(r)
        sl = []
        for a in range(3):
            i0 = max(int((c[a] - ext[a] - xs[a][0]) / h) - 1, 0); i1 = min(int((c[a] + ext[a] - xs[a][0]) / h) + 2, len(xs[a]))
            sl.append(slice(i0, i1))
        if any(s.stop <= s.start for s in sl): continue
        gx, gy, gz = np.meshgrid(xs[0][sl[0]], xs[1][sl[1]], xs[2][sl[2]], indexing='ij')
        P = np.stack([gx - c[0], gy - c[1], gz - c[2]], -1) @ R
        q = P / np.array(r); k0 = np.linalg.norm(q, axis=-1); k1 = np.linalg.norm(q / np.array(r), axis=-1)
        e = k0 * (k0 - 1) / (k1 + 1e-9)
        sub = F[sl[0], sl[1], sl[2]]
        if mode == 'cut':
            F[sl[0], sl[1], sl[2]] = np.maximum(sub, -e) if k == 0 else smax(sub, -e, k)
        else:
            F[sl[0], sl[1], sl[2]] = np.minimum(sub, e) if k == 0 else smin(sub, e, k)
    return F

def frame(t, n):
    """Orthonormal frame: x along t, z along n (surface normal)."""
    t = np.array(t, float); n = np.array(n, float); n /= np.linalg.norm(n)
    t = t - n * (t @ n); t /= np.linalg.norm(t); b = np.cross(n, t)
    return np.stack([t, b, n], 1)

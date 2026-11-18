from fo import *
def ell(X, Y, Z, c, r, R=None):
    P = np.stack([X - c[0], Y - c[1], Z - c[2]], -1)
    if R is not None: P = P @ R
    q = P / np.array(r); k0 = np.linalg.norm(q, axis=-1); k1 = np.linalg.norm(q / np.array(r), axis=-1)
    return k0 * (k0 - 1) / (k1 + 1e-9)
def rbox(X, Y, Z, c, hs, r):
    q = np.stack([np.abs(X-c[0])-hs[0]+r, np.abs(Y-c[1])-hs[1]+r, np.abs(Z-c[2])-hs[2]+r], -1)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r
def capsule(X, Y, Z, a, b, r):
    a = np.array(a); b = np.array(b); P = np.stack([X, Y, Z], -1)
    pa = P - a; ba = b - a; h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    rr = r(h) if callable(r) else r
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - rr
def rotx(a):
    c, s = np.cos(a), np.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def roty(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def blobpoly(X, Y, pts, warp=0.0, seed=0):
    """2D SDF of polygon (in XY), warped edge."""
    pts = np.array(pts)
    H = 0.003
    xmin, ymin = pts.min(0) - 0.05; xmax, ymax = pts.max(0) + 0.05
    gx = np.arange(xmin, xmax, H); gy = np.arange(ymin, ymax, H)
    GX, GY = np.meshgrid(gx, gy)
    inside = np.zeros(GX.shape, np.uint8)
    cv2.fillPoly(inside, [np.round((pts - [xmin, ymin]) / H).astype(np.int32)], 1)
    D = mask_sdf2d(inside.astype(np.uint8), 1 / H)
    u = (X - xmin) / H; v = (Y - ymin) / H
    d = sample2d(D, u, v, 0.05)
    if warp: d += warp * fbm(X, Y, X * 0, 0.05, 2, seed)
    return d

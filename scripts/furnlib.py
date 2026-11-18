"""Shared helpers for the cut list, printouts, sheet check and build book.

Parts come from a GLB/STL assembly (one mesh node per part), read the same way cadcheck reads them,
so roles (wood, floating, ply, hardware, fastener, insert, ignore), species and grain come from the
same cadcheck spec file.
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import numpy as np
import cadcheck as C  # noqa: E402


def load(model, units="m", up="auto", spec=None):
    """{name: trimesh in inches, Z up} and the loaded spec."""
    up = up if up != "auto" else ("y" if model.lower().endswith((".glb", ".gltf")) else "z")
    if spec:
        C.SPEC.update(json.load(open(spec)) if isinstance(spec, str) else spec)
    parts = C.load_parts(model, units)
    if up == "y":                           # glTF: Y up -> Z up, keeping it right-handed
        R = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
        for m in parts.values():
            m.apply_transform(R)
    elif up == "x":
        R = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]], float)
        for m in parts.values():
            m.apply_transform(R)
    C.UP[:] = [0, 0, 1]
    return parts, C.SPEC


def theme(path=None):
    path = path or os.path.join(ROOT, "assets", "theme.json")
    t = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    t["fonts"] = {k: (v if os.path.isabs(v) else os.path.join(base, v)) for k, v in t["fonts"].items()}
    return t


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def frac(x, den=32):
    """1.40625 -> '1 13/32' (nearest 1/den)."""
    neg = x < 0
    n = round(abs(x) * den)
    w, r = divmod(n, den)
    if not r:
        s = f"{w}"
    else:
        g = math.gcd(r, den)
        s = (f"{w} " if w else "") + f"{r // g}/{den // g}"
    return ("-" if neg else "") + s


def frame(m, grain=None):
    """Oriented box of a part: (centre, R with columns L, W, T axes, extents (T, W, L))."""
    obb = m.bounding_box_oriented
    ext = np.array(obb.primitive.extents)
    R = np.array(obb.primitive.transform[:3, :3])
    c = np.array(obb.primitive.transform[:3, 3])
    order = list(np.argsort(ext)[::-1])          # longest first
    if grain is not None:                        # length = the axis closest to the grain
        gi = int(np.argmax([abs(np.dot(R[:, i], grain)) for i in range(3)]))
        order.remove(gi)
        order = [gi] + order
    Lax, Wax, Tax = R[:, order[0]], R[:, order[1]], R[:, order[2]]
    L, W, T = ext[order[0]], ext[order[1]], ext[order[2]]
    if W < T:                                    # keep T the thinnest of the two cross dimensions
        Wax, Tax, W, T = Tax, Wax, T, W
    return c, np.column_stack([Lax, Wax, Tax]), (float(T), float(W), float(L))


BASE_RE = re.compile(r"([_\- ]?(L|R|F|B|FL|FR|BL|BR|Top|Bot|Left|Right|Front|Back)?[_\- ]?\d*)$", re.I)


def group_label(names):
    """A readable label for a set of identical parts: common prefix of their names, tidied."""
    if len(names) == 1:
        s = names[0]
    else:
        s = os.path.commonprefix(names)
        if len(s) < 3:
            s = names[0]
    s = re.sub(r"[_\-]+$", "", s)
    s = re.sub(r"(_\d+)$", "", s)
    return s.replace("_", " ").strip() or names[0]


def letters():
    """A, B, ... Z (no I or O), then AA, BB, ... then AB, AC ..."""
    import string
    one = [c for c in string.ascii_uppercase if c not in "IO"]
    yield from one
    yield from (c + c for c in one)
    yield from (c + d for c in one for d in one if c != d)


def parts_table(parts, snap=1 / 64):
    """Group identical parts. Returns a list of dicts with letter, label, names, qty, T, W, L, role,
    material, species, grain axis note. Hardware and 'ignore' parts are listed apart (role hardware)."""
    groups = {}
    for n, m in parts.items():
        role, grain = C.part_info(n, m)
        if role == "ignore":
            continue
        c, R, (T, W, L) = frame(m, grain)
        mat = str(C.part_spec(n, "material", "") or "")
        if role == "ply" and not mat:
            mat = "plywood"
        if role == "hardware" and not mat:
            mat = "hardware"
        sp = str(C.part_spec(n, "species", "") or "") if role not in ("ply", "hardware") else ""
        cut = str(C.part_spec(n, "cut", "") or "") if role not in ("ply", "hardware") else ""
        key = (role == "hardware", mat, sp, cut, round(T / snap), round(W / snap), round(L / snap),
               round(float(m.volume) / (T * W * L + 1e-9), 2))
        groups.setdefault(key, []).append((n, T, W, L, role))
    rows = []
    for key, items in groups.items():
        names = sorted(i[0] for i in items)
        T, W, L = items[0][1:4]
        rows.append(dict(names=names, qty=len(names), T=T, W=W, L=L, role=items[0][4],
                         material=key[1], species=key[2], cut=key[3], label=group_label(names)))
    order = {"wood": 0, "floating": 1, "insert": 2, "fastener": 3, "ply": 4, "hardware": 9}
    rows.sort(key=lambda r: (order.get(r["role"], 5), -r["T"], -r["L"], r["label"]))
    let = letters()
    for r in rows:
        r["letter"] = "" if r["role"] == "hardware" else next(let)
    return rows


def sha_prefix(path, n=10):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:n]

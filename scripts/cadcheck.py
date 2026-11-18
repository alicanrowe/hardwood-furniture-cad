#!/usr/bin/env python3
"""cadcheck: automatic joinery and model-hygiene checks for a furniture GLB/STL assembly.

Usage:
  python3 cadcheck.py model.glb [--only REGEX] [--skip REGEX] [--units in|mm|m] [--json out.json]

Every part is one mesh node. Checks (all distances in inches):
  hygiene      part is a closed solid with positive volume
  through      part has through-openings (genus > 0): a mortise or hole that breaks out the far side
  interference two parts overlap by more than 0.0005 in^3
  near_miss    faces of two joined parts look at each other 0.08 to 0.30 in apart: a shoulder,
               cheek or seat that should touch but doesn't (intended clearances are 1/64 to 1/16)
  empty_pocket a recess in a part that no neighbour fills, bigger than a panel-float gap
               (min section > 0.2 in): leftover holes, unfilled mortises, stray features
  protrude     an inserted part (tenon, tang, spline, tongue, dowel, peg) sticks out of its host
  cross_grain  two solid-wood parts glued with crossing grain over more than --max-cross in (default 4):
               the joint will crack or split as the wider part moves. Fix: buttons/clips, slotted screws,
               breadboard glued in the middle only, floating panel, or declare it in the spec's movement_ok
  end_grain    two wood parts meet only end grain to long grain with no tenon, dowel, spline or fastener:
               a butt joint that won't hold
  panel_room   a floating panel (or drawer bottom, slat) has less room in its groove across the grain than
               the wood will move: width x coefficient x MC swing (tangential for flatsawn, radial for
               quartersawn, their mean for rift; a ripped-and-flipped glue-up moves the same total amount)
  thin_web     (with --min-web, default 1/4 in) a solid-wood part whose body is held together by a web or
               neck thinner than about 0.8 x min-web: two grooves meeting at a corner post, a panel groove
               over a rabbet, a mortise breaking into a groove. Found by eroding a voxel copy of the part and
               looking for a split; the reported thickness is approximate, so confirm with a section
  grain        (info, with --grain) the grain direction assumed for each wood part
Wood parts: grain = longest axis unless the spec says otherwise. Parts named like hardware (screw, bolt,
hinge, steel, brass, sheet, plate, pin) and plywood/MDF are left out of the wood-movement checks.

Spec file (--spec project.json), all keys optional:
  {"species": "walnut", "cut": "flat", "mc_swing": 4, "max_cross": 4,
   "parts": {"REGEX": {"grain": "x|y|z", "role": "wood|floating|insert|fastener|hardware|ply|ignore",
                       "material": "plywood|mdf|baltic birch|steel|brass|glass ... (sets the role)",
                       "species": "cedar ... (per part)", "cut": "flat|rift|quarter"}},
   "movement_ok": [["REGEX_A", "REGEX_B", "why: e.g. slotted screws at the back"]],
   "allow": [["REGEX_A", "REGEX_B", "why the gap is intended"]],
   "skip": "REGEX of parts to leave out",
   "min_web": 0.25}           (thinnest web for thin_web; also per part, e.g. 1/8 for small box parts, 0 = off)
Exit code 1 if anything is flagged. Requires: trimesh, manifold3d, numpy, scipy, rtree, networkx.
"""
import argparse, json, re, sys, warnings, logging
warnings.filterwarnings("ignore")
logging.getLogger("trimesh").setLevel(logging.ERROR)
import numpy as np
import trimesh
import manifold3d as mf

PANEL_RE = re.compile(r"(panel|drawer_?bottom|bottom_?panel|back_?board|backboard|slat|shiplap)", re.I)  # float by design
HARDWARE_RE = re.compile(r"(screw|bolt|nut|washer|hinge|steel|brass|bronze|stainless|iron|sheet|plate|pin\b|_pin|knob|pull|"
                         r"glass|mirror|magnet|catch|leaf)", re.I)
PLY_RE = re.compile(r"(ply|mdf|veneered|hardboard|particle)", re.I)
FASTENER_RE = re.compile(r"(button|clip|figure.?8|fig8|z.?clip|cleat|desktop.?fastener)", re.I)
ALLOW = []                               # (regexA, regexB) pairs whose gaps are intended, from --allow
MOVE_OK = []                             # (regexA, regexB) pairs attached in a way that allows movement
SPEC = {"parts": {}}
UP = np.array([0.0, 0.0, 1.0])          # set by --up; glTF/GLB from Blender is Y up

# Approximate dimensional-change coefficients per 1% moisture change (USDA Wood Handbook, flatsawn = tangential)
SPECIES = {"walnut": (0.00190, 0.00274), "cherry": (0.00126, 0.00248), "white oak": (0.00180, 0.00365),
           "red oak": (0.00158, 0.00369), "hard maple": (0.00165, 0.00353), "soft maple": (0.00133, 0.00289),
           "ash": (0.00169, 0.00274), "mahogany": (0.00172, 0.00238), "poplar": (0.00158, 0.00289),
           "hickory": (0.00259, 0.00411), "beech": (0.00190, 0.00431), "birch": (0.00256, 0.00338),
           "sapele": (0.00170, 0.00240), "teak": (0.00101, 0.00186), "pine": (0.00122, 0.00213),
           # cedars: western red from the Wood Handbook table; aromatic (eastern red) and Spanish cedar
           # derived from published green-to-oven-dry shrinkage / ~30% FSP, so treat as approximate
           "western red cedar": (0.00111, 0.00234), "aromatic cedar": (0.00103, 0.00157),
           "eastern red cedar": (0.00103, 0.00157), "spanish cedar": (0.00137, 0.00210),
           "cedar": (0.00103, 0.00157), "white pine": (0.00071, 0.00212), "alder": (0.00151, 0.00256),
           "elm": (0.00144, 0.00338), "padauk": (0.00110, 0.00180), "wenge": (0.00230, 0.00310)}
CUTS = ("flat", "flatsawn", "plain", "rift", "riftsawn", "quarter", "quartersawn", "qs")


def part_spec(n, key, default=None):
    """a per-part spec value (species, cut, ...) from the first matching parts regex, else the project value"""
    for rx, v in SPEC.get("parts", {}).items():
        if re.search(rx, n) and key in v:
            return v[key]
    return SPEC.get(key, default)


def move_coef(n):
    """dimensional change per 1% MC across the face width of part n.
    flatsawn -> tangential, quartersawn -> radial, rift -> the mean of the two.
    A glue-up of narrow or ripped-and-flipped strips keeps the same total movement (it only spreads cupping),
    so it does not change this number."""
    name = str(part_spec(n, "species", "walnut")).lower()
    r, t = SPECIES.get(name, SPECIES["walnut"])
    cut = str(part_spec(n, "cut", "flat")).lower()
    if cut.startswith("q"):
        return r, f"{name}, quartersawn"
    if cut.startswith("rift"):
        return (r + t) / 2, f"{name}, rift"
    return t, name


def part_info(n, mesh):
    """role and grain axis (unit vector) for a part, from the spec first, then from its name and shape."""
    role, grain = None, None
    for rx, v in SPEC.get("parts", {}).items():
        if re.search(rx, n):
            role = v.get("role", role)
            mat = str(v.get("material", "")).lower()
            if mat in ("ply", "plywood", "baltic birch", "mdf", "hardboard", "particleboard", "veneered ply", "sheet"):
                role = "ply"          # sheet goods don't move: left out of the wood-movement checks
            elif mat in ("steel", "brass", "bronze", "stainless", "aluminium", "aluminum", "glass", "metal"):
                role = "hardware"
            g = v.get("grain")
            if g in ("x", "y", "z"):
                grain = np.eye(3)["xyz".index(g)]
    if role is None:
        if re.match(r"(deco|decor|cosmetic)_", n, re.I):
            role = "ignore"
        elif HARDWARE_RE.search(n):
            role = "hardware"
        elif PLY_RE.search(n):
            role = "ply"
        elif FASTENER_RE.search(n):
            role = "fastener"
        elif INSERT_RE.search(n):
            role = "insert"
        elif PANEL_RE.search(n):
            role = "floating"
        else:
            role = "wood"
    if grain is None:
        try:
            obb = mesh.bounding_box_oriented
            ext = obb.primitive.extents
            R = obb.primitive.transform[:3, :3]
            order = np.argsort(ext)[::-1]
            grain = R[:, order[0]] if ext[order[0]] > 1.15 * ext[order[1]] else None
        except Exception:
            grain = None
    return role, grain


def contact(pm, qm, n=6000, tol=0.004):
    """points on pm that touch qm face to face, with pm's outward normals there"""
    pts, fi = trimesh.sample.sample_surface_even(pm, n, seed=3)
    if len(pts) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3)), 0.0
    cp, d, tri = trimesh.proximity.closest_point(qm, pts)
    nrm = pm.face_normals[fi]
    ok = (d < tol) & (np.einsum("ij,ij->i", nrm, qm.face_normals[tri]) < -0.9)
    return pts[ok], nrm[ok], pm.area * ok.mean()


def allowed_move(a, b):
    return any((re.search(x, a) and re.search(y, b)) or (re.search(x, b) and re.search(y, a)) for x, y in MOVE_OK)


def allowed(a, b):
    return any((re.search(x, a) and re.search(y, b)) or (re.search(x, b) and re.search(y, a)) for x, y in ALLOW)


INSERT_RE = re.compile(r"(tenon|tang|spline|tongue|dowel|peg|key|wedge)", re.I)
SCALE = {"in": 1.0, "mm": 1 / 25.4, "m": 1 / 0.0254}


def load_parts(path, units):
    s = trimesh.load(path, force="scene")
    parts = {}
    for node in s.graph.nodes_geometry:
        T, g = s.graph[node]
        m = s.geometry[g].copy()
        m.apply_transform(T)
        m.apply_scale(SCALE[units])
        if not m.is_watertight:  # glTF splits vertices at UV/normal seams; weld them (0.0001 in)
            w = m.copy()
            w.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=4)
            trimesh.repair.fix_normals(w)
            if w.is_watertight:
                m = w
        parts[node] = m
    return parts


def to_manifold(m):
    try:
        mm = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                                 tri_verts=np.asarray(m.faces, np.uint32)))
        return mm if mm.status() == mf.Error.NoError and not mm.is_empty() else None
    except Exception:
        return None


def from_manifold(mm):
    me = mm.to_mesh()
    return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)


def hull(m):
    return to_manifold(m.convex_hull)


def boxes_touch(a, b, pad=0.31):
    return np.all(a.bounds[0] - pad <= b.bounds[1]) and np.all(b.bounds[0] - pad <= a.bounds[1])


def min_section(mesh):
    try:
        ext = mesh.bounding_box_oriented.primitive.extents
        return float(min(ext))
    except Exception:
        return float(min(mesh.extents))


def run(parts, near_lo=0.08, near_hi=0.30):
    flags = []
    names = sorted(parts)
    M = {n: to_manifold(parts[n]) for n in names}
    for n in names:
        m = parts[n]
        if M[n] is None or not m.is_watertight or m.volume <= 0:
            flags.append(dict(check="hygiene", part=n, detail="not a closed solid (open edges or bad normals)"))
            continue
        # genus from Euler characteristic of each closed shell
        g = M[n].genus()
        bodies = len(M[n].decompose())
        if bodies > 1:
            flags.append(dict(check="hygiene", part=n, detail=f"{bodies} separate bodies in one part; split it or confirm"))
    nb = {n: [o for o in names if o != n and boxes_touch(parts[n], parts[o])] for n in names}
    for n in names:
        if M[n] is None or M[n].genus() <= 0 or len(M[n].decompose()) > 1:
            continue
        k = breakouts(parts[n], M[n], [M[o] for o in nb[n] if M[o] is not None and HARDWARE_RE.search(o)])  # bolts fill their holes
        if k:
            flags.append(dict(check="through", part=n, detail=f"{k} opening(s) break out the far side; confirm each is drawn as a through cut"))
    seen = set()
    for a in names:
        for b in nb[a]:
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            v = (M[a] ^ M[b]).volume() if M[a] is not None and M[b] is not None else 0
            if v > 5e-4:
                flags.append(dict(check="interference", part=a, other=b, detail=f"overlap {v:.4f} in^3"))
            # near-miss facing faces, only between parts that are joined (touch somewhere)
            if PANEL_RE.search(a) or PANEL_RE.search(b) or allowed(a, b) \
                    or HARDWARE_RE.search(a) or HARDWARE_RE.search(b):
                continue
            _, dmin, _ = trimesh.proximity.closest_point(parts[b], parts[a].vertices[:: max(1, len(parts[a].vertices) // 3000)])
            if dmin.min() > 0.02:
                continue
            for p, q in ((a, b), (b, a)):
                pm, qm = parts[p], parts[q]
                pts, fi = trimesh.sample.sample_surface_even(pm, 4000, seed=1) if pm.area > 0 else (None, None)
                if pts is None or len(pts) == 0:
                    continue
                cp, d, tri = trimesh.proximity.closest_point(qm, pts)
                facing = np.einsum("ij,ij->i", pm.face_normals[fi], qm.face_normals[tri]) < -0.8
                # straight across only: a point beside the other face finds its edge at a slant (a drawer
                # end running 1/64 past a tapered leg is not a 0.2 in gap)
                along = np.einsum("ij,ij->i", pm.face_normals[fi], cp - pts) > 0.95 * d
                hit = facing & along & (d > near_lo) & (d < near_hi)
                if hit.any():   # a gap that a third part fills (crossing tenons in a leg) is not a miss
                    mid = (pts[hit] + cp[hit]) / 2
                    occ = np.zeros(len(mid), bool)
                    for o in set(nb[p]) & set(nb[q]):
                        if parts[o].is_watertight:
                            occ |= parts[o].contains(mid)
                    idx = np.where(hit)[0]
                    hit[idx[occ]] = False
                if hit.sum() >= 3:   # a sliver (e.g. the 1/32 end clearance where two mortises cross) is not a face
                    X = pts[hit] - pts[hit].mean(0)
                    w = np.linalg.svd(X, full_matrices=False)[2]
                    spans = [np.ptp(X @ w[i]) for i in range(2)]
                    if min(spans) < 0.1:
                        hit[:] = False
                area = pm.area * hit.mean()
                if area > 0.15:
                    flags.append(dict(check="near_miss", part=p, other=q,
                                      detail=f"{area:.2f} in^2 of face stands {np.median(d[hit]):.3f} in off {q}"))
    flags += wood_checks(parts, names, nb, M)
    # empty pockets and protrusions
    for n in names:
        if M[n] is None:
            continue
        H = hull(parts[n])
        if H is None:
            continue
        cav = H - M[n]
        if part_info(n, parts[n])[0] == "insert":      # a decorative spline or faux peg set to "ignore" is skipped
            hosts = [o for o in nb[n] if not INSERT_RE.search(o)]
            if hosts:
                hh = [hull(parts[o]) for o in hosts]
                hh = [h for h in hh if h is not None]
                out = M[n] - mf.Manifold.batch_boolean(hh, mf.OpType.Add) if hh else M[n]
                if out.volume() > 2e-3:
                    flags.append(dict(check="protrude", part=n, detail=f"{out.volume():.3f} in^3 sits outside every host"))
        if cav.volume() < 0.005:
            continue
        broken = [o for o in nb[n] if M[o] is None]
        if broken:
            flags.append(dict(check="skipped", part=n, detail="pocket check skipped: neighbour(s) not closed: " + ", ".join(broken)))
            continue
        others = [M[o] for o in nb[n] if M[o] is not None]
        if others:
            cav = cav - mf.Manifold.batch_boolean(others, mf.OpType.Add)
        if cav.is_empty():
            continue
        floaters = [parts[o] for o in nb[n] if PANEL_RE.search(o) or part_info(o, parts[o])[0] == "floating"]
        for comp in cav.decompose():
            c = from_manifold(comp)
            if floaters and any(trimesh.proximity.closest_point(f, c.vertices)[1].max() < 0.3 for f in floaters):
                continue   # just the expansion room around a floating panel
            t_eff = 2 * abs(c.volume) / max(c.area, 1e-9)   # effective thickness: thin leftover gaps are clearances
            if abs(c.volume) > 0.02 and min_section(c) > 0.2 and t_eff > 0.08 and not touches_hull_boundary_only(c, parts[n]):
                ctr = c.bounds.mean(axis=0)
                flags.append(dict(check="empty_pocket", part=n,
                                  detail=f"{abs(c.volume):.3f} in^3 unfilled recess near ({ctr[0]:.2f}, {ctr[1]:.2f}, {ctr[2]:.2f}), section {min_section(c):.2f} in"))
    return flags


def wood_checks(parts, names, nb, M):
    flags = []
    info = {n: part_info(n, parts[n]) for n in names}
    fastened = {n for n in names if any(info[o][0] == "fastener" for o in nb[n])}
    for n in names:
        role, g = info[n]
        if role in ("wood", "floating") and g is None:
            ext = np.sort(parts[n].extents)
            if ext[1] > 6:
                flags.append(dict(check="grain_unknown", part=n,
                                  detail=f"{ext[2]:.1f} x {ext[1]:.1f} in, grain can't be told from the shape; set it in the spec"))
    swing = float(SPEC.get("mc_swing", 4))
    max_cross = float(SPEC.get("max_cross", 4))
    wood = {"wood", "floating", "insert", "fastener"}
    seen = set()
    for a in names:
        for b in nb[a]:
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            ra, ga = info[a]
            rb, gb = info[b]
            if ra not in wood or rb not in wood or "ignore" in (ra, rb) or allowed(a, b):
                continue
            small, big = (a, b) if parts[a].area <= parts[b].area else (b, a)
            pa, na, area = contact(parts[small], parts[big], n=8000)
            if area < 0.05:
                continue
            # bridged by a joint part (tenon, dowel, spline) or a movement fastener (button, clip)?
            common = set(nb[a]) & set(nb[b])
            bridged = [o for o in common if info[o][0] in ("insert", "fastener")]
            held = bridged + [o for o in common if info[o][0] == "hardware"]
            # --- cross-grain glue ---
            if ga is not None and gb is not None and abs(ga @ gb) < 0.35 and "fastener" not in (ra, rb) \
                    and "floating" not in (ra, rb) and not allowed_move(a, b) \
                    and not any(info[o][0] == "fastener" for o in bridged) and not ({a, b} & fastened):
                inplane = (np.abs(na @ ga) < 0.3) & (np.abs(na @ gb) < 0.3)
                P, Nn = pa[inplane], na[inplane]
                if len(P) > 20:
                    nn = np.median(Nn, axis=0)
                    nn /= np.linalg.norm(nn)
                    span = 0.0
                    for g in (ga, gb):
                        c = np.cross(nn, g)
                        if np.linalg.norm(c) > 0.5:
                            c /= np.linalg.norm(c)
                            pr = P @ c
                            span = max(span, float(np.percentile(pr, 99) - np.percentile(pr, 1)))
                    if span > max_cross:
                        mv = span * max(move_coef(a)[0], move_coef(b)[0]) * swing
                        flags.append(dict(check="cross_grain", part=a, other=b,
                                          detail=f"glued with crossing grain over {span:.1f} in (moves about {mv:.3f} in): "
                                                 f"use buttons/clips, slotted screws, glue the middle only, or float it"))
            # --- end-grain butt with no joint ---
            interlock = reaches_into(parts[a], parts[b], M[a]) or reaches_into(parts[b], parts[a], M[b])
            if not held and not interlock and "floating" not in (ra, rb) and "fastener" not in (ra, rb) and "insert" not in (ra, rb):
                side = np.abs(na @ UP) < 0.8          # contacts facing up/down are parts resting on each other
                pa, na = pa[side], na[side]
                if len(pa) < 20:
                    continue
                area = area * side.mean() if len(side) else 0
                endg = np.zeros(len(pa), bool)
                for g in (ga, gb):
                    if g is not None:
                        endg |= np.abs(na @ g) > 0.8
                lg_area = area * (1 - endg.mean()) if len(pa) else 0
                if endg.mean() > 0.95 and lg_area < 0.05:
                    flags.append(dict(check="end_grain", part=a, other=b,
                                      detail=f"{area:.1f} in^2 end grain to long grain with no tenon, dowel or spline: a butt joint"))
    # --- floating panel room ---
    for n in names:
        role, g = info[n]
        if role != "floating" or g is None:
            continue
        m = parts[n]
        c = np.cross(g, np.eye(3)[np.argmin(np.abs(np.eye(3) @ g))])  # any perpendicular, refined below
        # cross-grain direction in the panel's plane = the OBB axis that is neither grain nor thickness
        try:
            obb = m.bounding_box_oriented
            R, ext = obb.primitive.transform[:3, :3], obb.primitive.extents
            axes = [R[:, i] for i in range(3)]
            thick = int(np.argmin(ext))
            cands = [i for i in range(3) if i != thick and abs(axes[i] @ g) < 0.7]
            if not cands:
                continue
            c = axes[cands[0]]
            width = ext[cands[0]]
        except Exception:
            continue
        coef, label = move_coef(n)
        need = width * coef * swing / 2
        hosts = [parts[o] for o in nb[n] if info[o][0] not in ("hardware", "ignore")]
        if not hosts:
            continue
        host = trimesh.util.concatenate(hosts)
        pts, fi = trimesh.sample.sample_surface_even(m, 4000, seed=4)
        nr = m.face_normals[fi]
        gaps = []
        for sgn in (1, -1):
            sel = (nr @ (sgn * c)) > 0.95
            if sel.sum() < 5:
                gaps.append(None)
                continue
            origins = pts[sel] + 1e-4 * sgn * c
            locs, ri, _ = host.ray.intersects_location(origins, np.tile(sgn * c, (len(origins), 1)), multiple_hits=False)
            d = np.full(len(origins), np.inf)
            if len(ri):
                d[ri] = np.minimum(d[ri], np.linalg.norm(locs - origins[ri], axis=1))
            gaps.append(float(np.median(d)))
        if None in gaps or np.inf in gaps:
            continue                     # an open edge (e.g. a drawer bottom running out under the back) can move freely
        if sum(gaps) < 2 * need:
            flags.append(dict(check="panel_room", part=n,
                              detail=f"{gaps[0]:.3f} + {gaps[1]:.3f} in of room across the grain; a {width:.1f} in wide panel "
                                     f"moves about {2 * need:.3f} in ({label}, {swing:g}% MC swing)"))
    return flags


def reaches_into(pa, pb, ma):
    """does part a reach into part b's outline (a tenon, tongue, dado fit)? works on open meshes too"""
    hb = hull(pb)
    if ma is not None and hb is not None:
        return (ma ^ hb).volume() > 0.01
    try:
        sd = trimesh.proximity.signed_distance(pb.convex_hull, pa.vertices[:: max(1, len(pa.vertices) // 2000)])
        return bool((sd > 0.05).any())
    except Exception:
        return True   # can't tell: don't accuse it of being a butt joint


def grain_report(parts):
    for n in sorted(parts):
        role, g = part_info(n, parts[n])
        gs = "?" if g is None else "xyz"[int(np.argmax(np.abs(g)))]
        print(f"  [grain] {n}: role {role}, grain {gs}")


def breakouts(mesh, mm, others):
    """count cavity regions (hull minus part, minus what neighbours fill) that span the whole part along one of its axes"""
    H = hull(mesh)
    if H is None:
        return 0
    cav = H - mm
    if others:
        cav = cav - mf.Manifold.batch_boolean(others, mf.OpType.Add)
    try:
        obb = mesh.bounding_box_oriented
        R, ext = obb.primitive.transform[:3, :3], obb.primitive.extents
    except Exception:
        return 0
    k = 0
    for comp in cav.decompose():
        if comp.volume() < 1e-3:
            continue
        v = np.asarray(comp.to_mesh().vert_properties)[:, :3] @ R
        span = v.max(0) - v.min(0)
        if np.any(span >= 0.98 * ext) and np.min(span) < 0.9 * np.max(ext):
            k += 1
    return k


def touches_hull_boundary_only(c, part):
    """A hull-minus-part region that is just the outside of a tapered or angled part (e.g. a leg taper) is not a pocket:
    such regions have less than 60% of their surface lying on the part itself."""
    try:
        pts, _ = trimesh.sample.sample_surface_even(c, 600, seed=2)
        _, d, _ = trimesh.proximity.closest_point(part, pts)
        return (d < 1e-3).mean() < 0.6
    except Exception:
        return False


def voxelize(m, pitch):
    """Solid voxel grid of a closed mesh by casting one ray per column along its longest axis and filling
    between entry and exit hits. Returns (bool array indexed x, y, z, origin of voxel [0,0,0] centre)."""
    lo, hi = m.bounds
    ax = int(np.argmax(hi - lo)); o1, o2 = [i for i in range(3) if i != ax]
    j = pitch * 0.0137                                       # stay off exact edges and vertices
    origin = lo + pitch / 2 + j
    n = np.maximum(1, np.ceil((hi - lo) / pitch).astype(int))
    g1, g2 = np.meshgrid(np.arange(n[o1]), np.arange(n[o2]), indexing="ij")
    starts = np.zeros((g1.size, 3))
    starts[:, o1] = origin[o1] + g1.ravel() * pitch
    starts[:, o2] = origin[o2] + g2.ravel() * pitch
    starts[:, ax] = lo[ax] - 1.0
    dirs = np.zeros_like(starts); dirs[:, ax] = 1.0
    loc, ri, _ = m.ray.intersects_location(starts, dirs, multiple_hits=True)
    grid = np.zeros(tuple(n), bool)
    if len(ri) == 0:
        return grid, origin
    order = np.lexsort((loc[:, ax], ri)); ri, t = ri[order], loc[order, ax]
    zc = origin[ax] + np.arange(n[ax]) * pitch
    for r in np.unique(ri):
        h = t[ri == r]
        h = h[np.concatenate(([True], np.diff(h) > 1e-7))]   # drop duplicate hits on shared edges
        col = np.zeros(n[ax], bool)
        for a, b in zip(h[0::2], h[1::2]):
            col |= (zc >= a) & (zc <= b)
        i1, i2 = np.unravel_index(r, (n[o1], n[o2]))
        idx = [slice(None)] * 3; idx[o1] = i1; idx[o2] = i2
        grid[tuple(idx)] = col
    return grid, origin


def thin_webs(parts, min_web=0.25, factor=0.8, slab=1.0):
    """Erode each solid-wood part by factor*min_web/2 and look, one 1 in slab at a time along its length,
    for material that comes loose: anything thinner than about factor*min_web was holding it on.
    Working in slabs finds necks that only run part of the length (stopped grooves, a mortise breaking
    into a groove) as well as full-length ones."""
    from scipy import ndimage
    from scipy.spatial import cKDTree
    flags = []
    st = np.ones((3, 3, 3))
    default = min_web
    for n in sorted(parts):
        m = parts[n]
        role, _ = part_info(n, m)
        min_web = float(part_spec(n, "min_web", default) or 0)
        if role != "wood" or not min_web or not m.is_watertight or m.volume <= 0:
            continue
        r = factor * min_web / 2
        pitch = min_web / 12
        while np.prod(m.extents / pitch) > 8e6:
            pitch *= 1.25
        try:
            grid, origin = voxelize(m, pitch)
        except Exception:
            continue
        solid = np.pad(grid, 1)
        dist = ndimage.distance_transform_edt(solid) * pitch - pitch / 2
        core = dist > r
        ax = int(np.argmax(core.shape))
        L = core.shape[ax]
        w = max(4, int(round(slab / pitch)))
        keep = 0.004 * slab
        hits = []
        for s0 in range(0, max(1, L - w // 2), w // 2):
            sl = [slice(None)] * 3; sl[ax] = slice(s0, min(L, s0 + w))
            sub = core[tuple(sl)]
            if not sub.any():
                continue
            lab, k = ndimage.label(sub, structure=st)
            if k < 2:
                continue
            sizes = ndimage.sum(sub, lab, range(1, k + 1)) * pitch ** 3
            big = [i + 1 for i in np.argsort(sizes)[::-1] if sizes[i] >= keep]
            if len(big) < 2:
                continue
            a = np.argwhere(lab == big[0]); b = np.argwhere(lab == big[1])
            rng = np.random.default_rng(0)
            if len(a) > 20000: a = a[rng.choice(len(a), 20000, replace=False)]
            d, j = cKDTree(b).query(a)
            i = int(np.argmin(d)); pa, pb = a[i], b[j[i]]
            off = np.zeros(3, int); off[ax] = s0
            pa, pb = pa + off, pb + off
            seg = np.rint(pa[None] + (pb - pa)[None] * np.linspace(0, 1, 25)[:, None]).astype(int)
            vals = [dist[tuple(q)] for q in seg if solid[tuple(q)]]
            neck = 2 * max(0.0, float(min(vals))) if vals else 0.0
            hits.append((neck, origin + ((pa + pb) / 2 - 1) * pitch, s0))
        if not hits:
            continue
        neck, where, _ = min(hits, key=lambda h: h[0])
        span = (len(hits) * (w // 2) + w // 2) * pitch
        flags.append(dict(check="thin_web", part=n,
                          detail=f"a web or neck about {neck:.2f} in thick (target {min_web:g} in) holds part of the "
                                 f"section on, near {where.round(2).tolist()}, over about {span:.1f} in of length; cut a section there"))
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--only")
    ap.add_argument("--skip")
    ap.add_argument("--units", default="in", choices=SCALE)
    ap.add_argument("--json")
    ap.add_argument("--allow", action="append", default=[], help="REGEX_A~REGEX_B: gap between these is intended")
    ap.add_argument("--spec", help="project spec JSON: species, grain overrides, roles, movement_ok, allow")
    ap.add_argument("--species")
    ap.add_argument("--grain", action="store_true", help="print the grain direction assumed for each part")
    ap.add_argument("--min-web", type=float, default=0.25, help="thinnest web or neck allowed in a solid-wood part, inches (0 turns the check off)")
    ap.add_argument("--up", choices=["x", "y", "z", "auto"], default="auto", help="vertical axis; auto = y for glb/gltf, z otherwise")
    a = ap.parse_args()
    up = a.up if a.up != "auto" else ("y" if a.model.lower().endswith((".glb", ".gltf")) else "z")
    UP[:] = np.eye(3)["xyz".index(up)]
    ALLOW.extend(tuple(x.split("~", 1)) for x in a.allow)
    if a.spec:
        SPEC.update(json.load(open(a.spec)))
        ALLOW.extend((p[0], p[1]) for p in SPEC.get("allow", []))
        MOVE_OK.extend((p[0], p[1]) for p in SPEC.get("movement_ok", []))
        if SPEC.get("skip"):
            a.skip = SPEC["skip"] if not a.skip else f"(?:{a.skip})|(?:{SPEC['skip']})"
    if a.species:
        SPEC["species"] = a.species
    parts = load_parts(a.model, a.units)
    if a.only:
        parts = {k: v for k, v in parts.items() if re.search(a.only, k)}
    if a.skip:
        parts = {k: v for k, v in parts.items() if not re.search(a.skip, k)}
    if a.grain:
        grain_report(parts)
    flags = run(parts)
    mw = SPEC.get("min_web", a.min_web)
    if mw:
        flags += [f for f in thin_webs(parts, mw) if not any(re.search(x[0], f["part"]) and x[1] in ("thin_web", "*") for x in ALLOW)]
    print(f"{len(parts)} parts checked, {len(flags)} flag(s)")
    for f in flags:
        o = f" vs {f['other']}" if "other" in f else ""
        print(f"  [{f['check']}] {f['part']}{o}: {f['detail']}")
    if a.json:
        json.dump(flags, open(a.json, "w"), indent=1)
    sys.exit(1 if any(f["check"] != "skipped" for f in flags) else 0)


if __name__ == "__main__":
    main()

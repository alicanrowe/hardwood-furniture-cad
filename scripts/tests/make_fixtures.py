#!/usr/bin/env python3
"""Builds test furniture (inches, Z up) in good and bad versions, each bad one with known mistakes.
Writes fixtures/<name>.glb. Run cadcheck on each with --up z --units in (see run_tests.py)."""
import os, sys
import numpy as np, trimesh, manifold3d as mf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
os.makedirs(OUT, exist_ok=True)


def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def U(*ms):
    return mf.Manifold.batch_boolean(list(ms), mf.OpType.Add)


def save(name, parts):
    sc = trimesh.Scene()
    for n, m in parts.items():
        me = m.to_mesh()
        tm = trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts))
        sc.add_geometry(tm, node_name=n, geom_name=n)
    sc.export(os.path.join(OUT, name + ".glb"))


# ---------------------------------------------------------------- table
def table(bad):
    L, W, H, S = 36.0, 20.0, 29.25, 1.75     # base footprint, leg height, leg section
    T, AH, AT = 0.75, 4.0, 0.75               # top thickness, apron height, apron thickness
    inset = 0.25                              # apron face set back from leg face
    tl, tt, th = 1.0, 0.25, 3.0               # tenon length, thickness, height
    p = {}
    legs = {"FL": (0, 0), "FR": (L - S, 0), "BL": (0, W - S), "BR": (L - S, W - S)}
    mort = []
    aprons = {}
    za0, za1 = H - AH, H
    # long aprons (along x), front y=inset..inset+AT, back
    for nm, y0 in (("Front", inset), ("Back", W - inset - AT)):
        a = box(S, L - S, y0, y0 + AT, za0, za1)
        yc = y0 + AT / 2
        for xe, sg in ((S, -1), (L - S, 1)):
            if bad and nm == "Front" and sg == 1:
                continue                      # BAD: front apron butted to the right leg, no tenon
            x0, x1 = (xe - tl, xe) if sg < 0 else (xe, xe + tl)
            ten = box(x0, x1, yc - tt / 2, yc + tt / 2, za0 + 0.5, za0 + 0.5 + th)
            a = a + ten
            mort.append(box(x0 - (1 / 32 if sg < 0 else 0), x1 + (1 / 32 if sg > 0 else 0), yc - tt / 2, yc + tt / 2, za0 + 0.5, za0 + 0.5 + th))
        aprons["Apron_" + nm] = a
    for nm, x0 in (("L", inset), ("R", L - inset - AT)):
        a = box(x0, x0 + AT, S, W - S, za0, za1)
        xc = x0 + AT / 2
        for ye, sg in ((S, -1), (W - S, 1)):
            y0, y1 = (ye - tl, ye) if sg < 0 else (ye, ye + tl)
            ten = box(xc - tt / 2, xc + tt / 2, y0, y1, za0 + 0.5, za0 + 0.5 + th)
            a = a + ten
            depth = (1 / 32)
            if bad and nm == "L" and sg < 0:
                depth = 0.0
                mort.append(box(xc - tt / 2, xc + tt / 2, -0.1, y1, za0 + 0.5, za0 + 0.5 + th))  # BAD: mortise through the leg
            mort.append(box(xc - tt / 2, xc + tt / 2, y0 - (depth if sg < 0 else 0), y1 + (depth if sg > 0 else 0), za0 + 0.5, za0 + 0.5 + th))
        aprons["Apron_" + nm] = a
    for k, (x, y) in legs.items():
        leg = box(x, x + S, y, y + S, 0, H)
        for m in mort:
            leg = leg - m
        if bad and k == "BR":
            leg = leg - mf.Manifold.cylinder(1.0, 0.1875, 0.1875, 24).rotate([0, 90, 0]).translate([x + S - 0.99, y + S / 2, 12])  # BAD: stray dowel hole
        p["Leg_" + k] = leg
    p.update(aprons)
    p["Top"] = box(-2, L + 2, -2, W + 2, H, H + T)
    if not bad:   # buttons in a 1/4 x 3/8 slot on the inside of the long aprons
        for i, x in enumerate((8, 18, 28)):
            for nm, y0, sg in (("Front", inset + AT, 1), ("Back", W - inset - AT, -1)):
                slot = box(x - 0.75, x + 0.75, min(y0, y0 - sg * 0.375), max(y0, y0 - sg * 0.375), H - 0.75, H - 0.5)
                aprons["Apron_" + nm] = aprons["Apron_" + nm] - slot
                yb0, yb1 = sorted((y0, y0 + sg * 1.0))
                btn = box(x - 0.75, x + 0.75, yb0, yb1, H - 0.75, H) + box(x - 0.75, x + 0.75, min(y0, y0 - sg * 0.3125), max(y0, y0 - sg * 0.3125), H - 0.75, H - 0.5)
                p[f"Button_{nm}_{i}"] = btn
        p.update(aprons)
    return p


# ---------------------------------------------------------------- chair
def chair(bad):
    W, D, S = 18.0, 16.0, 1.5
    p = {}
    morts = {k: [] for k in ("FL", "FR", "BL", "BR")}
    legpos = {"FL": (0, 0, 17.5), "FR": (W - S, 0, 17.5), "BL": (0, D - S, 36), "BR": (W - S, D - S, 36)}

    def rail(name, axis, fixed, z0, h, t, a_leg, b_leg, ten_h=None, gap_b=0.0):
        ten_h = ten_h or h - 0.75
        mt_h = h - 0.75
        if axis == "x":
            y0 = fixed
            r = box(S, W - S - gap_b, y0, y0 + t, z0, z0 + h)
            yc = y0 + t / 2
            r = r + box(S - 0.6, S, yc - 0.125, yc + 0.125, z0 + 0.375, z0 + 0.375 + ten_h)
            r = r + box(W - S - gap_b, W - S + 0.6, yc - 0.125, yc + 0.125, z0 + 0.375, z0 + 0.375 + ten_h)
            morts[a_leg].append(box(S - 0.6 - 1 / 32, S, yc - 0.125, yc + 0.125, z0 + 0.375, z0 + 0.375 + mt_h))
            morts[b_leg].append(box(W - S, W - S + 0.6 + 1 / 32, yc - 0.125, yc + 0.125, z0 + 0.375, z0 + 0.375 + mt_h))
        else:
            x0 = fixed
            r = box(x0, x0 + t, S + gap_b, D - S, z0, z0 + h)
            xc = x0 + t / 2
            r = r + box(xc - 0.125, xc + 0.125, S - 0.6, S + gap_b, z0 + 0.375, z0 + 0.375 + ten_h)
            r = r + box(xc - 0.125, xc + 0.125, D - S, D - S + 0.6, z0 + 0.375, z0 + 0.375 + ten_h)
            morts[a_leg].append(box(xc - 0.125, xc + 0.125, S - 0.6 - 1 / 32, S, z0 + 0.375, z0 + 0.375 + mt_h))
            morts[b_leg].append(box(xc - 0.125, xc + 0.125, D - S, D - S + 0.6 + 1 / 32, z0 + 0.375, z0 + 0.375 + mt_h))
        p[name] = r

    rail("Rail_Front", "x", 0.375, 14.5, 3, 0.75, "FL", "FR")
    rail("Rail_Back", "x", D - S + 0.375, 14.5, 3, 0.75, "BL", "BR")
    rail("Rail_L", "y", 0.375, 14.5, 3, 0.75, "FL", "BL")
    rail("Rail_R", "y", W - S + 0.375, 14.5, 3, 0.75, "FR", "BR")
    rail("Stretcher_L", "y", 0.375, 5, 1.25, 0.75, "FL", "BL", gap_b=(0.125 if bad else 0.0))   # BAD: shoulder 1/8 off the front leg
    rail("Stretcher_R", "y", W - S + 0.375, 5, 1.25, 0.75, "FR", "BR")
    rail("Crest_Rail", "x", D - S + 0.375, 31, 3, 0.75, "BL", "BR", ten_h=(1.0 if bad else None))   # BAD: tenon 1 in tall in a 2 1/4 mortise
    for k, (x, y, h) in legpos.items():
        leg = box(x, x + S, y, y + S, 0, h)
        for m in morts[k]:
            leg = leg - m
        p["Leg_" + k] = leg
    return p


# ---------------------------------------------------------------- chest of drawers (case + one drawer)
def chest(bad):
    W, D, H, t = 30.0, 18.0, 32.0, 0.75
    p = {}
    side_L = box(0, t, 0, D, 0, H)
    side_R = box(W - t, W, 0, D, 0, H)
    # top and bottom in 1/4 deep dados, grain side to side; back in a 3/8 x 1/2 rabbet
    for z0 in (0.5, H - 0.5 - t):
        d = box(t - 0.25, W - t + 0.25, 0, D - 0.5, z0, z0 + t)
        side_L = side_L - d
        side_R = side_R - d
    rab = U(box(t - 0.375, t, D - 0.5, D, 0, H), box(W - t, W - t + 0.375, D - 0.5, D, 0, H))
    side_L, side_R = side_L - rab, side_R - rab
    p["Case_Bottom"] = box(t - 0.25, W - t + 0.25, 0, D - 0.5, 0.5, 0.5 + t)
    p["Case_Top"] = box(t - 0.25, W - t + 0.25, 0, D - 0.5, H - 0.5 - t, H - 0.5)
    # front drawer rail with stub tenons into the sides, runners behind it
    zr = 16.0
    rail = box(t, W - t, 0, 2, zr, zr + t) + box(t - 0.375, t, 0.5, 1.5, zr + 0.25, zr + 0.5) + box(W - t, W - t + 0.375, 0.5, 1.5, zr + 0.25, zr + 0.5)
    side_L = side_L - box(t - 0.375 - 1 / 32, t, 0.5, 1.5, zr + 0.25, zr + 0.5)
    side_R = side_R - box(W - t, W - t + 0.375 + 1 / 32, 0.5, 1.5, zr + 0.25, zr + 0.5)
    p["Drawer_Rail"] = rail
    # runners: housed in a 1/4 dado in each side, front end tenoned into the rail
    for nm, x0, x1, dx0, dx1 in (("L", t, t + 1.5, t - 0.25, t), ("R", W - t - 1.5, W - t, W - t, W - t + 0.25)):
        run = box(x0, x1, 2, D - 1.0, zr, zr + t) + box(dx0, dx1, 2, D - 1.0, zr, zr + t)
        xm = (x0 + x1) / 2
        run = run + box(xm - 0.125, xm + 0.125, 1.5, 2, zr + 0.125, zr + t - 0.125)      # stub tenon into the rail
        p["Drawer_Rail"] = p["Drawer_Rail"] - box(xm - 0.125, xm + 0.125, 1.5 - 1 / 32, 2, zr + 0.125, zr + t - 0.125)
        if nm == "L":
            side_L = side_L - box(dx0, dx1, 2, D - 1.0, zr, zr + t)
        else:
            side_R = side_R - box(dx0, dx1, 2, D - 1.0, zr, zr + t)
        p["Runner_" + nm] = run
    p["Side_L"], p["Side_R"] = side_L, side_R
    # back
    if bad:
        p["Back"] = box(t - 0.375, W - t + 0.375, D - 0.5, D - 0.125, 0.5, H - 0.5)   # BAD: one solid back glued in the rabbets
    else:
        n, x0 = 5, t - 0.375
        bw = (W - 2 * x0 - (n - 1) * 0.0625) / n
        for i in range(n):
            xa = x0 + i * (bw + 0.0625)
            p[f"Back_Board_{i + 1}"] = box(xa, xa + bw, D - 0.5, D - 0.125, 0.5, H - 0.5)
    # drawer: 1/2 sides housed in a 1/4 rabbet on the front, bottom floats in grooves
    dz0, dh, dw = zr + t + 0.0625, 6.0, W - 2 * t - 0.125
    dx0 = t + 0.0625
    front = box(dx0, dx0 + dw, -0.75, 0, dz0, dz0 + dh)
    ds = {}
    for nm, sx0 in (("L", dx0), ("R", dx0 + dw - 0.5)):
        s = box(sx0, sx0 + 0.5, 0, D - 2, dz0, dz0 + dh)
        if not bad:
            s = s + box(sx0 + (0.25 if nm == "L" else 0), sx0 + (0.5 if nm == "L" else 0.25), -0.375, 0, dz0, dz0 + dh)  # tongue
            front = front - box(sx0 + (0.25 if nm == "L" else 0), sx0 + (0.5 if nm == "L" else 0.25), -0.375 - 1 / 64, 0, dz0, dz0 + dh)
        ds[nm] = s
    # bottom groove 1/4 x 1/4, bottom 3/8 with a 1/4 tongue, grain side to side
    gz = dz0 + 0.5
    bot_room = 0.0156 if bad else 0.125   # BAD: bottom tight in the side grooves (grain runs front to back here)
    bx0, bx1 = dx0 + 0.25 + bot_room, dx0 + dw - 0.25 - bot_room
    for nm in ("L", "R"):
        sx0 = dx0 if nm == "L" else dx0 + dw - 0.5
        g = box(sx0 + (0.25 if nm == "L" else 0), sx0 + (0.5 if nm == "L" else 0.25), -0.375, D - 2, gz, gz + 0.25)
        ds[nm] = ds[nm] - g
    front = front - box(dx0 + 0.25, dx0 + dw - 0.25, -0.25, 0, gz, gz + 0.25)
    bot_y0, bot_y1 = -0.25 + 0.0625, D - 2.0
    p["Drawer_Bottom"] = box(bx0, bx1, bot_y0, bot_y1, gz, gz + 0.25)
    p["Drawer_Front"] = front
    p["Drawer_Side_L"], p["Drawer_Side_R"] = ds["L"], ds["R"]
    return p


# ---------------------------------------------------------------- frame-and-panel door
def door(bad):
    W, H, t, sw = 16.0, 30.0, 0.75, 2.25
    p = {}
    stiles = {"L": box(0, sw, 0, t, 0, H), "R": box(W - sw, W, 0, t, 0, H)}
    g = lambda x0, x1, z0, z1: box(x0, x1, t / 2 - 0.125, t / 2 + 0.125, z0, z1)
    # grooves 1/4 x 3/8
    stiles["L"] = stiles["L"] - g(sw - 0.375, sw, 0, H)
    stiles["R"] = stiles["R"] - g(W - sw, W - sw + 0.375, 0, H)
    for nm, z0 in (("Bot", 0), ("Top", H - sw)):
        r = box(sw, W - sw, 0, t, z0, z0 + sw)
        r = r + g(sw - 1.0, sw, z0 + 0.375, z0 + sw - 0.375) + g(W - sw, W - sw + 1.0, z0 + 0.375, z0 + sw - 0.375)
        r = r - (g(sw, W - sw, z0 + sw - 0.375, z0 + sw) if nm == "Bot" else g(sw, W - sw, z0, z0 + 0.375))
        stiles["L"] = stiles["L"] - g(sw - 1.0 - 1 / 32, sw, z0 + 0.375, z0 + sw - 0.375)
        stiles["R"] = stiles["R"] - g(W - sw, W - sw + 1.0 + 1 / 32, z0 + 0.375, z0 + sw - 0.375)
        p["Rail_" + nm] = r
    p["Stile_L"], p["Stile_R"] = stiles["L"], stiles["R"]
    room = 0.0156 if bad else 0.125    # BAD: 1/64 room across the grain on a 12 in oak panel
    p["Panel"] = g(sw - 0.375 + room, W - sw + 0.375 - room, sw - 0.375 + 0.0625, H - sw + 0.375 - 0.0625)
    return p


# ---------------------------------------------------------------- bed (headboard end + rails)
def bed(bad):
    W, P, L = 60.0, 3.0, 40.0
    p = {}
    posts = {"L": box(0, P, 0, P, 0, 48), "R": box(W - P, W, 0, P, 0, 48)}
    # headboard 3/4 in a 3/4 x 1/2 groove in each post, between two rails
    hb_z0, hb_z1 = 24.0, 44.0
    for k, x in (("L", P), ("R", W - P)):
        sgn = 1 if k == "L" else -1
        gx0, gx1 = sorted((x, x - sgn * 0.5))
        posts[k] = posts[k] - box(gx0, gx1, 1.125, 1.875, hb_z0, hb_z1)
    if bad:
        p["Headboard"] = box(P - 0.5, W - P + 0.5, 1.125, 1.875, hb_z0, hb_z1)   # BAD: solid headboard glued into post grooves
    else:
        p["Headboard_Panel"] = box(P - 0.5 + 0.125, W - P + 0.5 - 0.125, 1.125, 1.875, hb_z0, hb_z1)
        # with rails above and below, tenoned into the posts
    # side rails attached with bed bolts (hardware) and a short stub tenon
    for k, x0 in (("L", 0.5), ("R", W - 0.5 - 1.5)):
        r = box(x0, x0 + 1.5, P, P + L, 10, 17)
        p["Side_Rail_" + k] = r
        if not bad:
            p["Bed_Bolt_" + k] = mf.Manifold.cylinder(6, 0.1875, 0.1875, 16).rotate([90, 0, 0]).translate([x0 + 0.75, P + 3, 13.5])
            # bolt passes through rail and post
            p["Side_Rail_" + k] = p["Side_Rail_" + k] - mf.Manifold.cylinder(3, 0.1875, 0.1875, 16).rotate([90, 0, 0]).translate([x0 + 0.75, P + 3, 13.5])
            posts[k] = posts[k] - mf.Manifold.cylinder(3, 0.1875, 0.1875, 16).rotate([90, 0, 0]).translate([x0 + 0.75, P, 13.5])
        # ledger strip glued along the inside of the rail, grain parallel
        lx0 = x0 + 1.5 if k == "L" else x0 - 0.75
        p["Ledger_" + k] = box(lx0, lx0 + 0.75, P + 1, P + L - 1, 10, 11.5)
    for i in range(5):
        y = P + 4 + i * 8
        p[f"Slat_{i + 1}"] = box(2.75, W - 2.75, y, y + 3, 11.5, 12.25)
    p["Post_L"], p["Post_R"] = posts["L"], posts["R"]
    return p


if __name__ == "__main__":
    for fn in (table, chair, chest, door, bed):
        for bad in (False, True):
            save(f"{fn.__name__}_{'bad' if bad else 'good'}", fn(bad))
            print("wrote", fn.__name__, "bad" if bad else "good")

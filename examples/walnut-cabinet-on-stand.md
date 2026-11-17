# Worked example: walnut cabinet on stand

A real piece: a walnut (and cherry) wall-style cabinet on a tall stand, built from a design by Philip Morley taught at the Center for Furniture Craftsmanship. The design and plans are Philip Morley's and aren't included here. This page shows only how the skill checked the 3D model.

## The piece
- **Stand:** tapered legs with mortised aprons and shadow grooves.
- **Case:** mitred at the top with keyed mitres (cherry keys), bottom lap-dovetailed into the sides, a divider with stub tenons, and a fixed shelf on tapered sliding dovetails.
- **Back:** frame and panel, with bridle joints, mullion and mid-rail tenons, and floating panels.
- **Door:** a rift walnut slab with breadboard ends on tongues, a cosmetic spline (decorative, nothing in it) and brass butt hinges.
- **Drawer:** half-blind dovetails at the front, through dovetails at the back, and a cedar bottom (a ripped-and-flipped glue-up) in grooves. The drawer is hand-planed to fit; the model shows the planed size.

The model has 55 parts, built parametrically in build123d and exported to GLB in millimetres, Z up.

## The spec
`walnut-cabinet-on-stand.cadcheck.json` says:
- Species, plus the grain direction for parts whose grain doesn't run their longest way: the door boards, side panels, divider, shelf and drawer bottom.
- Per-part wood: the drawer bottom is cedar, the door boards are rift. The cosmetic spline is set to `ignore`.
- The bottom sits on the stand rails and is held by wood buttons, so it's allowed to move.
- These gaps are intended: the case-to-stand reveal, the back frame behind the shelf, the sliding drawer, and the hinge leaves.

Writing the spec is half the value. It makes you state how every cross-grain contact is meant to work.

## Run
```
python3 scripts/cadcheck.py cabinet.glb --units mm --up z --spec walnut-cabinet-on-stand.cadcheck.json --grain
```

## What it found
- **First run, with no spec:** 25 flags. Most were how the piece is meant to work. The case sits on the stand. The drawer slides. The shelf grain was guessed front to back because the shelf is deeper than it is wide. That's what the spec is for.
- **With the spec:** 9 flags, all worth a look in the model (the cosmetic spline is no longer flagged once the spec marks it decorative):

| Flag | What it means |
|---|---|
| `hygiene` Back_Stile_L / _R | The two back stiles aren't closed solids. Rebuild them before trusting anything else about the back. |
| `interference` back panels vs stiles (0.02 to 0.045 in³) | The floating back panels run into the stiles. Either the panel is oversize or the stile groove is missing where the mesh is open. Probably the same fault as above. |
| `panel_room` Drawer_Bottom | Only 0.03 in of total room across the grain of an 11.8 in wide cedar bottom, which moves about 0.074 in over a 4% swing. Ripping and flipping the glue-up keeps it flat but doesn't reduce that. Widen the groove gap, or run the bottom out under the back and screw it through a slot. |
| `interference` hinge leaves | Leaf and knuckle overlap in the hardware model (0.01 in³), and one leaf runs 0.0015 in³ into the top breadboard. The model's hinge is a stand-in. The real hinge measures 1 1/2 in long x 1 in open with about 3/32 in leaves and a 7/32 in barrel; rebuild it at that size and cut its mortises to `hinge.py`'s numbers (about 13/32 in wide, 1/16 in deep per leaf for a 1/16 in gap). |

None of these show up in a render. Each would have shown up at the bench.

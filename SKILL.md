---
name: hardwood-furniture-cad
description: Use when modelling, editing, exporting or drawing solid hardwood furniture in CAD (Blender, build123d, CadQuery, any GLB/STL): tables, chairs, stools, benches, casework, drawers, doors, beds, shelves. Gives sizes, joinery and wood-movement rules, and checks the model for joinery and wood-movement mistakes.
metadata:
  author: Alican Rowe (@alicanrowe)
---

# Hardwood furniture CAD

Design solid-wood furniture that can actually be built and won't crack, then check the model before calling it done.

## Before modelling
1. Read `references/wood-movement.md`, the section of `references/furniture-types.md` for this kind of piece, `references/joinery-standards.md` and `references/modeling-rules.md`. If the user has a shop profile (see `references/shop-profile-template.md`), size every mortise, groove and rabbet to their tools, and flag anything they can't cut in one setup.
2. Start a project page from `references/project-template.md` and write the piece's cadcheck spec (`<piece>.cadcheck.json`): species, moisture swing (4% for a heated, air-conditioned house; 6% without AC), grain for any part whose grain doesn't run along its longest side, and which joints are attached so they can move.
3. Editing an existing piece: open the file the project page names as current and check its hash. Never build from remembered sizes.

## While modelling
- Plain boxes with box cuts; one part = one closed solid; never fill an old hole, rebuild the part.
- Shoulders square and seated (cut to the leg's angle on raked or tapered legs); blind mortises keep at least 1/8 in to the far face; tenon height = mortise height.
- No pegs, dowels, pins, wedges, plugs, inlays or round holes unless they're on the drawing.
- Wood movement: never glue long grain across long grain over about 4 in. Tops on buttons, clips or slotted screws; panels, drawer bottoms and back boards float with room across the grain; casework grain wraps the box; runners, kickers and side mouldings glued at the front only; breadboard ends glued in the middle only.
- Per-part wood: give secondary woods their own `species` (a cedar drawer bottom) and set `cut` (flat, rift, quarter) in the spec. Ripped-and-flipped or narrow-board glue-ups stay flatter but move the same total width, so leave the full room.
- Drawers and doors that are hand-planed to fit: model them at the final planed size (piston fit, about 0.005 to 0.010 in total side clearance) and say so in the project notes.
- Decorative parts that only look like joinery (a cosmetic spline, a faux peg) get `"role": "ignore"` in the spec, or a `Deco_` name.
- Hinges: pick a real hinge from `references/hinges.md` / `hinges.json`, model its leaves at the catalogue size (better: measured off the hinge in hand), and cut the mortises to `python3 scripts/hinge.py MODEL --door T --gap G`.
- Name parts so the checker knows their role: `Panel`, `Drawer_Bottom`, `Back_Board`, `Slat` (floating); `Button`, `Clip`, `Figure8` (fasteners that allow movement); `Tenon`, `Dowel`, `Spline`, `Tongue`, `Peg` (loose joinery); `Bolt`, `Screw`, `Hinge` (hardware); `Ply` (plywood).

## Before saying it's done
1. Export a new numbered version (never overwrite), then run:
   `python3 scripts/cadcheck.py MODEL.glb --units m --spec <piece>.cadcheck.json --grain`
   (A Blender GLB is metres, Y up. For a model in inches, Z up: `--units in --up z`.)
   Needs `pip install trimesh manifold3d numpy scipy rtree networkx`.
2. Check the `[grain]` lines against the drawing, then read every flag. Fix hygiene first, then through, interference, near_miss, empty_pocket, protrude, cross_grain, end_grain, panel_room, grain_unknown (`references/verification.md` explains each). Anything intended goes in the spec's `allow` or `movement_ok`, with the reason.
3. Diff part volumes and bounds against the previous version: any change that wasn't meant is a stray edit.
4. Cut a section through every changed joint and look at it. The checker doesn't see glue, short grain in curved parts, shelf sag or racking strength.
5. Regenerate the cut list, drawings and exports from the same file and note its hash on each.
6. Renders: run the grain audit in `references/rendering-wood.md` before final renders, and render a grain check sheet first.
7. Second pass: render the changed area (assembled and exploded), look at it against the brief or sketch, write down every problem you see, fix them, and render again. Only the second, clean pass goes out.

## Keep this skill improving
Any problem found with a model, a drawing or a render that a rule here would have prevented gets written into the matching reference file (modelling, joinery, furniture types, wood movement, rendering) in the same session. If the checker should have caught it, add a planted test piece to `scripts/tests/` too. Then commit and push.

After changing `scripts/cadcheck.py`, run `python3 scripts/tests/make_fixtures.py && python3 scripts/tests/run_tests.py`: all planted mistakes must be caught with no false alarms.

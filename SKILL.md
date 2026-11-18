---
name: hardwood-furniture-cad
description: Use when modelling, editing, exporting, drawing, rendering or writing up solid hardwood furniture in CAD (Blender, build123d, CadQuery, any GLB/STL): tables, chairs, stools, benches, casework, cases on stands, drawers, doors, beds, shelves, laser-cut plates. Gives sizes, joinery and wood-movement rules, checks the model for joinery, thin-web and wood-movement mistakes, and makes the cut list, full-size printouts, build book, renders and build animation.
metadata:
  author: Alican Rowe (@alicanrowe)
---

# Hardwood furniture CAD

Design solid-wood furniture that can actually be built and won't crack, then check the model before calling it done.

## Before modelling
1. Read `references/wood-movement.md`, the section of `references/furniture-types.md` for this kind of piece, `references/joinery-standards.md` (especially "Webs, necks and cheeks") and `references/modeling-rules.md`. For metal plates or a laser mockup also read `references/laser-cut-metal.md`. If the user has a shop profile (see `references/shop-profile-template.md`), size every mortise, groove and rabbet to their tools, and flag anything they can't cut in one setup. When you write a cutting plan for rough boards, keep every blank that still needs jointing or planing at least the jointer/planer minimum long (12 in unless the profile says otherwise), and crosscut short parts only after milling.
2. Start a project page from `references/project-template.md` and write the piece's cadcheck spec (`<piece>.cadcheck.json`): species, moisture swing (4% for a heated, air-conditioned house; 6% without AC), grain for any part whose grain doesn't run along its longest side, and which joints are attached so they can move.
3. Editing an existing piece: open the file the project page names as current and check its hash. Never build from remembered sizes.

## While modelling
- Plain boxes with box cuts; one part = one closed solid; never fill an old hole, rebuild the part.
- Shoulders square and seated (cut to the leg's angle on raked or tapered legs); blind mortises keep at least 1/8 in to the far face; tenon height = mortise height.
- **Leave wood around every cut:** at least 1/4 in of web between two cuts in one stick and 1/4 in cheeks (more in ash and oak). Where two grooves meet in a corner post, measure the neck between them in a plan section; bias grooves and tenons toward the outside and go shallower before it drops under 1/4 in. Don't put a panel groove and a second groove or rabbet in one stick so they leave a thin web: use a rabbet on the other edge, thicker stock, or two pieces.
- **Thicken on the inside only:** a rail thinner than its post gets filled out flush with the inside of the post, so the outside look doesn't change; then move whatever sat against the old face.
- **Mortises start about 1/2 in from the end of a leg or stile,** never 1/4 in; fill the gap with a haunch on the tenon.
- **Muntins get long tenons** (about 3/4 in at the top, 1/2 in at the bottom) in deeper pockets cut inside the panel groove, so the groove still locates everything.
- **A case locates on its stand with a hidden rabbet around the case bottom over a tongue on the aprons,** never glued-on locating strips.
- **Laser-cut plates:** no bar, web or tip thinner than the sheet; every motif tied into the bars (`scripts/sheetcheck.py`).
- No pegs, dowels, pins, wedges, plugs, inlays or round holes unless they're on the drawing.
- Wood movement: never glue long grain across long grain over about 4 in. Tops on buttons, clips or slotted screws; panels, drawer bottoms and back boards float with room across the grain; casework grain wraps the box; runners, kickers and side mouldings glued at the front only; breadboard ends glued in the middle only.
- Per-part wood: give secondary woods their own `species` (a cedar drawer bottom) and set `cut` (flat, rift, quarter) in the spec. Ripped-and-flipped or narrow-board glue-ups stay flatter but move the same total width, so leave the full room.
- Drawers and doors that are hand-planed to fit: model them at the final planed size (piston fit, about 0.005 to 0.010 in total side clearance) and say so in the project notes.
- Decorative parts that only look like joinery (a cosmetic spline, a faux peg) get `"role": "ignore"` in the spec, or a `Deco_` name.
- Hinges: pick a real hinge from `references/hinges.md` / `hinges.json`, model its leaves at the catalogue size (better: measured off the hinge in hand), and cut the mortises to `python3 scripts/hinge.py MODEL --door T --gap G`. Keep about 1/2 in of wood behind every screw, check the full swing, and order by how they're sold (Brusso: by the pair, so 4 hinges = 2 pairs).
- Figure: side and door panels plain-sawn with the cathedral centred and straight grain at both edges; rails, stiles, aprons and legs straight grain.
- Name parts so the checker knows their role: `Panel`, `Drawer_Bottom`, `Back_Board`, `Slat` (floating); `Button`, `Clip`, `Figure8` (fasteners that allow movement); `Tenon`, `Dowel`, `Spline`, `Tongue`, `Peg` (loose joinery); `Bolt`, `Screw`, `Hinge` (hardware); `Ply` (plywood).

## Before saying it's done
1. Export a new numbered version (never overwrite), then run:
   `python3 scripts/cadcheck.py MODEL.glb --units m --spec <piece>.cadcheck.json --grain`
   (A Blender GLB is metres, Y up. For a model in inches, Z up: `--units in --up z`.)
   Needs `pip install trimesh manifold3d numpy scipy rtree networkx`.
2. Check the `[grain]` lines against the drawing, then read every flag. Fix hygiene first, then through, interference, near_miss, empty_pocket, protrude, cross_grain, end_grain, panel_room, thin_web, grain_unknown (`references/verification.md` explains each). Anything intended goes in the spec's `allow` or `movement_ok`, with the reason.
3. Diff part volumes and bounds against the previous version: any change that wasn't meant is a stray edit.
4. Cut a section through every changed joint and look at it: corner-post plan sections, top views of the rails, the end view of every profiled stick, every mortise's distance from the end of its part (`references/drawings-and-printouts.md`). The checker doesn't see glue, short grain in curved parts, shelf sag or racking strength.
5. **Push everywhere** from the same file, with its hash on each, then list every image, page and viewer that shows the changed parts and confirm each is new:
   - cut list and milling plan: `python3 scripts/cutlist.py MODEL.glb --spec S.json --out build/`
   - full-size printouts (red outlines, red labels, no boxes): `python3 scripts/printouts.py MODEL.glb --spec S.json --cutlist build/cutlist.json --out build/`
   - laser cut sheets: `python3 scripts/printouts.py MODEL.glb --laser 'Plate' --out build/`
   - renders on white (hero finished; process and exploded raw): `python3 scripts/blender/stills.py MODEL.glb --look look.json --out renders/`
   - build book: `python3 scripts/build_book.py book.json --out build/Build_book.pdf` (start with `--init build/cutlist.json`)
   - build animation (finish only at the finishing step): `scripts/blender/animate_build.py`, then `scripts/overlay.py`
   - web viewer GLB: `python3 scripts/split_normals.py MODEL.glb MODEL_web.glb`
   `references/renders-and-animation.md` and `references/drawings-and-printouts.md` hold the house style: white backgrounds always, matte wood, labels in red with no box behind them. `assets/theme.json` holds the fonts and colours.
6. Renders: before the step 5 renders go out, run the grain audit in `references/rendering-wood.md` and render a grain check sheet first.
7. Second pass: render the changed area as the three-view check sheet in `references/drawings.md` (assembled with the moving part out, a hatched section, and an exploded view of the joinery; `scripts/drawings/`), look at it against the brief or sketch, write down every problem you see, fix them, and render again. Only the second, clean pass goes out.

8. Site: if the piece has a project site, update the viewer, drawings and spec table from the same file, viewer and drawing inline (`references/site-updates.md`).
9. Final renders, site stills and animations only after the design is locked; previews until then (`references/rendering-wood.md`).

## Keep this skill improving
Any problem found with a model, a drawing or a render that a rule here would have prevented gets written into the matching reference file (modelling, joinery, furniture types, wood movement, rendering) in the same session. If the checker should have caught it, add a planted test piece to `scripts/tests/` too. Then commit and push.

After changing `scripts/cadcheck.py`, run `python3 scripts/tests/make_fixtures.py && python3 scripts/tests/run_tests.py`: all planted mistakes must be caught with no false alarms.

# Hardwood furniture CAD skill

<table>
<tr>
<td width="50%"><img src="docs/pm-case-walnut.jpg" alt="A walnut cabinet on stand, modelled and checked with this skill: door open on brass butt hinges, drawer out"></td>
<td width="50%"><img src="docs/gallery/moth-hero-charred.jpg" alt="Moth: a charred ash case on a tall stand, frame-and-panel walls with stainless tracery, rendered on white"></td>
</tr>
<tr>
<td><sub>Walnut cabinet on stand (modelled, checked and animated with this skill)</sub></td>
<td><sub>Moth: charred ash case on stand (hero render: finished, on white)</sub></td>
</tr>
</table>

A Claude skill for designing solid hardwood furniture in CAD (Blender, build123d, CadQuery or anything that exports GLB/STL), checking the model for the mistakes that make real furniture fail, and turning it into everything the shop needs: a cut list and milling plan, full-size printouts, a build book, renders on white and a build animation.

Its rules come from real pieces and from the makers who reviewed them. Every rule below was learned the hard way on a model that had to be fixed.

## What it teaches

### Leave wood around every cut
<img src="docs/lessons/corner-neck.png" alt="Three plan sections of a 1 in corner post with two panel grooves. As drawn: grooves 3/8 deep, 1/4 from the outside, neck 0.18 in, too thin. Biased 1/16 out: neck 0.27 in. Biased and 5/16 deep: neck 0.35 in.">

Where two grooves meet in a corner post, the wood left between them (the neck) is what holds the inside of the post on. Measure it in a plan section. Bias the grooves and tenons toward the outside and go shallower before it drops under 1/4 in. `cadcheck` now finds these (`thin_web`).

<img src="docs/lessons/rail-web.png" alt="End view of two rails. Left: a 3/4 rail with a panel groove on top and a floor groove from the inside leaves a 1/8 in web. Right: a 1 in rail with the groove 3/16 from the outside and a rabbet on the inside bottom edge leaves a 1/4 in web and a solid cheek; the rabbet drops over a tongue on the stand apron.">

One stick, two cuts: a panel groove over a second groove left a 1/8 in web that failed a maker's gut check at a glance. Use a rabbet on the other edge instead, keep 1/4 in of web and a solid cheek, or make it two pieces.

### Thicken on the inside only
<img src="docs/lessons/thicken-inside.png" alt="Plan of a rail meeting a post. Left: a 3/4 rail on a 1 in post seats on only part of the post. Right: the rail filled out to 1 in, flush with the inside of the post; the outside face doesn't move.">

### Keep mortises away from the end of a leg
<img src="docs/lessons/leg-mortise.png" alt="Leg top elevation. Left: a mortise 1/4 in from the top leaves a thin cap of short grain. Right: the mortise starts 1/2 in down and a 1/4 in haunch on the tenon fills the gap.">

A mortise 1/4 in from the top leaves a cap of short grain that blows out. Start it about 1/2 in down and fill the space with a haunch on the tenon.

### Muntins get real tenons
<img src="docs/lessons/muntin-tenon.png" alt="Elevation of a muntin meeting a top rail. Left: a 3/8 stub tenon that only fills the panel groove. Right: a 3/4 tenon in a deeper pocket cut inside the groove.">

Long tenons (about 3/4 in at the top, 1/2 in at the bottom) in deeper pockets cut inside the panel groove: the groove still locates everything at glue-up and the pocket gives the joint real glue area.

### A case locates on its stand with a hidden rabbet
<img src="docs/lessons/case-on-stand.png" alt="Section through a case bottom on a stand. Left: a glued-on locating strip under the floor. Right: a rabbet round the case bottom drops over a tongue on the stand apron.">

No glued-on locating strips. A rabbet around the whole case bottom drops over a tongue on the stand's aprons: it locates both ways and can't be seen.

### Laser-cut plates: no web thinner than the sheet
<img src="docs/lessons/laser-plate.png" alt="Two laser-cut plate outlines in red. Left: a ring thinner than the sheet and a motif that touches nothing. Right: full-width bars and a motif tied into them.">

Every bar, web and tip at least the sheet thickness; every motif tied into the bars; cut sheets drawn as red outlines only. `scripts/sheetcheck.py` checks it.

### And
- **Hinges are sold by the pair** (Brusso, and most butts): 4 hinges = 2 pairs. Keep about 1/2 in of wood behind every hinge screw, and step every lid through its full swing.
- **Figure:** side and door panels plain-sawn with the cathedral centred and straight grain at both edges; rails, stiles, aprons and legs straight grain.
- **Push everywhere:** when the design changes, regenerate the cut list, printouts, drawings, book, renders, animation and web viewer from the same file, then list every image that shows the changed part and confirm each one is new.

## What it checks

`scripts/cadcheck.py` reads a GLB/STL assembly (one mesh per part) and flags:
- open or broken solids
- mortises that break through
- overlapping parts
- shoulders and seats that don't touch
- cuts that nothing fills
- tenons that stick out
- long grain glued across long grain over 4 in
- butt joints with no joinery
- panels without room to move, sized by species and moisture swing
- **new: webs and necks under about 0.2 in** (two grooves at a corner post, a groove over a rabbet, a mortise breaking into a groove), found by eroding each part one slab at a time

The test suite builds a table, chair, chest of drawers, frame-and-panel door, bed and case corner, each once correctly and once with mistakes planted: **24 of 24 caught, no false alarms.** On the real Moth model (v6r) the new check found what the shop reviewers found by eye: the 0.16 to 0.19 in necks in the three grooved corner posts and the 1/8 in web in all four bottom rails.

`scripts/sheetcheck.py` checks laser and waterjet plates: bars or tips thinner than the sheet, pieces that fall out, holes too small to cut.

## What it makes

| Step | Script | Output |
|---|---|---|
| Cut list and milling plan | `scripts/cutlist.py` | lettered parts, batches by thickness, strips by width, cross-cuts, board feet |
| Full-size printouts | `scripts/printouts.py` | face, edge, end and mid-length section of every part at 1:1, red outlines, red labels with no box; roll PDF, tiled letter PDF with check squares, SVG |
| Laser cut sheets | `scripts/printouts.py --laser` | red outlines only, 1:1 SVG, checked |
| Renders on white | `scripts/blender/stills.py` | hero (finished), process and exploded (plain wood), close-ups; matte wood, grain along each part, split normals, flattened onto white |
| Build book | `scripts/build_book.py` | cover, parts, milling plan, numbered steps with pictures and checks, finishing, sheet index; model hash on every page |
| Build animation | `scripts/blender/animate_build.py` + `scripts/overlay.py` | parts arrive in shop order, exploded joinery, finish only at the finishing step, a turn; labels on white; H.264 |
| Web viewer GLB | `scripts/split_normals.py` | split normals so flat faces don't streak |

<table>
<tr>
<td width="50%"><img src="docs/tools/printout-sections.png" alt="Full-size printout page: stand aprons, a corner post, a bottom rail and a muntin, each with face, edge, end and mid-length section views in red outlines. The post section shows the two grooves and the narrow neck between them; the rail section shows the groove over a second groove."></td>
<td width="50%"><img src="docs/tools/printout-tile.png" alt="One tiled letter page of the full-size printout with crop marks, a page grid label and a 1 in check square."></td>
</tr>
<tr>
<td><sub>Full-size printout from the Moth v6r model: the mid-length sections show the corner-post necks and the rail web</sub></td>
<td><sub>Tiled letter page: crop marks, page grid, 1 in check square</sub></td>
</tr>
</table>

<table>
<tr>
<td width="33%"><img src="docs/tools/book-p1.png" alt="Build book cover with the hero render"></td>
<td width="33%"><img src="docs/tools/book-p2.png" alt="Build book intro, tools and lettered parts list"></td>
<td width="33%"><img src="docs/tools/book-p3.png" alt="Build book step: tenon the aprons, with the exploded plain-wood render and a check line"></td>
</tr>
<tr><td colspan="3"><sub>Build book from the worked example in <code>examples/pipeline/</code></sub></td></tr>
</table>

<table>
<tr>
<td width="33%"><img src="docs/tools/table-hero.jpg" alt="Walnut side table, oiled, on white"></td>
<td width="33%"><img src="docs/tools/table-process.jpg" alt="The same table in plain wood from another angle"></td>
<td width="33%"><img src="docs/tools/table-exploded.jpg" alt="The table exploded, plain wood, showing the tenons and buttons"></td>
</tr>
<tr><td colspan="3"><sub><code>stills.py</code> on the test table: hero finished; process and exploded in plain wood</sub></td></tr>
</table>

<img src="docs/tools/animation-contact.jpg" alt="Twelve frames from the build animation: legs, aprons, buttons and top arrive in order, the table opens into an exploded view, the oil goes on only at the finishing step, then the table turns.">
<sub>Build animation frames: shop order, exploded joinery, oil only at the finishing step</sub>

Run the whole chain on the test table with `examples/pipeline/run.sh`.

## From real pieces

**Moth** (charred ash case on stand, frame-and-panel walls, stainless grilles, roof lids on Brusso hinges)

<table>
<tr>
<td width="50%"><img src="docs/gallery/moth-case-exploded.jpg" alt="Moth case exploded on white, plain wood: posts, rails, panels, roof halves, grilles and handle"></td>
<td width="50%"><img src="docs/gallery/moth-stand-exploded.jpg" alt="Moth stand exploded on white: legs, aprons, stretchers and tray"></td>
</tr>
<tr><td><sub>Case exploded (process shots are plain wood)</sub></td><td><sub>Stand exploded</sub></td></tr>
<tr>
<td><img src="docs/gallery/moth-corner-options.png" alt="Corner post plan at the top rail: as drawn neck 0.18 in, 1/16 out neck 0.27 in (chosen), 3/32 out neck 0.31 in"></td>
<td><img src="docs/gallery/moth-plan-section-v6r.png" alt="Plan section of the case 2 1/2 in above the bottom with detail A of the front-right corner post: solid red neck 0.18 in at 3/8 deep grooves, dashed 0.27 in at 5/16"></td>
</tr>
<tr><td><sub>Corner post options, numbers under each</sub></td><td><sub>Plan section with the corner detail (before the fix)</sub></td></tr>
<tr>
<td><img src="docs/gallery/moth-top-rails-v6r.png" alt="Top views of the top rails and bottom rails with a corner detail showing 1/4 thick, 3/8 long tenons in the panel groove"></td>
<td><img src="docs/gallery/moth-cross-section-v6r.png" alt="Cross-section through a side bay, roof to stand, with eave and ridge details; the case bottom still sits on locating strips in this version"></td>
</tr>
<tr><td><sub>Top views of the rails</sub></td><td><sub>Cross-section, before: the floor sits on glued locating strips, since replaced by a rabbet over an apron tongue</sub></td></tr>
<tr>
<td><img src="docs/gallery/moth-jail-plates.png" alt="Two stainless grille plates with C-scrolls tied into the bars, 1/16 in sheet, webs at least 1/16"></td>
<td><img src="docs/gallery/moth-cut-sheets-red.jpg" alt="Laser cut sheets for the cardboard mockup, every part as a red outline"></td>
</tr>
<tr><td><sub>Grille plates: every motif tied in, no web under the sheet</sub></td><td><sub>Mockup cut sheets: red outlines only</sub></td></tr>
<tr>
<td><img src="docs/gallery/moth-elevation.png" alt="Front and side elevations of the case on its stand with red dimensions"></td>
<td><img src="docs/gallery/moth-roof-top-view.jpg" alt="Top view of the closed roof halves with the hinges and handle, plain wood"></td>
</tr>
<tr><td><sub>Elevations: red dimensions straight on white</sub></td><td><sub>Roof from above: two lids, 4 hinges = 2 pairs</sub></td></tr>
</table>

<img src="docs/gallery/moth-instrument-lineup.jpg" alt="Thirty small instruments and a white moth figure in a row on white">
<sub>Rendered on solid white, never keyed from a dark background</sub>

**Walnut cabinet on stand**

<img src="docs/gallery/pm-walnut-raw.jpg" alt="The walnut cabinet in matte, unfinished wood: book-matched cathedrals on the two doors, straight grain on the apron and legs, brass hinges" width="50%">
<sub>Matte walnut: book-matched cathedrals centred on the doors, straight grain on the apron and legs</sub>

The worked example in `examples/walnut-cabinet-on-stand.md` walks through its spec, what the checker found, and what each flag meant.

## What's in it
- **`SKILL.md`**: the workflow Claude follows: read the rules, model, check, then push to every output.
- **`references/`**
  - `joinery-standards.md`: fits, mortise and tenon, webs and necks, frame and panel, locating a case on a stand
  - `wood-movement.md`: seasonal movement for 25 woods and the rules for tops, panels, casework, drawer bottoms and backs
  - `furniture-types.md`: sizes, default joinery and common failures for tables, chairs, stools, benches, casework, drawers, doors, beds and shelves; grain and figure
  - `drawings-and-printouts.md`: the sections reviewers ask for, house style, printouts, cut sheets, cut list, build book
  - `drawings.md`: the three-view check sheet (assembled with the moving part out, a hatched section, an exploded view of the joinery) and how to render it
  - `rendering-wood.md`: getting grain right in renders (rift vs flat-sawn figure, end grain, ring scale per shot, imported-mesh pitfalls) and a grain audit to run before final renders, when to render (previews until the design is locked), and fixing hero renders that look like plastic
  - `renders-and-animation.md`: white backgrounds, matte wood, finish by shot type, split normals, animation rules
  - `site-updates.md`: what a model change hands to the site (viewer GLB, drawings, spec table, all from the same file); the page work itself is in the [website-publishing](https://github.com/alicanrowe/website-publishing) skill
  - `laser-cut-metal.md`: plates, grilles and mockups
  - `hinges.md` + `hinges.json`: 71 hinges from Brusso, Lee Valley, Whitechapel, Sugatsune, SOSS, Horton Brasses, Rockler, Häfele and Blum, with screw-wood, swing and ordering checks
  - `modeling-rules.md`, `verification.md`, `project-template.md`, `shop-profile-template.md`
- **`scripts/`**: `cadcheck.py`, `sheetcheck.py`, `hinge.py`, `cutlist.py`, `printouts.py`, `build_book.py`, `overlay.py`, `split_normals.py`, `blender/` (`look.py`, `stills.py`, `animate_build.py`) and `drawings/` (the check-drawing sheet as clean line drawings from any GLB)

  ![Drawer check drawing](docs/drawer-check-drawing.png)
- **`assets/`**: `theme.json` (fonts and colours every output uses) and the fonts (Newsreader, IBM Plex Mono; OFL)
- **`docs/`**: the diagrams above (`make_diagrams.py` redraws them) and the gallery
- **`examples/`**: the walnut cabinet case study and a runnable pipeline on the test table

## Install
- **Claude.ai / Claude app:** zip this folder and upload it under Settings > Capabilities > Skills.
- **Claude Code:** copy the folder to `~/.claude/skills/hardwood-furniture-cad/`.
- Checks, cut list, printouts and book: `pip install trimesh manifold3d numpy scipy rtree networkx shapely reportlab pillow`.
- Renders and animation: Blender 4.2 or later (`blender -b -P scripts/blender/stills.py -- ...`), or `pip install bpy`; `ffmpeg` for the encode.

## Quick start
```
python3 scripts/cadcheck.py my_table.glb --units m --spec my_table.cadcheck.json --grain
python3 scripts/cutlist.py my_table.glb --spec my_table.cadcheck.json --out build/
python3 scripts/printouts.py my_table.glb --spec my_table.cadcheck.json --cutlist build/cutlist.json --out build/
python3 scripts/build_book.py --init build/cutlist.json > book.json      # fill in, then:
python3 scripts/build_book.py book.json --out build/Build_book.pdf
```
Example spec:
```json
{"species": "white oak", "mc_swing": 4, "min_web": 0.25,
 "parts": {"^Top$": {"grain": "x"}, "^Box_": {"min_web": 0.125}},
 "movement_ok": [["^Runner_", "^Side_", "glued at the front 2 in only, slotted screw at the back"]]}
```

## Limits
The checker treats every face-to-face contact as glued unless a fastener, a floating role or `movement_ok` says otherwise. Grain is taken as the longest side of each part unless you set it. The thin-web check is voxel-based: it flags necks under about 0.8 x `min_web` and its thickness readings are approximate, so confirm each with a section. It doesn't check short grain in curved parts, shelf sag, racking strength, or a mortise's distance from the end of its part. The cut list gives blank sizes from each part's oriented box: leaning and curved parts get their bounding blank, and the printouts give the shape. It's a second pair of eyes, not an engineer. Look at sections through your joints, and show them to someone who has built one.

Movement coefficients are approximate, from the USDA Forest Products Laboratory *Wood Handbook*.

# Rendering wood so the grain reads right

## The wood library (26 Nov 2026): one walnut, one ash, one oak
The same walnut came out muddy on one project, pale pink on a site card and grey in a reel, because every pipeline built or copied its own wood shader (seven walnut colours and five ashes were hard-coded). Now:
- **Data:** `references/woods.json`. Per species: the photo target (median and 10th/90th percentile sRGB of the wood in a neutral studio photo, from reference boards), albedo (earlywood, latewood, sapwood) fitted to it by `scripts/woodlib_fit.py`, ring spacing, porosity, pores, ray fleck, end-grain darkening, roughness, specular, pith depth for flat-sawn stock, and `house` gains per studio. Change numbers there, never in a script.
- **Model:** `scripts/woodlib.py` (numpy, for web bakes and checks) and `scripts/blender/woodlib_bl.py` (the same maths as plain Cycles/EEVEE nodes, no OSL). A part is a board: its own frame (grain u, wide face v, thickness w) plus where the pith runs. `flat`: pith a few inches under the wide face, tilting slowly, so the face shows a few nested cathedrals, centred, running out to straight grain at both edges. `quarter`: rings at 90 deg to the face. `rift`: about 45 deg, straight lines on all four faces. `auto`: frame members by name (leg, rail, stile, mullion, apron...) and small stock rift, boards flat. Sapwood is the rings beyond the heart radius (`sap: "edge"` puts one along an edge), so its boundary follows a ring. End grain is the same rings end on.
- **Use:** Blender `WB.apply(obj, species, cut=..., grain=...)` / `WB.apply_all(objs, look)` (look.py, photoreal.py, carving/render.py and laminated_wood.py already do). Web GLBs: `web_laminate.py --all`. Imported library GLBs in a studio: `WB.house_glb(material, studio)`.
- **Studios:** AgX and the bright soft studio lights lift and grey dark wood (the card studio turned the PM case's correct walnut texture, median 0.39 0.29 0.21, into 0.66 0.52 0.44). Calibrate each studio once per species with `scripts/woodlib_calibrate.py` (renders a card, measures the wood, solves the gain) instead of nudging colours.
- **Checks:** `scripts/woodlib_lint.py` on scripts, GLBs and blends; the site gate's `WOODLOCAL` (GLB wood without the library stamp) and `WOODTONE` (a wood card more than 0.06 off the photo median).
- Web bakes keep at least 5 texels per growth ring and fade detail finer than about 3 texels (`lod`), or rings and pores alias into mush and the bake check's correlation drops.

People judge a furniture render by its grain before anything else. Wrong figure makes a correct model look wrong, and a plasticky finish makes it look fake. These rules come from real review passes.

## Grain direction and figure by part
- **Rift stock** (legs, posts, rails, stiles, muntins, aprons, stretchers, frame members, box sides): straight parallel lines on **all four faces**, with growth rings on the end grain running about 45° across the section. That's the reason rift is chosen for square parts. Flame or cathedral figure on two faces of a leg reads as wrong grain, even though it's real for flat-sawn stock.
- **Flat-sawn stock** (raised panels, roof and lid panels, gables, case tops, glued-up blocks): cathedral figure is fine and expected, running along the panel's long dimension, centred, with straight grain at both edges.
- **Drawer bottoms** run side to side, parallel to the drawer front, whatever their proportions, so the bottom moves front to back in its groove and can be screwed through a slot at the back. A rip-and-flip bottom is strips running across the drawer, every other one turned over. Never front to back (PM case reel, 26 Nov 2026: "It's rip and flip, remember?").
- **Grain direction:** along the longest dimension for every frame member. Wall panels run vertical, roof panels along the ridge, and gables horizontal. Box sides follow the joinery: finger-jointed or dovetailed corners mean the grain runs around the box.
- **End grain** shows only on real ends: leg tops and feet, post tops, tenon ends and shoulders, finger and tail ends, through-tenon ends. Never on a long face.
- **Plywood** parts show face veneer only.
- **Mirrored or instanced parts** must not flip their grain frames.

## Grain audit before final renders
**Run `scripts/blender/render_grain_check.py` first** (`blender -b scene.blend -P scripts/blender/render_grain_check.py -- --frame F --spec piece.grain.json --sheet grain.jpg`). It renders every wood part alone and flat, measures the grain angle from the pixels (structure tensor), and fails any part more than 20 degrees off where its grain must run, or with no readable figure. It doesn't read the node graph, so a stray image layer or a mapping on the wrong axis can't hide: the PM case drawer bottom passed a node-level read and still rendered front to back, because a scanned-grain image layer was laid along the other axis. Spec only the exceptions (`{"parts": {"Side_*": "z"}}` for case sides whose grain wraps down from a mitered top); drawer bottoms are built in. Exit 1 blocks the stills.

For each wood part, list its bounding-box dims, the world direction of its grain axis, its end-grain faces, and its cut (rift or flat). Flag:
- any frame member whose grain isn't along its longest side;
- any end grain on a long face;
- any grain running across a part's width or through its thickness;
- any rift part showing cathedral figure;
- any mirrored frame.

Fix the flagged parts, then render a check sheet before re-rendering finals: the whole piece from two 3/4 angles, plus close-ups of a leg top, a post top, a case corner, a gable or panel and a drawer or box corner.

## Figure that reads as real flat-sawn walnut (26 Nov 2026, PM case)
- **Cathedrals run out to straight grain.** The ring height across a flat-sawn face is `sqrt(across^2 + D^2)` (D = the pith's depth under the face), not a straight V: a rounded arch over the middle, then the face turns towards the radius and the rings cross it at about one ring per inch, so the legs become straight lines along the board near both edges. A shallow linear V (0.25 ring/in across) gives nested chevrons that "radiate out fully" right to the edges. Keep the taper slope (rings per inch along the board) well under the across rate at the edges, so a door leaf shows a few arches, not a stack of nine.
- **Sapwood follows a ring.** Its edge is a growth ring meeting the face: it wanders gently along the board and feathers over a ring or so, and the figure (rings, pores, streaks) runs straight through it. Colour it pale tan (warm, like the heartwood around it after oil), never a flat grey bar, and never let its edge be the seam between two mesh pieces: put the boundary inside the sap piece and make the seam bevel tiny so heart meets heart without a groove.
- **End grain comes from the same rings as the face.** An end cap or end face is shaded with its own part's wood, in the part's coordinates (map the cap's space into the part's, rotation included), so the rings on the end are the ones the face shows, continuous round the corner, with crisper latewood lines and duller, darker oil. Never a separate ring image on the end: it reads a step down in quality from the face beside it.
- **Bark (black walnut):** the ridges interlace as a dark grey-brown network and the furrows are deep, near-black diamonds between them. Displace outward only from the bark's base surface, or whatever sits under it (the pale sapwood) shows through every furrow as a light net. Ridges about 1 to 1.5 in wide on a 30 in log, matte (roughness 1, no specular).

## Wood shader that reads as real ash or oak
- Give each part its own grain frame from PCA of its vertices (long axis = grain), not world axes, or tilted roof
  and gable parts get grain across them.
- Rift parts put the pith 35 to 55 degrees off a corner; flat-sawn panels put it a few inches off the face, with a
  slight cone so cathedral figure shows.
- Ring-porous species need earlywood pores stretched along the grain, a latewood colour gradient, fibre and
  streak noise and a darker end grain. Without them the wood reads as pine, and flat colour bands posterise at 100%.

## Laminated, staved and glued-up parts (2026-11-24)
The Studio Shrine Bench went out with one straight walnut grain running over its whole stack-laminated plank and its staved drums, so the twist read as one board bent into a ribbon. The client: "the grain wouldnt look like that because they are multiple pieces laminated not a single board being bent".
- Shade every glued-up part with `scripts/blender/laminated_wood.py` (Cycles OSL): `stack` for horizontal stack laminations, `stave` for coopered drums and curved backs, `panel` for edge-glued tops and discs, `solid` for single boards.
- Match the shader to the real build: layer thickness and a layer boundary from the cut list, stave count and centre from the model. Keep the boundaries out of a show face (face the top layer down a little, so no glue line lies in the seat).
- Each board gets its own pith, ring spacing and tone. Keep the tone spread to about +-20 % in shader units (it reads as +-10 % on screen) so the piece stays one tone; the figure breaking at every seam is what shows the lamination.
- Where a faired surface cuts the stack at a slant, the layer rings show as contour bands; on a vertical face of a stack they read as level stripes one layer apart. Check both in a close-up before the finals.
- End grain shows on real ends only (darker, open pores); in a stave or stack it comes out of the same per-board rings.
- Web viewer GLBs: glued-up and curved parts are baked in 3D by `scripts/web_laminate.py` from the same lamination parameters as the render (spec `"lamination"`), so the 3D preview shows the same boards and contour bands (25 Nov 2026).

## Dark-room key light with polished metal
- The world is black to the camera and to diffuse rays. Only glossy rays see a couple of soft strip boxes, so
  rhodium and brass have something to reflect instead of rendering black or grey.
- Set the floor's specular to 0, or it mirrors the strips and flattens the light pool.

## Imported meshes (GLB, OBJ)
- Procedural grain driven by object coordinates breaks when a part arrives in different units or a different axis order. Check each part's grain origin, pith and direction after every import, and convert units (inches vs metres, Y vs Z up).
- Clear custom split normals on flat boards and use smooth-by-angle (about 30°). Smooth normals bent across a flat board give a soft, even, plastic sheen and broad diagonal bands.

## Finish
- Raw or oil-finished wood: no clearcoat, little anisotropy, specular around 0.3 to 0.4, roughness driven by the grain (the latewood a bit smoother). A grain bump breaks up the highlight.
- **Scale the ring pattern to the shot's pixel density**, not only to real inches. Rings that read well on a wide shot of a long board blur into flat streaks in a close-up. Aim for roughly 15 to 25 px between rings on screen; use a finer procedural on close-ups and a coarser one on wide shots.
- Don't stack scene lights on top of a bright world: it washes the grain out and flattens the figure.

## When to render, and where
- **Preview only until the design is locked.** While parts, motifs or hardware are still changing, use cheap previews (viewport or low-sample cloud renders, line drawings). Final stills, site images and animations are rendered once, after the client signs off the design. Stop any final render the moment a design change makes it obsolete.
- Render on cloud machines, never on the client's own computer. Use a paid farm only for big jobs (animations), and only with the client's go on the cost.

## Hero renders that look fake
Shiny plastic is the usual complaint. Before showing a hero, put it beside two or three real photographs of comparable finished pieces (same species and finish) and check:
- the finish: no clearcoat on oiled or charred wood, broad soft highlights, roughness 0.45 to 0.7 driven by the grain;
- charred or blackened wood (shou sugi ban) is matte and textured, with brushed raised grain, never a glossy black;
- normals: flat faces stay flat (see Imported meshes), edges get a small real bevel so they catch light;
- lighting: one large soft key, a fill, a dark flag for edge contrast, a real floor with contact shadow;
- grain scale is right for the shot (15 to 25 px between rings).
Fix what doesn't match, re-render, and repeat. Show only the pass that holds up next to the photos.

## Matching a photographer's studio look
When the owner names a maker or photographer whose pictures the renders should match, measure their pictures before changing anything, and loop until the numbers agree (Studio Shrine Bench, Nov 2026, six rounds):
- Pick 4 to 6 of their images per setting (paper sweep, room, curtain). Measure the median and 10th/90th percentile colour of the wood pixels (r - b > 35, r < 200, g < 0.85 r) and the background at the top and bottom of the frame. Measure your renders the same way after every round and write both down.
- Catalogue sweeps are flatter than you think: one large soft source high and to the side (aimed at the piece from about 45 degrees up), a real fill at a quarter of it, exposure set so the paper reads about 220 not 240. Side light at seat height makes the near faces glare.
- A white sweep reflects into the wood and greys it: keep specular low (0.15 IOR level, roughness 0.6, no coat) for oiled walnut, or the median goes milky and the blue channel climbs.
- AgX lifts mid tones a lot: an upholstery albedo of 0.24 rendered as a white card. Upholstery around 0.08 to 0.13 reads as mid-tone cloth. Tint Blender 4's sheen with the yarn colour; the default white sheen whitens cloth.
- Tonal variation for walls and floors comes from a grey noise (Fac), never the noise's Color output, which shifts the hue (green walls, camouflage rugs). A sisal or jute rug is fine noise bump at about 900 per metre; a wave texture moirés into corduroy at a distance.
- Make the backdrop wider than any lens you'll use sees: a long diagonal shot ran past the curtain and cyc ends.
- Keep the look knobs (specular, roughness, tint, exposure per setting) in one block at the top of the render script, so each round changes numbers, not code.

## Web viewer GLBs (2026-11-23)
The PM case preview on the site went out with swirly contour-map figure on its panels, a cathedral image as its "end grain" and diagonal grain on the legs, twice. Causes: a texture named "flat" was exempt from the straight-grain check, anything named "end" was skipped, and all 55 parts were merged into six meshes by material, so the per-part check saw two "parts" and passed; the old regrain also used each part's longest side and ignored the spec, so case sides ran front to back.
- Build viewer GLBs only with `scripts/web_glb.py`; it writes each part's grain axis into the GLB.
- `scripts/web_grain_check.py` must pass: per part (merged meshes are split and checked piece by piece), grain along the part, end grain only on ends, and every long-grain texture straight, whatever its name.
- `curved` (25 Nov 2026, Shrine bench plank: "grain is wrong again"): a 2D texture on a surface that twists, sweeps or bends along its grain follows the surface like one board bent into shape, even when its lines run along the part. Wood is a solid: bake such parts with `scripts/web_laminate.py` (stack / stave / panel / solid, `--auto` for unnamed turned or carved parts) and the check re-evaluates the bake (`bake`). Turning round the grain (dowels, handles, roundovers) is fine as 2D. Only a real steam-bent board or bent lamination is `"bent": true`.
- Site GLBs are meshopt + quantized: the check decodes and dequantizes them itself (trimesh misreads quantized normals and UVs).
- No wood image of your own goes in a web GLB. Figure comes only from the wood library bake (`web_laminate.py --all`), which puts flat-sawn cathedrals where a board really has them (case sides, tops, panels) and rift grain on frame parts. A flat-sawn case side shown with straight grain reads as missing its cathedral (PM case card, 26 Nov 2026).

## When laminated_wood.py can't run (25 Nov 2026)
The pip `bpy` build has no OSL compiler (`No module named 'oslquery'`, then `key "Pos" not found`), so `laminated_wood.py`
fails there. Either render with a downloaded Blender binary, or split the glue-up into one object per layer and use a
node shader whose ring coordinate is offset by a per-object `seed` property: every layer then gets its own figure, and
parts cut out of a layer (a drawer front) can share its seed so the figure runs on. Add the glue line from world position
(pingpong of y / layer thickness). Keep bump Distance tiny (about 0.00015 m); the default 1 m turns pores into ridges.
Worked example: a `mat_cherry()` node tree built this way (TexCoord Object x 39.37, ring distance from a pith offset by the seed, noise wander, stretched pore noise, per-seed tone).

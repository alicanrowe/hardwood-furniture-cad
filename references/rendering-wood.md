# Rendering wood so the grain reads right

People judge a furniture render by its grain before anything else. Wrong figure makes a correct model look wrong, and a plasticky finish makes it look fake. These rules come from real review passes.

## Grain direction and figure by part
- **Rift stock** (legs, posts, rails, stiles, muntins, aprons, stretchers, frame members, box sides): straight parallel lines on **all four faces**, with growth rings on the end grain running about 45° across the section. That's the reason rift is chosen for square parts. Flame or cathedral figure on two faces of a leg reads as wrong grain, even though it's real for flat-sawn stock.
- **Flat-sawn stock** (raised panels, roof and lid panels, gables, case tops, drawer bottoms, glued-up blocks): cathedral figure is fine and expected, running along the panel's long dimension.
- **Grain direction:** along the longest dimension for every frame member. Wall panels run vertical, roof panels along the ridge, and gables horizontal. Box sides follow the joinery: finger-jointed or dovetailed corners mean the grain runs around the box.
- **End grain** shows only on real ends: leg tops and feet, post tops, tenon ends and shoulders, finger and tail ends, through-tenon ends. Never on a long face.
- **Plywood** parts show face veneer only.
- **Mirrored or instanced parts** must not flip their grain frames.

## Grain audit before final renders
For each wood part, list its bounding-box dims, the world direction of its grain axis, its end-grain faces, and its cut (rift or flat). Flag:
- any frame member whose grain isn't along its longest side;
- any end grain on a long face;
- any grain running across a part's width or through its thickness;
- any rift part showing cathedral figure;
- any mirrored frame.

Fix the flagged parts, then render a check sheet before re-rendering finals: the whole piece from two 3/4 angles, plus close-ups of a leg top, a post top, a case corner, a gable or panel and a drawer or box corner.

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
- Web viewer GLBs still carry one straight grain per part (`web_glb.py` has no lamination mode yet). Until it does, say so if the viewer is the only view of a laminated piece.

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
- No flat-sawn, cathedral or figured image goes in a web GLB. Real figure belongs in the Blender renders, where it's procedural and checked by eye.

## When laminated_wood.py can't run (25 Nov 2026)
The pip `bpy` build has no OSL compiler (`No module named 'oslquery'`, then `key "Pos" not found`), so `laminated_wood.py`
fails there. Either render with a downloaded Blender binary, or split the glue-up into one object per layer and use a
node shader whose ring coordinate is offset by a per-object `seed` property: every layer then gets its own figure, and
parts cut out of a layer (a drawer front) can share its seed so the figure runs on. Add the glue line from world position
(pingpong of y / layer thickness). Keep bump Distance tiny (about 0.00015 m); the default 1 m turns pores into ridges.
Worked example: a `mat_cherry()` node tree built this way (TexCoord Object x 39.37, ring distance from a pith offset by the seed, noise wander, stretched pore noise, per-seed tone).

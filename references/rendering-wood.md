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

## Web and exported GLBs
The audit above covers Blender renders. A GLB for the web carries its grain in UVs, not in a procedural shader, so check it separately with `scripts/glb_grain_check.py` (texture grain axis compared with each part's long axis, face by face). Fix with `scripts/glb_regrain.py`. The baked texture itself must be straight (rift) grain along U: `scripts/glb_texture_check.py model.glb` fails flat-sawn figure, which looks wavy on every part even with perfect UVs. Name an intentionally figured material with flat, figure or burl.

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

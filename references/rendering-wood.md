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

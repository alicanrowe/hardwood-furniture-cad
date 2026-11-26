# Photo-matched hand tools (squares, rules, pencils, planes, saws, chisels)

Use when a piece has to hold a real tool (a holster, a pocket, a till, a case insert) and the tool has to be the
real one, not a stand-in. The target is a model you could not tell from the maker's product shot.

## Sources first
- Official numbers: the maker's product page and any instructions PDF. Shopify stores expose every product, variant,
  weight and full-size image at `<site>/products.json` (and `/products/<handle>.json`). Save the URL and read date.
- Pictures: the maker's own orthographic or near-orthographic renders beat any photo. Download them at full size
  (Shopify: strip the `_<size>x` suffix or ask for `?width=2000`).
- When the images and the published spec disagree, trust the images, say so, and give both numbers.

## Scale from the picture
- A graduated part (rule, square blade) gives its own scale: take a strip through the ticks and FFT it; the peak is
  ticks per pixel. 1/32 in ticks across 2000 px give the scale to better than 0.1%.
- Otherwise use the longest published dimension, measured edge to edge on the silhouette.

## Make and check
1. Trace the silhouette in the photo's pixel frame, convert with the scale, and build the B-rep from it (build123d).
2. Render the model with a matched orthographic camera on the photo's background colour, then overlay the two
   (XOR image + IoU). Fix until the outline sits within ~1 px. Leftover IoU loss that is just a dark part against a
   dark background is a threshold problem, not geometry.
3. Thickness: solve the camera from known corners of a part that does not move (solvePnP on the blade, never the
   sliding head), then overlay. A single photo resolves about 1 mm at best; mark thicknesses as estimates.
4. Clash check every part pair (manifold3d boolean intersection, fail above 0.02 mm^3).
5. Studio stills on white, then compare against the maker's close-ups (ferrule, tip, stamp, knob) and fix again.

## Etched scales, stamps and labels
- Build the etch as a texture from the maker's own image: threshold to a mask, map it onto the face by its rect.
- Areas the head or a hand hides: fill from copies shifted by whole inches (the scale repeats), iteratively, masked
  so you only ever copy real blade.
- Missing text: set it in a close font (Inter) at the measured cap height and position, never freehand.
- Back faces: the UV must mirror u so the back reads correctly from its own side; edges get a blank UV.
- glTF metallicRoughness: G = roughness, B = metallic. OpenCV writes BGR, so in a cv2 array index 0 is metallic and
  index 1 is roughness. Mark the image Non-Color.

## Gotchas
- build123d polygons must be counter-clockwise or extrude goes -Z; wrap them in a ccw() helper.
- Wedge-shaped webs between two legs: build the triangle through the legs' line intersection, not from the outline.
- Bevel facets: cut with planes along each leg's inner line, limited so a cutter can't remove the whole leg.
- Blender Mix node: pick sockets by index (RGBA in 6/7, out 2); by name hits the float sockets.
- Small objects: area lights at "normal" wattage blow out. Use exposure about -1.5 to -1.8, a dim world, and
  camera-invisible dark cards so polished steel has something to reflect.
- Gold-plated or polished parts in a white world read white; give them dark cards too.
- A ferrule or tube built by subtracting lofts can leave an open window; check the shell's volume against
  wall x area before export.

## Turned tools from bench photos (chisels, awls, files; learned on a six-chisel set)
- No orthographic shots? Straighten each tool out of the photo first: rotate the image about the tool's midpoint so
  its axis is vertical, crop a strip, then measure rows. GrabCut and colour masks fail on a wood handle over a wood
  bench (they swallow the bench or lose glossy edges); read the strip with a grid by eye, it is faster and right.
- Perspective in a tilted bench photo: model the scale as linear along the strip, s(y) = s0 (1 + k (y - y0)), fixed by
  two known widths at different rows (blade width, official handle diameter). Lengths are then integral dy / s(y).
- That still leaves axis foreshortening (the camera is not square to the tool): widths are right, lengths come out
  short (10% on a 45-degree phone shot). Calibrate lengths with the official overall length, then check one other
  official length (handle) as an independent test. Different tools in the same photo need their own factor.
- A second photo shot from the other end reverses the perspective: ratios that agree in both (ferrule back / handle
  max) are trustworthy; absolute ratios that disagree by the perspective factor are not.
- Overlay check: draw the model's top-view half-width envelope (max |y| per x over all parts, windowed so bores
  don't drag it in) back onto each straightened strip with that strip's scale model.
- Bevel-edge blade section: fixed side-bevel angle from the full-thickness top flat; at the cutting bevel the thinner
  section gets a wider top, which reproduces the trapezoid facet seen end-on.
- Maker's sticker: overlapping glare stripes make tracing unreliable; set it in matched fonts at measured radii and
  compare against several copies. Old English capitals: Cloister Black (1001fonts, free commercial) is the closest
  free match to Old English Text.
- Rendering polished steel: on a white set the flat facets go pure white. Three causes, all hit here: a shadow-catcher
  floor turns into transparent pixels in reflections; a big key light in the mirror direction of a flat facet; and
  anisotropic BSDF without tangents. Use a floor that is white to camera rays and dark grey otherwise (Light Path
  Is Camera Ray), the same trick for the world, a key light in front of the tool, and plain roughness ~0.3.
- Turn on sharp-by-angle (mesh.set_sharp_from_angle(30 deg)) for lofted and revolved parts or smooth shading smears
  facets and leaves slivers at steps (cap to handle).
- Revolved domes pinch the texture to a point at the pole: give the dome planar UVs.

## Back saws and other flat tools from catalog side shots (learned on two Lie-Nielsen back saws)
- A clean side shot on white is a free orthographic view: segment by HSV (background = bright + low saturation,
  steel = low saturation, brass = hue 38-65 deg bright, wood = the rest), keep the largest component, keep enclosed
  holes that are background (closed hand holes), fill those that are brass (bolt heads).
- When two official lengths (overall vs blade) disagree in the maker's own photo, use the geometric mean of the two
  px/mm scales: both land within 1 % instead of one exact and one 2 % off. Say so in SPECS.
- Rounded handles from a 2-D mask: upsample x6 bicubic + blur for a sub-pixel outline, distance-transform it, map
  distance to a round-over half-thickness, Gaussian-smooth that field (~0.35 mm) or the edges terrace, pad the volume,
  marching cubes, then let manifold3d merge + simplify; that gives a watertight mesh trimesh alone calls open.
- Photo-matched look: planar UVs straight into the photo; a 2x-wide atlas whose right half is the photo with etches
  median-filled away, for faces whose normal points away from the camera. Pad the photo outward from 2 px inside the
  silhouette (EDT nearest index) or rounded edges streak white from background-blended pixels.
- trimesh PBRMaterial treats integer baseColorFactor as uint8: [1,1,1,1] exports as near-black. Use [255,255,255,255].
- Blender's default camera clip_start is 0.1 m: close-ups of small parts render empty. Set 0.002.
- Calibrate exposure by comparing the mean colour inside the handle mask of the match render with the photo.
- Saw teeth for push saws: the near-vertical cutting face faces the toe. Bend set into alternate teeth by moving
  the vertices below the tooth root in z, scaled by depth below the root.
- Validate on the maker's other catalog shots too: handmade handles drift between batches (2-3 % here), so match
  the current primary product image and report the others.

## Bench planes (learned on a bronze smoother and an iron jointer, 22 parts each)
- Model the blade stack in a bed frame: s along the bed (up), n normal to it (n>0 frog side, n<0 cap side), mapped
  as x = xm - s*cos45 - n*cos45, z = s*sin45 - n*sin45. Blade, chipbreaker, cap, screws and frog all become simple
  (s, n) prisms and clearances are just offsets in n.
- Catalog side shots are not orthographic for long tools: a 22 in jointer needed a perspective camera (D ~1.1 m)
  and a lens calibrated at the near sole edge, or the toe and heel drift 2-3 %. A 9 in plane was fine ortho.
- Photo pixels are on the near cheek, the model centre plane is W/2 behind it: convert every measured point
  (near vs centre plane) using the camera elevation, or features above the sole climb a few mm.
- Sole width and casting thicknesses are not published; say "assumed" in SPECS and keep them in one place.
- Tote and knob: digitise the side profile from the wood mask, buffer it 1-2 px with shapely to get a valid polygon,
  then SDF-round (R ~9.5 mm) and marching-cube it; the knob is a revolve of a measured radius table.
- Do the frog cut-outs, lever hook union and tote-nut holes as manifold3d mesh booleans after meshing; OCC fillets on
  these shapes fail or self-intersect. Assert watertight after each.
- Clash fixing order that converged: cap screw taps into the frog (shorten), knob/tote seated exactly on the pads,
  tote nut hole coaxial with the rod, lever start clear of the cap screw, lateral lever offset off the blade.

## Second pass to "exact" (squares, rule, pencil, 26 Nov 2026)
- Measure every width from the tool's own graduations: an FFT of a 1-px band along the ticks gives the px/mm to
  0.05 %, then alpha-sum across the blade gives the width to ~0.1 mm. This beat both "nominal" guesses (a 3/4 in blade
  measured 18.84 mm, a 6 in rule 18.72 mm) and the first pass's trace. Check the method on a part of known size first.
- Score with an honest IoU (no fill_holes on the reference, same closing on both) and p95 edge distance in mm; when a
  part slides (a square's head), align it before scoring and say so.
- Machined faces: build the slab, then planar cuts per facet (crease line + slope), and a Minkowski bicone for the
  45 deg edge break. Heightfield caps give noisy shading. Weld manifold output (union-find, eps ~1.5 um) before export,
  or a 1 um GLB merge splits seams. Keep a slot face a few um off any other face to avoid pinches.
- Re-register an etch texture by fitting the major ticks (n x 25.4 mm) and cropping, not by stretching to the part.
- Black patches in close-ups that stay black with a diffuse override are the camera's near clip, not normals.
- Colours: render with Standard view transform, a white floor and a world that is white above and dark below the
  horizon; then compare the same patches with the maker's photo (eraser, wood, plating). AgX plus a uniform white world
  washes metals and makes wood read pink. Take the albedo where a lit face sits next to the white backdrop.
- Wood grain for small parts: rectify a clean band of the maker's close-up, flatten shading, take its mean and first
  colour axis, then make procedural lines + flecks + pores at the part's UV scale, histogram-matched to the band.
  Random-phase synthesis of a thin band loses the streaks.
- Sheet-metal parts (ferrules): loft one closed section per x station (circle blended into a superellipse), outer minus
  inner (radius minus wall), so the solid is watertight by construction. Re-read the profile off the maker's side view
  (crimp grooves, shoulder length) instead of trusting the first pass.

## Second pass on turned/ground tools (bench chisel set, 26 Nov 2026)
- Score against the owner's own photos with a matched camera: fit pose (Rodrigues) per tool plus one focal length
  shared by the whole photo (median of per-tool fits), Powell then Nelder-Mead, initialised from the mask's PCA
  (handle end = wide end). Oblique photos need a multistart over camera tilt or the fit lands in a mirror minimum.
- Rasterise the model silhouette as convex hulls of consecutive station rings, per part (hulling across parts drops
  thin parts like a ferrule). Full triangle rasterisation inside an optimiser is far too slow.
- Masks: BiRefNet (rembg birefnet-general) beats GrabCut on wood/brass/steel on a bench, but it is memory heavy: run
  one image at a time at ~2000 px, and resize any mask saved at a different size before scoring.
- Measure along the tool axis in the fitted camera frame and classify colour along it (brass / wood / black) to find
  the washer and cap. Mask edges add ~+0.3 mm per side; subtract it. Published "handle length" may not be the wood
  barrel; measure the barrel (it was the same ~84 mm on all six sizes).
- IoU 0.97 against a phone photo is near the floor set by 1-2 px mask error and unmodelled lens distortion on thin
  parts; report the number honestly instead of tuning the scorer.
- Ferrule swell: outer radius = cone + s*sin(pi*t) (s ~0.45 mm), inner bore stays a cone so the wall stays valid.
- Hollow grind: sag the primary bevel by (x-x0)(xe-x)/(2R), R ~100 mm (a bench wheel radius). Give the bevel its own
  rough, coarse lengthwise scratch texture; a glossy bevel blows out to white.
- Blade facets: give every edge of the section a fixed vertex budget so facet corners are vertices on every ring;
  resampling by arc length makes a sawtooth along the corners. Clamp the land and top so no edge is zero length.
- Labels/decals must be closed thin solids (outer skin + inner skin 0.02 mm off the wood + rim), not open sheets.
- Lathe UVs: make the loop UV seam-aware (if a face spans u > 0.5, add 1 to the small u's) or the handle opens.
- Wood from photos: direct unwraps, patch and strip quilting all showed glare, seams and repeats on lacquered handles.
  What worked: synthesise per handle (periodic noise, domain-warped lengthwise grain, the handle's own figure type:
  arches, ribbon, curl, fleck), quantile-match to that handle's lightness histogram, colour ramp = median Lab per
  lightness quantile from the photo, then calibrate a BGR gain on the render vs photo means (two passes got dE 2-5).

## Second pass on sculpted saw handles (back saws, 26 Nov 2026)
- Round-overs from a traced outline: never mesh a height field `|z - zc| - zh(x,y)` with marching cubes. Where the edge
  goes vertical the crossing jumps cell to cell per z level and the wall reads as stacked terraces. Mesh an approximate
  signed distance of the section instead: wall `-d`, elliptical corner `(q - 1) * min(Rh, Rz)`, flat face `w - half`.
- Build the marching-cubes mesh with `process=False`: merging coincident MC vertices creates non-manifold edges, and
  every decimator then throws long spikes. Smooth (Taubin) and decimate with Blender's Decimate (collapse) modifier.
- Trace the wood from the whole silhouette minus only the metal that is connected to the blade/back, not "wood colour":
  low-saturation highlights on the wood otherwise dent the outline. Blur the upsampled mask by ~1 mm (in mm, not px),
  then open by 0.5 mm to kill hair-thin JPEG leaks (one ran from the cheek to the lower horn).
- Section by region: crisp R ~2.5-3 mm round-over on the cheek and horns, full oval on the grip (horizontal semi-axis
  ~11 mm), horns thinning to ~72 % at the tips. Local thickness (largest inscribed disc) via thresholded EDTs.
- Projected photo texture on a rounded handle smears into stripes on every edge. Unwrap (xatlas), bake texel positions
  with Cycles (EMIT of Geometry Position into a float image, margin EXTEND), then evaluate a solid 3D wood there.
  Relax xatlas chart options (normal_deviation_weight ~0.3, max_cost ~10): defaults on a decimated MC mesh gave ~3,800
  tiny charts and a fine hatch pattern in close-ups. Cache the unwrap: it takes ~7 min for 320k triangles.
- Solid wood: rings = (n0 . p + kz (z - zc)) / ring + warp, n0 from the photo's median line direction (band-pass
  structure tensor so shading is ignored). A Poisson stream function of the full field does not keep unit gradient:
  ring spacing ran wide and the cheek figure turned vertical. Add long streaks (fbm along/across grain) for cherry.
- Calibrate the light on the parts whose albedo comes straight from the photo (plate, brass) first, then tune the wood
  albedo to the photo mean in that light (got dE 1.4-2.2).
- Etch letters: fit font, cap height, x-scale and position per word by NCC (correlate2d, sub-pixel offsets); at a
  ~6 px cap the stroke weight is not resolvable, so take the measured fit and un-mix the ink colour from the brass.

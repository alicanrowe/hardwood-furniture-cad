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

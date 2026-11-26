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

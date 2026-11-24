# Photo-matched carving: modelling a finished carved piece from photos

For a piece that already exists and only lives in photos (Fawn Orchard, Nov 2026): no cut list, no joinery, just
"make the CAD look like the pictures". Hand-carved, power-carved and gouged surfaces don't come out of B-rep CAD;
build them as signed distance fields (SDFs) on a voxel grid, mesh with marching cubes and render in Blender.
Tools: `scripts/carving/` (`fo.py` grid/meshing/gouge/scoops, `shapes.py` primitives, `render.py` scene-JSON
renderer with the walnut material, `camera_from_photo.py`).

## The loop
1. **Gather every photo** of the piece, including process shots: a close-up of one carving from a known angle is
   worth more than another wide shot. Sort them by layout; exhibition photos taken on different days often show the
   pieces moved or turned (photos 3 and 6 of Fawn Orchard are two different arrangements). Pick one layout as the
   target and say so.
2. **Solve the camera** for each target photo with `camera_from_photo.py` from four floor points of the biggest
   piece with a known size. Then measure the other pieces by casting pixel rays onto known planes (floor, slab top):
   sizes from two photos agreeing within an inch is good enough.
3. **One script per piece**, local coordinates in inches, base on z = 0. Blocking shapes first (rounded boxes,
   capsules, ellipsoids, smooth-unioned with `smin` 0.3 to 1 in), then the carving, then the tool texture.
4. **Render from the solved camera, put the render next to the photo** (side by side, same size), and write down
   every difference: silhouette first, then turn, then proportions, then surface, then colour. Fix the biggest
   one, render again. Crop single pieces from the photo and the render for close checks.

## Carving recipes that read right
- **Flowing channels (power-carved flames, water, grain)**: ellipsoid scoops strung along streamlines of a smooth
  2D flow field (`carve_scoops`), long axis along the flow. Deep and narrow (width 0.45 to 1 in, depth up to the
  width) packed close gives sharp ridges between them; wide shallow scoops read as lumpy dough.
- **Gouge / chisel facets**: Voronoi F1 cells (`gouge`, cell 0.35 to 0.8 in, depth 0.03 to 0.1 in, stretched along
  the main flow). Keep it out of polished bowls: scale it by a mask that goes to ~0.1 inside them.
- **Bowls and pockets**: superellipsoid cuts (`q**4`) give flat-bottomed, steep-walled bowls; ordinary ellipsoids
  read too shallow. Cut bowls after the channels and drop channel scoops whose centre falls inside a bowl.
- **Pierced openwork** (arch, lattice): extrude a silhouette mask traced from a straight-on photo, with thickness
  `min(t_max, sqrt(2 * 0.9 in * distance_to_edge))` so thin members come out round in section, not slabs.
- **Fins and seat backs** that lean and hook: model the panel as `|y - y_mid(z)| - t(z)`, with `y_mid` curving with
  height, a crest height that peaks off-centre, and the hook as a tapered capsule at the tip.
- Rims added as separate tori read as rope handles; leave the rim to the cut.
- Grid size: 0.12 in for a 96 in log (about 800x130x90 voxels) is the practical limit in numpy; small pieces at
  0.07 in. Light smoothing on the mesh (0.45) keeps ridges sharp.

## Pitfalls seen
- Fitting a piece's turn from an angled photo is easy to get wrong by 180 degrees or mirrored. Render four turns
  (and the mirror) side by side at 16 samples against the crop and pick by silhouette.
- A work-in-progress process photo (chalk lines, raw wood) may show parts that were cut away later; the chalk is
  usually where it was cut.
- Scoops that lower the top surface also make bowls shallower; raise the blank height to compensate.
- Floors and wood blow out under bright area lights with clearcoat: keep floor coat 0.15 to 0.35, add roughness
  variation, lower exposure; walnut base colour around (0.06, 0.03, 0.015) with low ring contrast.
- Channels laid out by rule (concentric lanes that part round each pocket, one common wave) read as machine
  knurling and failed a blind review. Start each stream at a random point on the rim, pull it toward the pockets
  and bowls (inverse-square sinks plus a little swirl), taper width and depth as it goes, and stop it at a polished
  collar round the pocket. Seed a second set inside the field so nothing between the pockets is left blank.
  Even, evenly spaced grooves on a rim edge also read as knurling: leave the edge plain.
- A handle grown out of a carved slab: smooth-union the slab with the handle SDF (k about 24 mm), cap the
  collar a few mm above the top, then cut the socket as `max(F, -(handle_sdf - gap))`. The gap is subtracted:
  `handle_sdf + gap` makes the socket smaller than the tenon (a clash that grows as the gap grows).
- Grip ends: the clearance cut that keeps a grip off a curved body shaves the last section into a frayed shell
  if the centreline ends inside it. End the centreline one section radius outside the clearance surface, and
  stop scoop lanes and pierced slots short of a thin end (lanes to about 0.8 of the length).
- Check every assembly with exact solid booleans (manifold3d, intersection volume over 0.02 mm3 = clash), not
  ray tests; it finds lug, liner, seat and tenon clashes a render hides.

## Outputs
Render pairs (photo | CAD) on a brand comparison sheet, a `.blend` built from decimated meshes (about 30 MB), a web
GLB under 3 MB (`gltfpack -cc`), one STL per piece, and a plan + elevation SVG traced from the same meshes by
rasterising the projected triangles and following the contour (`cv2.findContours` + `approxPolyDP`).

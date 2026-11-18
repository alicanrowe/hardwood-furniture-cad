# Modelling rules (Blender, build123d, CadQuery)

## Geometry
- One part = one closed solid (watertight, outward normals, one body). Printed parts too: an open mesh can't be sliced.
- Build wood parts as plain boxes with box cuts. Every cut opens onto the face it is cut from.
- Never "fill" an old hole by adding a plug of geometry: rebuild the part without the cut.
- Never leave booleans that create steps under 1/8 in except deliberate clearances.
- When a design change removes a feature (dowels, lid, pins), remove its cuts from **every** mating part too.
- When a joint changes, trim the old part back to the new seat (an old tenon or foot left running into solid wood shows up as `interference`). Never dismiss an overlap on an open mesh as an artefact: close the part first, then measure.
- After a boolean rebuild (trimesh, manifold3d), copy each part's material back from the source file before export, and list materials per part in the version diff.
- Export GLBs with split normals (`scripts/split_normals.py`) so flat faces don't streak in viewers.
- **Clearing old cuts with a convex hull:** hull only the run of the part that is prismatic (for example the tapered length of a leg below its apron joints), then union it back with the untouched part. Hulling the whole leg bridges from a plumb top block to the taper and silently adds wood. Afterwards, diff section areas at several heights outside the cleared zone; they must match the old part exactly.
- **A rail that ends on a leg:** cut its ends to the leg face over the whole rail section. Trimming only by the leg solid (`rail - leg`) leaves an ear wherever the rail is deeper than the leg, behind or in front of it, and that ear runs into runners and kickers.
- **Drawer side grooves** run through the front tails; the half-blind lap hides them. A groove that stops at the tail baseline makes the bottom crash into the tails.

## Units and axes
- Source models: inches, Z up. GLB exports are **metres, Y up** (Blender's glTF export): pass `--units m` to cadcheck.
- Name parts by role and position: `Stand_Leg_FL`, `Side_L_Rail_Top`, `Drawer_Bottom`, `Lid_Spline_1`. Inserted parts keep `Tenon`, `Tang`, `Spline`, `Tongue`, `Dowel`, `Peg` in the name so the checker knows they go into a host.
- **Decorative parts that only look like joinery** (a cosmetic spline, an inlaid key, a faux peg with nothing behind it) are marked `"role": "ignore"` in the spec, or named `Deco_*`, so they aren't checked as joints. Say in the notes that they carry no load.

## Versions (the stale-model problem)
- Every export gets a new letter (v1a, v1b ...) and its sha256 prefix written on the project page.
- Before editing, open the file the project page names as current and check its hash. If the hash doesn't match, stop and find out why.
- Keep the previous version next to the new one; never overwrite in place.
- After the export, the cut list, drawings, renders and any other copies must be regenerated from the same file, and the project page says which hash each was made from.

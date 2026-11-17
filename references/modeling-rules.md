# Modelling rules (Blender, build123d, CadQuery)

## Geometry
- One part = one closed solid (watertight, outward normals, one body). Printed parts too: an open mesh can't be sliced.
- Build wood parts as plain boxes with box cuts. Every cut opens onto the face it is cut from.
- Never "fill" an old hole by adding a plug of geometry: rebuild the part without the cut.
- Never leave booleans that create steps under 1/8 in except deliberate clearances.
- When a design change removes a feature (dowels, lid, pins), remove its cuts from **every** mating part too.

## Units and axes
- Source models: inches, Z up. GLB exports are **metres, Y up** (Blender's glTF export): pass `--units m` to cadcheck.
- Name parts by role and position: `Stand_Leg_FL`, `Side_L_Rail_Top`, `Drawer_Bottom`, `Lid_Spline_1`. Inserted parts keep `Tenon`, `Tang`, `Spline`, `Tongue`, `Dowel`, `Peg` in the name so the checker knows they go into a host.
- **Decorative parts that only look like joinery** (a cosmetic spline, an inlaid key, a faux peg with nothing behind it) are marked `"role": "ignore"` in the spec, or named `Deco_*`, so they aren't checked as joints. Say in the notes that they carry no load.

## Versions (the stale-model problem)
- Every export gets a new letter (v1a, v1b ...) and its sha256 prefix written on the project page.
- Before editing, open the file the project page names as current and check its hash. If the hash doesn't match, stop and find out why.
- Keep the previous version next to the new one; never overwrite in place.
- After the export, the cut list, drawings, renders and any other copies must be regenerated from the same file, and the project page says which hash each was made from.

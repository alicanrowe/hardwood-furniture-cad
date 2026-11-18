# Verification checklist (run before calling any model done)

1. **Automatic check:**
   `python3 scripts/cadcheck.py MODEL.glb --units m --spec <piece>.cadcheck.json --grain`
   (`--units in --up z` for a model exported in inches, Z up.) Check the `[grain]` lines first: every wood part's grain must be what the drawing says; fix wrong ones in the spec. Then read every flag:
   - `hygiene`: fix before anything else. An open part hides other errors.
   - `through`: every through-opening must be on the drawing.
   - `interference`: clear it, unless it's a known artefact listed on the project page.
   - `near_miss`: a glued face that doesn't touch. Fix the shoulder or seat.
   - `empty_pocket`: a cut nothing fills. Fill it, stop the groove, or remove the cut.
   - `protrude`: a tenon, tang or spline sticks out of its host.
   - `cross_grain`: glued with crossing grain over 4 in. Change the joint (wood-movement.md), or, if it's attached so it can move (glued at the front only, slotted screws), say so in the spec's `movement_ok` with the reason.
   - `end_grain`: a butt joint with no tenon, dowel, spline or hardware. Add joinery.
   - `panel_room`: a floating panel, drawer bottom or back board has less room across the grain than it will move. Widen the groove gap or the board gaps.
   - `grain_unknown`: a wide part whose grain can't be told from its shape. Set it in the spec.
   - `skipped`: the pocket check couldn't run next to an open part; fix hygiene and rerun.
2. **Diff against the previous version:** list parts whose volume or bounds changed. Anything that changed and wasn't meant to is a stray edit.
3. **Sections:** cut a section through every changed joint and look at it.
4. **Downstream:** regenerate cut list, drawings and exports from the same file. Write the hash on each.
5. **Write back:** project page (current file, hash, what changed), and a mistakes log if you keep one.

## Cut list rows against the model

After any model change, check every cut-list row against the current GLB: for each object a row names, its sorted bounding-box extents must match the row's length, width and thickness (within 1/32 in; angled parts like roof stiles need their own local frame, so skip those or measure them in their part frame). Drop rows whose objects no longer exist. Rows carried forward from an older version go stale silently: a drawer front once printed as 2 7/16 tall when the model said 3 15/16. cadcheck does not catch this.

## Build book scope

When asked for a book of wood operations, leave out the fitting of metal parts (handles, pulls) but keep the wood cuts that receive them (their mortises), and say on the page that the metal part is not in the book.

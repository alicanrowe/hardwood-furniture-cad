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
   - `thin_web`: a web or neck under about 0.2 in holds part of a stick's section on (two grooves at a corner post, a panel groove over a rabbet or second groove, a mortise breaking into a groove). Bias the cuts outward, make them shallower, use a rabbet instead of a second groove, or thicken the part on the inside (joinery-standards.md, "Webs, necks and cheeks"). Small secondary parts in thin stock can set their own `min_web` in the spec (`"parts": {"^Box_": {"min_web": 0.125}}`). It works in 1 in slabs along the part's longest axis, so two layouts flag falsely: the pins of a through dovetail (inside a slab across the corner the pins are islands joined to the wall outside the slab) and a hole bored through a thin part, such as a vise screw through a jaw. Cut a section to confirm, then add `["^Part$", "thin_web", "reason"]` to the spec's `allow` (BASELINE kei bench, 25 Nov 2026).
   - `skipped`: the pocket check couldn't run next to an open part; fix hygiene and rerun.
2. **Diff against the previous version:** list parts whose volume or bounds changed. Anything that changed and wasn't meant to is a stray edit.
3. **Sections:** cut a section through every changed joint and look at it. For casework, draw the corner-post plan sections, the top-rail and bottom-rail top views and the end view of every profiled stick (drawings-and-printouts.md), and read the webs, necks and cheeks off them: at least 1/4 in each.
   - Every mortise at least 1/2 in from the end of its part, with a haunch filling the gap.
   - Hardware: at least about 1/2 in of wood behind every hinge screw and leaf; step every lid and door through its full swing.
   - Laser plates: `sheetcheck.py` clean (no web under the sheet thickness, nothing floating).
4. **Downstream: push everywhere.** When the design changes, regenerate from the same file, and write the hash on each: cut list (`cutlist.py`), full-size printouts (`printouts.py`), drawings and sections, the build book (`build_book.py`), renders and exploded views (`blender/stills.py`), animations, and any web viewer GLB (`split_normals.py`). Then **list every image, page and viewer that shows the changed part and confirm each one is the new version** (old features like locating strips or an old grille have a way of surviving in one forgotten image). Give replaced images new file names so caches can't serve the old one.
5. **Write back:** project page (current file, hash, what changed), and a mistakes log if you keep one.

## Cut list rows against the model

After any model change, check every cut-list row against the current GLB: for each object a row names, its sorted bounding-box extents must match the row's length, width and thickness (within 1/32 in; angled parts like roof stiles need their own local frame, so skip those or measure them in their part frame). Drop rows whose objects no longer exist. Rows carried forward from an older version go stale silently: a drawer front once printed as 2 7/16 tall when the model said 3 15/16. cadcheck does not catch this.

## Build book scope

When asked for a book of wood operations, leave out the fitting of metal parts (handles, pulls) but keep the wood cuts that receive them (their mortises), and say on the page that the metal part is not in the book.

## Every figure shows the current model (viewcheck)

A drawing that was right when it was made goes stale when the model changes. On the Moth, the stand's stretchers were replaced by low aprons and a drawer, and the book cover kept its old drawing: legs and stretchers, no drawer. cadcheck can't see this, because it checks the model, not the pictures.

`scripts/viewcheck.py` keeps a record (views.json) for every figure: its page, its kind (assembly, exploded, detail, diagram), its scope (a part-name regex) and the parts it draws with their bounds. `record` writes it from the render_drawings.js jobs file. `check` compares it with the current model and cut list:
- missing_part: a cut-list part inside an assembly or exploded figure's scope isn't drawn
- unknown_part: the figure draws a part that is gone
- moved_part: a drawn part has changed size or place
- no_record (with --pdf): a page has a picture nobody recorded

Planted case: `scripts/tests/views/` (the old cover). Run `python3 scripts/tests/test_viewcheck.py` after changing viewcheck.py.

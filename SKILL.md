---
name: hardwood-furniture-cad
description: Use when modelling, editing, exporting, drawing, rendering or writing up solid hardwood furniture in CAD (Blender, build123d, CadQuery, any GLB/STL): tables, chairs, stools, benches, casework, cases on stands, drawers, doors, beds, shelves, laser-cut plates. Gives sizes, joinery and wood-movement rules, checks the model for joinery, thin-web and wood-movement mistakes, and makes the cut list, full-size printouts, build book, renders and build animation.
metadata:
  author: Alican Rowe (@alicanrowe)
---

# Hardwood furniture CAD

Design solid-wood furniture that can actually be built and won't crack, then check the model before calling it done.

## Before modelling
0. **Do what was asked, no more.** Quote the user's words for the job. "Matching close-ups", "same layout", "re-render" or "update the page" means new pictures of the current model, with no design change. Change geometry only where the user's words ask for it, keep everything else, and list which parts changed. A brief for another thread quotes the user and lists what must not change.
1. Read `references/wood-movement.md`, the section of `references/furniture-types.md` for this kind of piece, `references/joinery-standards.md` (especially "Webs, necks and cheeks") and `references/modeling-rules.md`. For metal plates or a laser mockup also read `references/laser-cut-metal.md`. If the user has a shop profile (see `references/shop-profile-template.md`), size every mortise, groove and rabbet to their tools, and flag anything they can't cut in one setup. When you write a cutting plan for rough boards, keep every blank that still needs jointing or planing at least the jointer/planer minimum long (12 in unless the profile says otherwise), and crosscut short parts only after milling.
2. Start a project page from `references/project-template.md` and write the piece's cadcheck spec (`<piece>.cadcheck.json`): species, moisture swing (4% for a heated, air-conditioned house; 6% without AC), grain for any part whose grain doesn't run along its longest side, and which joints are attached so they can move.
3. Editing an existing piece: open the file the project page names as current and check its hash. Never build from remembered sizes.

Hardware and ornament (handles, pulls, feet, hinges, inlay motifs) are design work: build them from motifs already on the piece, and check them against the shared `design-taste` skill (`../design-taste/` next to this skill: principles, banned moves, and the rubric every render is scored with before it is shown). A taste remark from the client goes into its `critique-log.md` the same day, then into its principles, and the skill is published with `_publish/sync.sh design-taste`.

Modelling an existing carved or sculpted piece from photos (no cut list, "make the CAD match the pictures"): follow `references/photo-matched-carving.md` instead of the joinery steps; its make-and-check loop renders from cameras solved from the photos and compares side by side.

## While modelling
- Plain boxes with box cuts; one part = one closed solid; never fill an old hole, rebuild the part.
- Shoulders square and seated (cut to the leg's angle on raked or tapered legs); blind mortises keep at least 1/8 in to the far face; tenon height = mortise height.
- **Leave wood around every cut:** at least 1/4 in of web between two cuts in one stick and 1/4 in cheeks (more in ash and oak). Where two grooves meet in a corner post, measure the neck between them in a plan section; bias grooves and tenons toward the outside and go shallower before it drops under 1/4 in. Don't put a panel groove and a second groove or rabbet in one stick so they leave a thin web: use a rabbet on the other edge, thicker stock, or two pieces.
- **Thicken on the inside only:** a rail thinner than its post gets filled out flush with the inside of the post, so the outside look doesn't change; then move whatever sat against the old face.
- **Mortises start about 1/2 in from the end of a leg or stile,** never 1/4 in; fill the gap with a haunch on the tenon.
- **Muntins get long tenons** (about 3/4 in at the top, 1/2 in at the bottom) in deeper pockets cut inside the panel groove, so the groove still locates everything.
- **A case locates on its stand with a hidden rabbet around the case bottom over a tongue on the aprons,** never glued-on locating strips.
- **Laser-cut plates:** no bar, web or tip thinner than the sheet; every motif tied into the bars (`scripts/sheetcheck.py`).
- No pegs, dowels, pins, wedges, plugs, inlays or round holes unless they're on the drawing.
- Wood movement: never glue long grain across long grain over about 4 in. Tops on buttons, clips or slotted screws; panels, drawer bottoms and back boards float with room across the grain; casework grain wraps the box; runners, kickers and side mouldings glued at the front only; breadboard ends glued in the middle only.
- Per-part wood: give secondary woods their own `species` (a cedar drawer bottom) and set `cut` (flat, rift, quarter) in the spec. Ripped-and-flipped or narrow-board glue-ups stay flatter but move the same total width, so leave the full room.
- Drawers and doors that are hand-planed to fit: model them at the final planed size (piston fit, about 0.005 to 0.010 in total side clearance) and say so in the project notes.
- Decorative parts that only look like joinery (a cosmetic spline, a faux peg) get `"role": "ignore"` in the spec, or a `Deco_` name.
- Hinges: pick a real hinge from `references/hinges.md` / `hinges.json`, model its leaves at the catalogue size (better: measured off the hinge in hand), and cut the mortises to `python3 scripts/hinge.py MODEL --door T --gap G`. Keep about 1/2 in of wood behind every screw, check the full swing, and order by how they're sold (Brusso: by the pair, so 4 hinges = 2 pairs).
- Figure: side and door panels plain-sawn with the cathedral centred and straight grain at both edges; rails, stiles, aprons and legs straight grain.
- Name parts so the checker knows their role: `Panel`, `Drawer_Bottom`, `Back_Board`, `Slat` (floating); `Button`, `Clip`, `Figure8` (fasteners that allow movement); `Tenon`, `Dowel`, `Spline`, `Tongue`, `Peg` (loose joinery); `Bolt`, `Screw`, `Hinge` (hardware); `Ply` (plywood).

## Before saying it's done
1. Export a new numbered version (never overwrite), then run:
   `python3 scripts/cadcheck.py MODEL.glb --units m --spec <piece>.cadcheck.json --grain`
   (A Blender GLB is metres, Y up. For a model in inches, Z up: `--units in --up z`.)
   Needs `pip install trimesh manifold3d numpy scipy rtree networkx`.
2. Check the `[grain]` lines against the drawing, then read every flag. Fix hygiene first, then through, interference, near_miss, empty_pocket, protrude, cross_grain, end_grain, panel_room, thin_web, grain_unknown (`references/verification.md` explains each). Anything intended goes in the spec's `allow` or `movement_ok`, with the reason.
3. Diff part volumes and bounds against the previous version: any change that wasn't meant is a stray edit.
4. Cut a section through every changed joint and look at it: corner-post plan sections, top views of the rails, the end view of every profiled stick, every mortise's distance from the end of its part (`references/drawings-and-printouts.md`). The checker doesn't see glue, short grain in curved parts, shelf sag or racking strength.
4b. **It stands flat.** `python3 scripts/check_rest.py MODEL.glb --units m --up y --feet N` fails a piece that rocks (a foot more than 0.3 mm off the floor), rolls or tips over, and gives the lean it tips at. Cushions and straps in a render are cloth-settled, not hand-posed (`references/physics.md`).
5. **Push everywhere** from the same file, with its hash on each, then list every image, page and viewer that shows the changed parts and confirm each is new:
   - cut list and milling plan: `python3 scripts/cutlist.py MODEL.glb --spec S.json --out build/`
   - board-by-board cut map, once the user's boards are logged: `python3 scripts/cutmap.py build/cutlist.json boards.json --out build/` (add `"cutmap": "build/cutmap.json"` to book.json and it becomes a page)
   - full-size printouts (red outlines, red labels, no boxes): `python3 scripts/printouts.py MODEL.glb --spec S.json --cutlist build/cutlist.json --out build/`
   - laser cut sheets: `python3 scripts/printouts.py MODEL.glb --laser 'Plate' --out build/`
   - renders on white (hero finished; process and exploded raw): `python3 scripts/blender/stills.py MODEL.glb --look look.json --out renders/`
   - build book: `python3 scripts/build_book.py book.json --out build/Build_book.pdf` (start with `--init build/cutlist.json`)
   - build animation (finish only at the finishing step): `scripts/blender/animate_build.py`, then `scripts/overlay.py`
   - web viewer GLB: `python3 scripts/web_glb.py MODEL.blend|glb MODEL_web.glb --spec <piece>.cadcheck.json --units in --up z [--pose pose.json]`, then `python3 scripts/web_grain_check.py MODEL_web.glb --spec <piece>.cadcheck.json --sheet grain.jpg` must pass (decode meshopt first). One mesh per part, grain from the spec, straight grain on long faces, end grain on ends only. Never hand-texture or regrain a viewer GLB, never use a flat-sawn or figured image in one, and never join its meshes (compress with `gltf-transform meshopt`, not gltfpack, which merges parts and drops names).
   `references/renders-and-animation.md` and `references/drawings-and-printouts.md` hold the house style: white backgrounds always, matte wood, labels in red with no box behind them. `assets/theme.json` holds the fonts and colours.
6. Renders: before the step 5 renders go out, run the grain audit in `references/rendering-wood.md` and render a grain check sheet first.
   **Glued-up parts render as their boards.** A stack-laminated, coopered (staved) or edge-glued part is shaded with `scripts/blender/laminated_wood.py`: every layer or stave its own board with its own grain, tone and log position, a faint glue line between them, and the layer rings showing as contour bands where a faired surface cuts through the stack. Never one grain stretched over the whole part, which reads as a single board bent into shape (Studio Shrine Bench, 24 Nov 2026).
6b. **Every picture is current:** record what each figure draws when you render it (`python3 scripts/viewcheck.py record ...`), then run `python3 scripts/viewcheck.py check --views views.json --model MODEL.glb --cutlist build/cutlist.json --pdf build/Build_book.pdf`. It fails a figure that leaves out a part in its scope (a stand drawn without its drawer), draws a part that no longer exists (old stretchers) or a part that has since changed, and any book page whose picture has no record (a drawing carried over from an older version). Re-render every flagged figure from the current model; never patch a new version over an old drawing.
7. Second pass: render the changed area as the three-view check sheet in `references/drawings.md` (assembled with the moving part out, a hatched section, and an exploded view of the joinery; `scripts/drawings/`), look at it against the brief or sketch, write down every problem you see, fix them, and render again. Only the second, clean pass goes out.

8. Site: if the piece has a page on the studio website, export the viewer GLB, drawing and spec table from the same file and hash (`references/site-updates.md`), then publish them with the **website-publishing** skill, which owns the page layout (render, viewer and drawing inline with the spec table), image and GLB optimisation, the screenshot check loop and the PR.
9. Final renders, site stills and animations only after the design is locked; previews until then (`references/rendering-wood.md`).
10. **Render on cloud machines, never on the owner's Mac.** `stills.py` and `animate_build.py` refuse to run on macOS. Animations and other big jobs go to a render farm (RenderBeamer/GarageFarm), split one piece per machine; a Mac session is only for starting farm downloads and moving files. Upload, submit and download with the `render-farm` skill (github.com/alicanrowe/render-farm): headless Blender upload plus the GarageFarm web manager, so nobody has to click renderBeamer.

## At the shop (build-day questions)
- Answer from the project's own build book, cut list, milling plan and board log, never with generic milling advice and never from memory. Find the step the user is on (which boards, which faces are done) and give the next operations for those boards. For "what do I cut from board C?" run `python3 scripts/cutmap.py build/cutlist.json boards.json --board C --only '<today>'` and give its line. If a board isn't logged yet, log it first (ask only for the size you can't read from the photo); if the map says NEED WOOD, say so instead of inventing a board.
- Map the user's boards to parts by their sizes and marks, using the cut list's rough blank sizes (finished + 1 in long, + 1/4 in wide, short parts kept in 12 in or longer blanks for the jointer and planer). Ask only for a size you can't read from the photos, such as thickness.
- **Caveman mode** is the default on the shop floor or whenever the user asks for short answers. No prose, one line per board or cut, in this form:
  `A: chop at 23 1/2, 44. Bandsaw rip 1 1/4, 2. Parts: 4 posts (11), 2 top rails (10 7/32).`
  `Glue: none today.` Measurements from one end, rips from the jointed edge. Give the full explanation only when they ask for it.
- **Milling questions get threshold commands**, in shop order (thickness, then width, then crosscut), one line per part group, in the form `Top rails: anything wider than 1 3/4, rip to 1 3/4.` Run `python3 scripts/millcmd.py build/cutlist.json --strips strips.json` (strips = what is pencilled on the wood) and give its lines. Say which stock stays out of each planer setting (other thicknesses, leg glue-up layers, wide slabs). Its fit check lists every strip too short for the parts it is meant for (e.g. two 9 1/4 parts need 18 5/8, not 18) and every part with no strip left: say those as NEED WOOD, never hide them.
- **Read the marks before mapping.** The user's pencil letters are usually board ids (`24(C)` = 24 in long, from board C). The book's part keys must never reuse the same letters as board ids: use the batch/part key with a prefix (`P-K`, `P-M`) or names, and say which is which in the first line of the answer.
- **One current list.** Before answering, check which milling list, cut list and cutting plan match the current model hash. Older plans (other thicknesses, other batch letters) are moved to `old_*/` or marked SUPERSEDED on their first line, so a stale plan can't be read by mistake.
- Only answer for what they say they are building today (for example the carcass only).
- The build book carries a **board-by-board cut map** once boards are logged: each board's letter, chop positions from one end, rip widths, resaw thickness and the parts that come out, in the order they're cut (`references/drawings-and-printouts.md`).

## Excuses that don't count
Each of these is a shortcut that ends in a broken result. If you catch yourself thinking the left column, do the right column.

| The excuse | What to do instead |
|---|---|
| "The joint looks right in the viewport" | Run the interference/clipping check; parts passing through each other fail. |
| "Grain direction doesn't matter in a render" | Grain runs along every part. Check it before any render or GLB ships. |
| "It's only the small 3D preview" / "the texture is named flat, so figure is expected" | The preview is what most people see. Build it with `web_glb.py` and pass `web_grain_check.py`; no name exempts a texture from the straight-grain check. |
| "One walnut texture over the whole sculpted plank looks clean" | A glue-up is many boards. Shade it with `laminated_wood.py` so each layer or stave shows its own grain and the glue lines; check a close-up of an oblique cut. |
| "The sizes are fine, nobody sits on it in CAD" | Run seating-load-check on anything people sit on. |
| "While I'm in here I'll also tidy/refactor this other bit" | Change only what the task needs. Smallest diff that works; no new options, helpers or files nobody asked for. Note other ideas for later instead. |

## Keep this skill improving
Any problem found with a model, a drawing or a render that a rule here would have prevented gets written into the matching reference file (modelling, joinery, furniture types, wood movement, rendering) in the same session. If the checker should have caught it, add a planted test piece to `scripts/tests/` too. Then commit and push.

After changing `scripts/cadcheck.py`, run `python3 scripts/tests/make_fixtures.py && python3 scripts/tests/run_tests.py`: all planted mistakes must be caught with no false alarms. After changing `scripts/cutmap.py`, run `python3 scripts/tests/test_cutmap.py`; after `viewcheck.py`, `python3 scripts/tests/test_viewcheck.py`; after `web_grain_check.py` or `web_glb.py`, `python3 scripts/tests/test_web_grain.py` (5 of 5).

Lessons already folded in (18 Nov 2026): shop answers guessed instead of read from the book (now `cutmap.py --board`); long prose on the shop floor (caveman mode); no single board-by-board map with fence order (now `cutmap.py`); a redesign started when only matching pictures were asked for (step 0); a render started on the owner's Mac (step 10). 20 Nov 2026: a milling list sorted by part instead of by the strips in hand, part letters (B, C, D) clashing with the board letters on the wood, and stale plans at other thicknesses (now threshold commands from `millcmd.py`, prefixed part keys, one current list).

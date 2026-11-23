# Renders and build animations

Pictures of a piece get used on the site, in the build book and on Instagram, so they follow one set of
rules. Each rule below came from images that had to be redone.

## Every image
- **Solid white background.** Render on a white world with a shadow catcher, then flatten onto pure white
  (255) and save JPG. Never ship a transparent PNG, a keyed cut-out (jagged edges), or a dark backdrop.
  `scripts/blender/look.py` (`finish_white`) does this.
- **Frame with breathing room.** Nothing clipped: roofs, handles and legs stay inside the frame with a
  margin, and the page must not crop it with CSS either. Re-render at the size it's shown (2x for retina).
- **Current model only.** Render from the file and hash the project page names. When the design changes,
  list every image that shows the changed part and re-render each one (see "Push everywhere" in
  verification.md).
- **Smooth where it should be smooth.** Raise subdivision on curved metal and blades, shade smooth, and
  check close-ups for facets and jagged tips before sending.

## Pieces in a built world (reels, room scenes)
White backgrounds stay the rule for product images. When the client asks for a piece in a scene (a room, a landscape,
a reel world), follow the environment rules in the sculpted-metal-casting skill (`references/environments.md`
there): one aimed key with a pool of light that falls off, a satin floor that mirrors the piece but not the lamp
(light linking), ground-hugging mist only, a low 28 to 35 mm camera, and the film finish (`env_grade.py` in the sculpted-metal-casting skill).

## Materials
- **Matte PBR wood:** principled BSDF, roughness about 0.65 raw and 0.45 oiled, specular about 0.35, no
  clearcoat, no coat or sheen. Glossy wood reads as plastic.
- **Grain follows the part:** stripes along each part's length. Side and door panels: plain-sawn, cathedral
  centred, straight grain at both edges. Rails, stiles, aprons and legs: straight grain. Match the real
  boards when there are photos of them.
- **Finish by shot type:** hero shots carry the finish (oil, or charred / ebonised when the piece is). Process,
  joinery, exploded and milling shots are **plain wood**: the joinery has to read.
- **Split normals on export.** CAD meshes with shared vertices shade smooth across sharp corners and streak.
  Shade smooth by angle (30 deg) and clear imported custom normals in Blender; when writing a GLB for a web
  viewer, export split (per-face-group) normals: `python3 scripts/split_normals.py in.glb out.glb`.
- After any boolean rebuild, copy each part's material back from the source file before export (rebuilt parts
  come out with no material and render white).

## Shots
`scripts/blender/stills.py MODEL.glb --look look.json --out renders/` renders the default set: hero
(finished), process (raw) and exploded (raw), each on white. Add close-ups with `"only": "REGEX"` and a small
`"explode"`. Numbered exploded views get their callout numbers set in the site or book theme afterwards, on
white, with no boxes behind them.

## Build animations
`scripts/blender/animate_build.py` + `scripts/overlay.py`:
- Parts come in **in shop order** (legs, aprons, posts, rails, muntins, panels, roof, hardware), each group
  from outside the piece, then slide home.
- An **exploded view** opens the whole piece to show the joinery, raw wood.
- **The finish appears only at the finishing step,** keyed per part as a sweep from the top down. Nothing
  shows oil or char before that, however high a part floats earlier in the film.
- A slow turn at the end.
- Labels: the step title in the serif, uppercase, and one mono line under it, set straight on white, faded
  in and out (0.6 s). No boxes or plates. For a 9:16 reel keep text out of the top 220 px and bottom 380 px.
- Render frames as RGBA PNG; `overlay.py` flattens them onto white, adds labels and encodes H.264.
  Long jobs go to a render farm from the saved .blend; the overlay step runs on the frames that come back.

## Joinery reels (exploded, cut to a beat)
- **Every part moves only along its real assembly path**, or the reel shows joints that couldn't go together:
  tenons along their own axis, floating panels in-plane along their grooves, dovetailed drawer sides across the
  face of the tail board (never pulled straight back through a housing), a drawer bottom along its grooves,
  lids and roofs about their hinge pins. A tray dropped in from below hit the leg pockets in testing, so check
  each path before you pick the direction.
- **Run an animation clipping check** before any farm upload: world matrices every second frame, mesh
  intersection for each moving pair, flagged only above the at-rest overlap. Zero new clips is the gate.
- **Pacing check** on the animatic: mean frame difference per half second. Any stretch over about 2 s with
  little change is a dead hold. Give it a callout on the beat (one per tool in a tool rack) or a camera push.
- Overlays come from a per-frame track file (projected bounding boxes plus the camera), so tags and leaders
  follow the parts through the moves.


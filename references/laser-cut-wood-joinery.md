# Laser-cut joinery in solid hardwood sheet

For boxes and small casework cut on a CO2 laser from milled 1/4 in hardwood (the client's machine is a 36 x 18 in bed).
The laser cuts only straight through the sheet, so every joint is drawn in the plane of one part.

## Joints that work (and look better than finger joints)
- **Wedged through-tenon (tusk):** a wall runs through the next wall as a tenon; a flat wedge, cut in the same sheet, drives
  across a slot in the tenon. Slot starts about 1/32 in inside the far face so the wedge draws the joint tight; leave at least
  1/2 in of wood beyond the slot (shear along the grain). Taper 1:8, round striking head. Knock-down, no glue.
- **Cross-lap corner:** half-depth slots from the top in one wall and from the bottom in the other, ends running past the
  corner. Panels float on tabs through closed mortises; the lid can be the same frame made shallow, keyed into wall-top notches.
- **Brick-bond strip stack:** every course is four strips glued flat, corners alternating like brickwork, butt joints
  staggered course to course. The lamination is the joint, and strips nest almost perfectly. Bow the outer edges in plan and
  step the courses for a sculpted wall.
- **Pivot from the sheet itself:** a stack of discs, one per course, glued face to face; the lower discs glue into the body,
  the upper ones turn in the lid. Hole in the body = disc size, in the lid +0.008 in. Keep 1/4 in of web around the hole.

## Rules
- Every part comes off the same sheet (client, 25 Nov 2026: "just laser cut parts from this piece tho so no pins or maple
  wedge strip"). No bought rods or pins, no second-species strips, unless asked.
- Grain runs along the sheet's long side; box walls are nested with their length along it so the grain wraps the box.
- Floors and lid panels float with about 0.03 in room each side across the grain.
- Kerf and fit change with each milled batch: cut a test coupon first (a 1.000 in square for kerf, a strip of slots at
  T -0.004 to +0.012 in for fit), then set them and regenerate the cut files. Compensate kerf in the file: outlines grow by
  kerf/2, holes shrink by kerf/2. Inside cuts run before outside cuts.
- Feet: cut a shallow segmental arch under each wall rather than a square notch.
- Nest by searching box mixes and keeping the fullest one that fits; bounding-box nesting of these parts reaches about 75 to
  80 % of the sheet.

## Stack-laminated pieces from the sheet (PERRON boot podium, 25 Nov 2026)
- A piece glued up from many laser-cut layers face to face: cut each layer to the larger of its two faces and fair the
  stack by hand after glue-up (a quarter-ellipse roundover over the outer layers). Left stepped, the ends read as a
  serrated staircase; the client wants laminations faired smooth (design-taste B10).
- A drawer front can be the piece the laser cuts out of the face layers: the figure runs on unbroken and the kerf
  (about 0.008 in) is the piston-fit gap. Square the bottom corners of the opening so the drawer sides run on the full floor.
- Registration keys through a bowed or terraced stack: run them through the core layers only and keep 1/4 in of wood
  to the end face and to the arch at the narrowest core layer (check it in 2D for every layer, not one).
- cadcheck `thin_web` on 1/4 in sheet parts: the erosion at the default 1/4 in target eats the whole sheet thickness and
  every layer flags. Set `"min_web": 0.125` for sheet parts in the spec and check in-plane webs in 2D at 1/4 in. A tunnel
  through every layer (a drawer) still flags as a neck in cadcheck's 1 in slabs; cut a section, and if the in-plane webs
  are 1/4 in or more, put it in `allow` with the reason.

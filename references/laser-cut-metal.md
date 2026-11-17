# Laser-cut and waterjet plates (grilles, tracery, hinge plates, mockups)

Flat parts cut from sheet: stainless or brass grilles screwed into a frame, decorative tracery, cardboard or
MDF mockups. The same rules hold for all of them.

## Rules
- **No web thinner than the sheet.** Every bar, bridge, scroll and the tip of every point is at least the
  sheet thickness wide (1/16 in stainless: 1/16 in minimum; more is better for anything that gets handled).
  Narrower bits burn away, warp from the heat, or snap. Pointed tips: end them round at that width.
- **Every motif is tied into the bars.** A leaf, a ring, a C-scroll or the middle of a letter must connect to
  the frame or the bars on at least two sides; anything only touching at a point, or not at all, falls out.
- **Holes and slots at least the sheet thickness wide;** screw holes clear the screw, and sit at least
  1.5 x the hole diameter from any edge.
- **Leave a solid border** wide enough for the screws (at least 3/16 in plus the hole) and for the plate to
  sit flat in its rabbet or against its frame.
- **Draw cut sheets as red outlines only:** one closed outline per cut, no fills, no black in the openings,
  1:1, hairline stroke (`printouts.py --laser` writes this). A filled black preview is not a cut file.
- **Mirror and compare:** left and right plates are usually mirror images. Compare outlines after every
  edit: a missing cut-out on one side is easy to miss.
- **Plates move when the wood around them moves:** when rails get thicker or a rabbet moves in, the plates
  and their screws move by the same amount. Re-check screw positions against the new rail faces.

## Check
```
python3 scripts/sheetcheck.py plate.svg --t 0.0625          # SVG in inches (--scale 0.03937 for mm)
python3 scripts/sheetcheck.py MODEL.glb --only BarPlate        # flat parts in a model
python3 scripts/printouts.py MODEL.glb --laser BarPlate --out build/   # cut sheet + check
```
`thin_web` marks bars, webs and tips narrower than the sheet; `floating` marks pieces that fall out;
`tiny_hole` marks openings too small to cut. Fix them in the drawing, not at the cutter.

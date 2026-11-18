# Drawings, full-size printouts and the build book

Everything a maker reads at the bench comes from the same model file, and says which file and hash it came
from. A book or sheet that disagrees with the model is worse than none.

## Sections the reviewer will ask for
Draw these for every frame-and-panel or casework piece, and read the numbers before anyone else does:
- **Plan section through each corner post** at a rail, with the neck between the two grooves marked and
  measured (red), the inside block and the outside cheek dimensioned. Show options side by side when the
  neck is short (as drawn, grooves biased 1/16 out, grooves 3/32 out) with the numbers under each.
- **Top view of the top rails and of the bottom rails** (a plan cut just below the top and just above the
  bottom), with a detail of one corner showing tenon length and thickness.
- **End view and section of every profiled stick** (a rail with a groove and a rabbet, a moulded edge):
  webs and cheeks dimensioned. This is where the thin-web mistakes show.
- **Cross-section through a bay** of a case, from roof to stand, showing how the floor sits and how the case
  locates on the stand.
- **Leg and stile sheets** with every mortise's distance from the end of the part.

## House style
- White page. Wood in section: a pale wood fill with a light hatch; end grain a shade darker.
- **Dimensions and labels in red, straight on the page: no white box behind them.**
- Titles in the serif, uppercase; dimensions and notes in the mono; fractions to 1/32 in.
- Section names (A-A) and detail circles in red, matching the call-out on the parent view.
- The fonts and colours live in `assets/theme.json`; every script reads it.

## Full-size printouts (`scripts/printouts.py`)
- 1:1, three views per lettered part (face, edge, end), drawn as **red outlines**, labels red with no box.
- A roll PDF (36 in plotter roll), a tiled letter PDF (overlap, crop marks, page grid A1, A2 ..., a 1 in
  check square on every page) and an SVG.
- Print at 100%. Measure the check square on the first page before anything is cut.
- Use them to pick boards for figure (cathedral centred on panels, straight grain on frame parts), to
  transfer curves and bevels, and to set stops.

## Cut sheets
Laser, waterjet and CNC sheets are **red outlines only**, one closed path per cut, hairline stroke, 1:1.
No fills. Run `sheetcheck.py` on them (laser-cut-metal.md).

## Cut list and milling plan (`scripts/cutlist.py`)
Lettered parts (A, B, C ...), finished sizes T x W x L with L along the grain, grouped into milling batches
by species and thickness (one planer setting each), strips by rip width, cross-cuts longest first, and rough
board feet to buy. Hardware is listed apart with a reminder to check how it is sold (hinges by the pair).

## Build book (`scripts/build_book.py`)
Cover with the hero render, about, tools, lettered parts list, milling plan, then numbered steps (picture,
parts, text, a red "Check:" line), finishing, and the sheet index. Process pictures are plain wood; only the
cover and finishing pages show the finish. Every page's footer carries the model file and hash.
Start one with `python3 scripts/build_book.py --init build/cutlist.json > book.json`.

## Board-by-board cut map (build book, Part 1)

Once the user's boards are logged (letter, length, width, thickness, defects), the book gets one line per board, in cutting order:
`A (20 1/4 x 8 9/16 x 1 1/4): chop at -. Bandsaw rip 3 11/16, 3 11/16. Resaw in half (slice 9/16). Parts: 8 side panels.`
Chop positions are measured from the labelled end, rips from the jointed edge, resaw slices 1/8 in over the finished thickness. Keep every blank that still goes over the jointer or planer at least 12 in long. Group the lines by what gets built that day (carcass, stand, roof), and list what gets glued that day, or "none".
Make it with `scripts/cutmap.py` from the cut list and the board log (never by hand): it places every part exactly once, keeps milling blanks 12 in or longer, lists rips widest first (fence order), resaws boards that are thick enough, and prints NEED WOOD rather than inventing a board. `--board C` prints one board's line for a shop-floor answer; `--only 'post|rail'` limits it to today's parts.

# Hinges for fine furniture

The data lives in `hinges.json` (71 hinges: Brusso, Lee Valley, Whitechapel, Sugatsune, SOSS, Horton Brasses, Rockler, Häfele, Blum). `scripts/hinge.py` reads it and works out the mortises for a given door:

```
python scripts/hinge.py --list knife
python scripts/hinge.py 205H1 --door 3/4 --gap 1/16
```

**Confidence.** Each record carries its source:
- *maker chart* and *retailer page* records were read off the maker's or seller's own page: the Whitechapel spec chart, and the Lee Valley butt, knife and double-offset pages.
- *secondary* records came from search summaries of those catalogues. Check them against the hinge before you trust them.

Whitechapel's own advice holds for every record: "any hinge or other piece of mortised hardware should always be fitted empirically rather than by measurement." Buy the hinges before you finalise the drawing, measure them with calipers, and put those numbers in the model.

## Modelling a hinge in CAD

- **Model the hinge as its own part.** Name it `Hinge_*` so cadcheck treats it as hardware. Model its mortises as real cuts in both the door and the case.
- **Mortise depth matches the hinge, and the door gap comes out of the hinge.** It is not a separate offset.
- **Screws** go in as `HScrew_*` parts, or as pilot holes sized for the gauge in the record.
- **Allow the hinge in the spec, not each touch.** Add `["^Hinge", "^(Hinge|HScrew)", "hinge leaves and knuckles"]` to the spec's `allow` list. The hinge legitimately touches its mortises.
- **Two or more doors:** the hinge line must be a single straight axis. Check that knife-hinge mortises in the top and bottom line up on the same pivot axis.

## Types: how each works and how it's fitted

### Butt hinge (Whitechapel 205/206, Lee Valley 00D, Brusso CB, Horton)

- **How it works:** two leaves on a knuckle, swinging on a pin. It is mortised into the door edge and the case side.
- **Depth per leaf** = (barrel diameter − door gap) / 2. This is Whitechapel's rule, and it's the same for flat and tapered leaves. With a 1/4 in barrel and a 1/16 in gap that gives 3/32 in, equal to the leaf.
- **Mortise width:**
  - For the pin centre to sit just proud of the case face, use open width / 2 − about 1/32. The door then clears the case as it opens.
  - Loose-pin and ball-tip hinges show the whole barrel: use open width / 2 − barrel / 2.
- **Mortise length** = the hinge length.
- **Third hinge:** use one when a door is over about 48 in. A light tall door wants it to resist warp, and a heavy one for load.
- **Extruded vs cast:**
  - English cast hinges have tapered leaves, thick at the knuckle.
  - Extruded hinges (Whitechapel, Brusso machined from bar) are stronger, flat, and square to the barrel.
  - Stamped and rolled hinges develop play. Avoid them on fine work.
- **Screws:** brass screws snap in hardwood. Tap each hole with a steel screw of the same size first. 5/8–3/4 in long is plenty in hardwood.

### Stop hinge (Brusso JB series)

- **How it works:** a butt hinge with a stop machined into the knuckle. The lid stops at 95° and holds, with no chain or stay.
- **Fitting:**
  - The leaves have to be fully mortised so the stop faces meet squarely. A shallow mortise lets the lid go past 95°, and over time the stop wrenches the screws.
  - Lid weight is the limit. The leverage on the screws is high, so step up a size for heavy lids.

### Quadrant hinge (Brusso quadrant)

- **How it works:** a butt hinge with a curved stay that slides into a deep slot in the box wall, so it holds the lid at about 95°.
- **Fitting:**
  - The wall needs room for the stay mortise. The small Brusso needs a 3/4 in deep mortise and a wall at least 3/8 in thick. The large one needs just over 1 in of depth and a wall of 5/8 in or more.
  - Model the stay slot. The tool flags it as an empty pocket if the stay isn't modelled, so model the stay too.

### Knife hinges

The door turns on a pin through two flat leaves. One leaf is mortised into the top and bottom of the door, the other into the case. From the front you see only a thin line.

- **Straight (centre pivot):**
  - **Pivot position:** the pivot sits in the door's thickness. The door is inset and opens to about 90°, limited by the case side.
  - **Door thickness:** Lee Valley and Brusso say the door should be at least the leaf width + 1/8 in. Brusso's centre pivots say leaf width + 1/4 in (1/8 in of wood each side).
- **Offset (L-shaped, Brusso L series):**
  - **Pivot position:** the pivot sits just outside the case face, so the door swings clear. Use these on inset doors that must open past 90°, or with a bead at the edge.
  - **Thick doors:** L-37 suits 5/8 in doors. L-39 has an extended knuckle for thicker stock or a wider swing.
- **Double offset (Brusso, Lee Valley 05H0135):**
  - **Pivot position:** the pivot is outside both the door and the case, so the door folds back to about 270° and lies flat against the case side.
  - **Door thickness:** the door is at least the offset + 1/8 in.
- **Fitting knife hinges:**
  - **The case must be square and flat.** The two pivots have to be on one straight axis, so any twist in the case shows as a door that binds or a gap that varies.
  - **Order of work:** cut the case mortises first. Then fit the door to the opening with a hand plane, mark the door mortises off the hung leaves, and cut them.
  - **Gaps:** the top and bottom gap is the thickness of the pivot washer, not the leaf. Plane the door's top and bottom to that.
  - **Hanging:** the door can't be hung after the case is glued if the bottom leaf is in a fixed bottom. Hang it before glue-up, or use the version with a removable leaf.

### Concealed barrel hinges (SOSS, Sugatsune HES3D)

- **How they work:** a linked body sits fully inside two deep mortises, one in the door edge and one in the case edge, so nothing shows when closed. They open to 180°.
- **Door thickness:** the door must be at least the hinge's minimum. For example, SOSS 203/204 need 3/4 in, SOSS 208 needs 1 in, Sugatsune HES3D-90 needs about 7/8 in, and HES3D-120 needs about 1 1/8 in.
- **Mortise:** a two-step mortise, a shallow outline for the face plate and a deep pocket for the body. Use the maker's template.
- **Edges:** the edge must be dead square, or the door sits proud.
- **Adjustment:** the Sugatsune HES3D adjusts in three axes after hanging. SOSS doesn't, so cut it perfectly.

### Euro cup hinges (Blum CLIP top, Häfele, Grass)

- **How they work:** the cup sits in a 35 mm hole in the back of the door and clips to a mounting plate on the case side. They adjust in three ways and have soft close options.
- **Boring:** bore at least 13 mm deep, 3–7 mm from the door edge to the edge of the hole.
- **Overlay** = X + B − H. X is the hinge constant with a 0 mm plate, B is the boring distance, and H is the plate height. Look up X in the maker's table for the exact hinge.
- **Door thickness:** at least about 16 mm, so 3/4 in doors are fine.
- **Where to use them:** good for kitchens and shop furniture. On fine solid-wood work they read as utility hardware, and the cup weakens a thin frame-and-panel stile.

### Lift-off hinge (Brusso LH-201)

- **How it works:** a butt hinge whose leaves separate, so the door lifts off for finishing or moving.
- **Fitting:** mortise it like a butt. Put the pin leaf on the case, pointing up.

### Non-mortise hinge (Horton 2 1/2 in ball tip)

- **How it works:** the leaves nest inside each other when closed, so there's no mortise.
- **Fitting:** the door needs a 2–3° back bevel on its hinge edge. It suits a 3/4–1 in door. Traditional look, quick to hang. The gap is set by the hinge.

### Drop-leaf hinge (Rockler)

- **How it works:** an asymmetric hinge. The long leaf goes on the drop leaf and spans the rule joint, and the short leaf goes on the fixed top.
- **Fitting:**
  - The knuckle sits in a recess under the top, and the pin centre has to sit exactly at the centre of the rule-joint radius.
  - Model the rule joint and the hinge together, and check the leaf clears through the whole swing.

### Card-table hinge (Häfele folding table hinge)

- **How it works:** mortised into the edges of the two halves of a folding top. It lies flush in both the folded and the open position.
- **Fitting:** the recess depth is set by the top thickness: 14 mm for a 16 mm top, 16 mm for 18 mm, 19 mm for 21 mm, 23 mm for 25 mm, and so on. The table is in the record.

### Piano (continuous) hinge (Lee Valley)

- **How it works:** a hinge that runs the full length of a lid or fall front.
- **Fitting:**
  - Leaves are thin: 0.040 in in plated steel, 0.037 in in stainless. It's usually surface mounted or set in a shallow rebate.
  - Hard to make look fine. Use it where strength along the whole length matters more than looks, such as a fall-front desk or a tool chest.

## Choosing quickly

| Job | Hinge |
|---|---|
| Small box lid that must hold open | Brusso JB stop hinge, or a quadrant hinge in a thick wall |
| Small box lid that just swings | Brusso CB butt, Whitechapel 206 series |
| Inset cabinet door, traditional | Butt hinge (Whitechapel 205/206 extruded, Horton), or ball tip with the barrel showing |
| Inset door, nothing visible from the front | Straight or offset knife hinge |
| Door that folds flat against the case | Double-offset knife |
| Seamless panel door, nothing showing when closed | SOSS or Sugatsune HES3D (needs a thick door) |
| Adjustable overlay door, shop or kitchen | Blum CLIP top |
| Drop-leaf table | Rule joint plus drop-leaf hinges |
| Folding card table | Card-table hinges |

## Sources

- Whitechapel Ltd., *Cabinet Hinge Specs*: the butt chart and the mortise depth rule.
- Lee Valley product pages for the fixed-pin butts, straight knife hinges and Brusso double-offset knife hinges: sizes, screws, and the door thickness rule.
- Brusso collection pages: the 95° stop, the pivot behaviour, and machining from bar stock.
- Secondary records come from search summaries of the Brusso, SOSS, Sugatsune, Horton, Rockler, Häfele and Blum catalogues, and are marked as such in the JSON.

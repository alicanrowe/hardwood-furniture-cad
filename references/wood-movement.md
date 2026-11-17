# Wood movement (solid hardwood)

Wood swells and shrinks **across the grain** with the seasons and barely at all along it. Almost every failed piece of solid-wood furniture is a joint that fights this. `cadcheck` checks it (cross_grain, panel_room) once every wood part has a known grain direction.

## How much
Seasonal movement across the grain = width x coefficient x moisture swing. Use 4% MC swing for a heated/air-conditioned house (New York); 6% for a porch, cabin or a house without AC.

| Species | Radial (quartersawn) | Tangential (flatsawn) | 12 in flatsawn board, 4% swing |
|---|---|---|---|
| Walnut | 0.00190 | 0.00274 | 0.13 in |
| Cherry | 0.00126 | 0.00248 | 0.12 in |
| White oak | 0.00180 | 0.00365 | 0.18 in |
| Red oak | 0.00158 | 0.00369 | 0.18 in |
| Hard maple | 0.00165 | 0.00353 | 0.17 in |
| Soft maple | 0.00133 | 0.00289 | 0.14 in |
| Ash | 0.00169 | 0.00274 | 0.13 in |
| Mahogany | 0.00172 | 0.00238 | 0.11 in |
| Sapele | 0.00170 | 0.00240 | 0.12 in |
| Poplar | 0.00158 | 0.00289 | 0.14 in |
| Hickory | 0.00259 | 0.00411 | 0.20 in |
| Beech | 0.00190 | 0.00431 | 0.21 in |
| Birch | 0.00256 | 0.00338 | 0.16 in |
| Teak | 0.00101 | 0.00186 | 0.09 in |
(Coefficients per 1% MC change, approximate, from the USDA Wood Handbook. Quartersawn stock uses the radial column; rift is about halfway between. Cedar, alder, elm, white pine, padauk and wenge are also in cadcheck, the cedars approximate.)

## Rules
1. **Never glue long grain across long grain over more than about 4 in.** Mortise-and-tenon cheeks are cross-grain too: keep a tenon under about 4 in wide (split into twin tenons, or haunch it).
2. **Tops** (tables, desks, cases with a separate top) are fixed with buttons, figure-8s, Z-clips or screws in slotted holes, never glued to aprons or rails. Fix the centre, let the edges move. Button slots leave 1/8 in or more room.
3. **Panels float.** Frame-and-panel, headboards, backs: panel edges sit in a groove with no glue, with room across the grain of at least half the seasonal movement each side (fit in summer: tight; in winter: full gap). Prefinish panels so bare wood doesn't show when they shrink.
4. **Breadboard ends:** glue only the middle 2 to 3 in of the tongue; peg the outer pegs through elongated holes in the tongue.
5. **Casework: grain wraps the box.** Sides vertical, top and bottom side to side, so the whole case moves front to back together. Anything glued across that (runners, kickers, cleats, mouldings on the sides) is glued at the front only and screwed in a slot or sliding-dovetailed at the back.
6. **Drawer bottoms:** grain runs side to side, so movement goes out the back. Bottom in a groove at the front and sides, slotted screw at the back, no glue.
7. **Backs:** shiplap or tongue-and-groove boards with gaps (1/16 in per 6 in board), one screw per board at the centre of each rail, or a floating panel; plywood is fine and doesn't move.
8. **Mouldings across the grain** (crown on a case side): glue the front 2 in, then nail or slot-screw.
9. Plywood, MDF and veneered ply don't move; mixing them with solid wood frames is fine.
10. **Glue-ups of narrow or ripped-and-flipped boards reduce cupping, not movement.** Ripping a wide board and flipping alternate strips (or gluing up several narrow boards) balances the cup so the panel stays flat, but every strip still shrinks and swells by the same coefficient, so the total change in width is the same as one wide board. Size grooves, slots and button room for the full width either way. Only the cut changes the amount: quartersawn uses the radial column, rift is about halfway, flatsawn the tangential. Set `"cut"` and `"species"` per part in the cadcheck spec (e.g. `"^Drawer_Bottom$": {"species": "cedar", "cut": "flat"}`).
11. **Per-part species.** Secondary woods (cedar, poplar, pine drawer parts) move differently from the show wood; give them their own species in the spec so the room is worked out right.

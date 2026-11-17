# Shop profile (fill in for your shop)

Size joinery to the tools you actually have, so every mortise, groove and rabbet in the model can be cut in one setup. Copy this file to your project folder, fill it in, and point Claude at it.

## Machines and tooling
- **Mortising:** e.g. a hollow chisel mortiser with 1/4 and 3/8 in chisels. Mortise width equals the chisel, and tenon thickness matches it. If you drill and pare, or use a router, say so.
- **Router bits:** e.g. a 1/4 in upcut spiral (it leaves rounded ends, radius 1/8 in), a 1/4 in straight, a rabbeting bit with bearings. List the widths you can cut.
- **Table saw:** blade tilt (left or right) and which side the fence is on. The bevel cut is planned on that side. List the dado stack widths you have.
- **Hand tools:** e.g. planes for fitting drawers and doors to a piston fit.

## Defaults this sets for CAD
| Joint | Default size |
|---|---|
| Mortise and tenon in 3/4 in stock | |
| Mortise and tenon in legs and rails | |
| Frame-and-panel groove | |
| Back rabbet | |
| Stopped groove or slot | |
| Hinge mortise | |

When a drawing calls for a size the shop can't cut in one setup, Claude flags it and offers the nearest size the shop can cut.

## Example
An example shop has a hollow chisel mortiser (1/4 and 3/8 in chisels), 1/4 in spiral and straight router bits, a Whiteside rabbeting bit, and a table saw with 1/4–1/2 in dado inserts. In that shop:
- **Tenons:** 3/4 in stock gets 1/4 in tenons, and legs and rails get 3/8 in.
- **Grooves:** 1/4 in.
- **Slots:** cut with the spiral bit and rounded at the ends.
- **Hinge mortises:** routed, then pared square.

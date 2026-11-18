# Joinery standards (inches)

Fine-furniture defaults. A dimension on a drawing you've approved beats this page.

## Fits and clearances
| Situation | Value |
|---|---|
| Tenon cheek in mortise | 0 in model (line to line); shop fits by hand |
| Tenon end to mortise bottom | 1/64 to 1/16 short (glue room) |
| Panel edge to groove bottom | 1/16 short each side (panel floats, never glued) |
| Panel thickness in groove | fills the groove width at the tongue |
| Case rabbet over a stand's apron tongue | 1/32 each side |
| Free-standing insert to wall (racks, trays) | 1/16 |
| Bottom ply in its groove | 1/64 each side, glued |

Anything 0.08 to 0.30 in between two glued faces is a mistake (a shoulder that doesn't seat). `cadcheck` flags it as near_miss.

## Webs, necks and cheeks (the gut check)
Every groove, rabbet and mortise takes wood out of a stick. Before you size one, look at what's left.
- **At least 1/4 in of wood between any two cuts** in one stick: a panel groove and a rabbet, a groove and a mortise, two grooves meeting at a corner post. A 1/8 in web snaps when you clamp it or split it along the grain later. An experienced maker's eye catches this at a glance on a printed section (a reviewer failed a 3/4 in rail with a 3/8 deep panel groove over a case-bottom groove: 1/8 in web).
- **Solid cheeks:** each cheek beside a groove or mortise at least 1/4 in, 5/16 or more in soft or coarse woods (ash, oak).
- **Corner posts with two grooves:** measure the neck, the diagonal between the two groove corners, in a plan section. Two 3/8 deep grooves set 1/4 in from the outside of a 1 in post leave a 0.18 in neck. Fixes, in order: bias the grooves and tenons toward the outside (1/16 in out took the neck to 0.27 in and kept a 3/16 in outside cheek); make the grooves shallower (5/16 instead of 3/8); use a thicker post. Aim for a neck of at least 1/4 in.
- **Don't split one stick into two jobs** when the cuts crowd each other: drop the second groove and use a rabbet on the other edge (the floor drops into a rabbet on the inside bottom edge of the rails instead of a second groove), or make it two pieces.
- `cadcheck --min-web 0.25` flags webs and necks under about 0.2 in (thin_web). Still cut a section through every stick with more than one cut in it and read the numbers yourself.

## Thickening a part without changing the look
When a rail is thinner than the post it meets, the shoulder seats on part of the post and the inside corner is a lone square. Thicken the rail **on the inside only**, flush with the inside of the post, so the outside reveal and proportions don't change. Then move anything that sat against the old inside face (racks, plates, screws, a floor rabbet) in by the same amount, and check clearances again.

## Mortise and tenon
- Tenon thickness about 1/3 of the stock: 1/4 on 3/4 rails, 3/8 on 1 1/8 aprons.
- **Shoulders are square to the tenon and seat flat on the face they meet.** On a leaning or tapered leg, the shoulder is cut to the leg's angle, never drawn as a taper from the full section down to the tenon.
- **Blind mortises have a flat floor at least 1/8 in from the far face.** A mortise never breaks through unless the drawing says "through".
- Tenon height must match the mortise height.
- Two mortises in one post leave at least 1/4 in of wood between them (1/8 in is the absolute floor in hard maple; don't design to it).
- **Keep mortises away from the end of a leg or stile.** A mortise that stops 1/4 in below the top of a leg leaves a thin cap of short end grain that blows out (a shop reviewer called this one off a printed leg sheet). Start the mortise about 1/2 in down (more on a big tenon), and fill the gap with a **haunch** on the tenon, about 1/4 in deep, so the top of the joint still looks closed and the rail can't twist.
- **Muntins and other short vertical members:** don't rely on a stub tenon that only fills the panel groove. Make the tenons long (about 3/4 in into a top rail, 1/2 in into a bottom rail, kept clear of any rabbet below) and cut deeper mortise pockets in the bottom of the groove at each muntin. The groove still locates everything during glue-up; the pocket gives the tenon real glue area.

## Frame and panel
- Panel groove 1/4 x 3/8, centred. Stopped where no panel sits (or filled with a 1/4 x 3/8 strip).
- Raised panels: flat slab plus flat raised field, no recesses.

## Case pieces (defaults)
Half-blind dovetails on the case (grain wraps the box), twin tenon or sliding dovetail drawer rails with runners, shiplapped back in a rabbet, wood buttons to hold a case on its stand. Stands: aprons mortise-and-tenoned into the legs.

### Locating a case on its stand
**Never glued-on locating strips** (they look added, fall off, and show under the case). Instead cut a **rabbet around the whole bottom of the case**: in a frame-and-panel case, on the inside bottom edge of all four bottom rails, with the floor (ply or solid) sitting at the top of the rabbet. That leaves a recess under the floor that drops over a **tongue on the inner part of the stand's apron tops**, 1/32 in clear each side. It locates the case in both directions and can't be seen once the case is on the stand. Keep the web between the rabbet and the panel groove above it at 1/4 in or more.

## Never add unless drawn
Pegs, dowels, drawbore pins, wedges, plugs, screws on show faces, inlay recesses, round holes. Every round feature must be a seat for a real part.

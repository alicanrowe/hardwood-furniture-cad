# Hardwood furniture CAD skill

A Claude skill for designing solid hardwood furniture in CAD (Blender, build123d, CadQuery or anything that exports GLB/STL) and checking the model for the mistakes that make real furniture fail.

## What's in it
- **`SKILL.md`**: the workflow Claude follows: read the rules, model, then check.
- **`references/`**
  - `wood-movement.md`: seasonal movement for 15 hardwoods and the rules for tops, panels, casework, drawer bottoms and backs
  - `furniture-types.md`: sizes, default joinery and common failures for tables, chairs, stools, benches, casework, drawers, doors, beds and shelves
  - `joinery-standards.md`, `modeling-rules.md`, `verification.md`, `project-template.md`
- **`scripts/cadcheck.py`**: a checker that reads a GLB/STL assembly (one mesh per part) and flags:
  - open or broken solids
  - mortises that break through
  - overlapping parts
  - shoulders and seats that don't touch
  - cuts that nothing fills
  - tenons that stick out
  - long grain glued across long grain over 4 in
  - butt joints with no joinery
  - panels without room to move, sized by species and moisture swing
- **`references/hinges.md` + `hinges.json`**: a hinge library for fine furniture (71 hinges from Brusso, Lee Valley, Whitechapel, Sugatsune, SOSS, Horton Brasses, Rockler, Häfele and Blum): sizes, leaf and barrel thickness, screws, door-thickness rules, how each type works and how it's mortised. Every record names its source and how sure it is.
- **`scripts/hinge.py`**: looks up a hinge and gives the mortise length, width and depth for your door and gap (`python3 scripts/hinge.py 205H1 --door 3/4 --gap 1/16`).
- **`examples/`**: a worked example on a real walnut cabinet on stand: its spec, what the checker found, and what each flag meant.
- **`scripts/tests/`**: builds a table, chair, chest of drawers, frame-and-panel door and bed, each once correctly and once with mistakes planted, and checks the checker against them. Current result: 19 of 19 mistakes caught, no false alarms.

## Install
- **Claude.ai / Claude app:** zip this folder and upload it under Settings > Capabilities > Skills.
- **Claude Code:** copy the folder to `~/.claude/skills/hardwood-furniture-cad/`.
- Checker requirements: `pip install trimesh manifold3d numpy scipy rtree networkx`.

## Quick start
```
python3 scripts/cadcheck.py my_table.glb --units m --spec my_table.cadcheck.json --grain
```
Example spec:
```json
{"species": "white oak", "mc_swing": 4,
 "parts": {"^Top$": {"grain": "x"}},
 "movement_ok": [["^Runner_", "^Side_", "glued at the front 2 in only, slotted screw at the back"]]}
```

## Limits
The checker treats every face-to-face contact as glued unless a fastener, a floating role or `movement_ok` says otherwise. Grain is taken as the longest side of each part unless you set it. It doesn't check short grain in curved parts, shelf sag, racking strength or anything about how a part is machined. It's a second pair of eyes, not an engineer. Look at sections through your joints.

Movement coefficients are approximate, from the USDA Forest Products Laboratory *Wood Handbook*.

## License
MIT. See `LICENSE`.

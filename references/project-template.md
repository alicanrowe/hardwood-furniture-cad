# <Piece name> (<species>, <type>)

## Current files (source of truth)
| What | File | Hash | Date |
|---|---|---|---|
| Model | | | |
| Drawings | made from hash ... | | |
| Cut list | made from hash ... | | |

## Key sizes and decisions
- Overall:
- Species and cut (flat/rift/quarter):
- Joinery per joint (see furniture-types.md):
- How the top / panels / back are attached so they can move:

## cadcheck spec (save as <piece>.cadcheck.json next to the model)
```json
{"species": "walnut", "mc_swing": 4,
 "parts": {"REGEX": {"grain": "x|y|z", "role": "wood|floating|insert|fastener|hardware|ply|ignore", "material": "plywood|mdf|steel|..."}},
 "movement_ok": [["REGEX_A", "REGEX_B", "why it can move"]],
 "allow": [["REGEX_A", "REGEX_B", "why the gap is intended"]],
 "skip": "REGEX of parts to leave out"}
```

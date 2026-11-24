# Photoreal product stills (why an all-CAD account reads as photographs and ours read as CAD)

Written 24 Nov 2026 after the client pointed at an all-CAD Instagram account (Blender, about 170 posts of chairs,
thrones, dining sets, cars and figures) and asked why it is so much more photoreal than ours. We pulled 60 posts and
looked at about 100 images full size, then re-rendered our Stay chair with every fix below. Learn the techniques;
never copy the pieces, motifs or staging of anyone's work.

Worked example: `scripts/blender/photoreal.py` (room, lights, materials, lens, AgX) and the film finish in the
sculpted-metal-casting skill (`scripts/env/env_grade.py`). Before/after: Stay chair, 24 Nov 2026.

## The gaps, biggest first

| # | What their images have | What ours had | Fix (in `photoreal.py`) |
|---|---|---|---|
| 1 | **The piece stands in a real place.** A concrete floor that takes the light, walls or a dark room behind, a contact shadow and a soft reflection under every foot. | A cut-out: white world, shadow catcher, flattened onto 255 white. No floor, no horizon, the piece floats. | `room("gallery")`: pale troweled-concrete floor with satin patches, pale walls, one big overhead softbox. `room("pool")`: dark room, one overhead spot throwing a pool that dies off before the frame edge. |
| 2 | **One motivated light with falloff.** A single overhead source; brightness drops off across the floor and up the walls, so there is a gradient in every part of the frame. | Key + fill + rim area lights in an evenly white world: flat, no gradient anywhere. | One key (spread 24 to 120 deg), a weak cool rim from behind, nothing else that lights the room. |
| 3 | **Metal reflects something.** Long soft highlights run down every rod and plate; the dark between them is what makes it read as steel. | Metal reflected a featureless white world, so it read as grey plastic. In a dark room with no reflectors it read black. | Two tall strip boxes beside the camera axis, invisible to camera, **light-linked to the piece only** (the satin floor mirrored them as hot blobs before linking), plus a dim top-lit world that camera rays can't see. |
| 4 | **Nothing is factory-clean.** Brushed grain, fingerprints, scuffs, polishing swirl, roughness that changes across a face; concrete with mottling and stains. | One roughness value per material, near-uniform procedural noise. | `metal()`: streaks along each part's long axis (bump + roughness), cloudy smudges moving roughness between two values, a 3% colour drift. `gfrc()`/`floor_concrete()`: low-frequency mottling plus pinholes. Keep the smudges subtle: big high-contrast blotches read as dirt, not wear. |
| 5 | **Rolled edges.** Every edge catches a thin bright line. | Knife edges from CAD: no edge highlight, parts look like card. | Bevel shader node on every material (0.8 mm metal, 2.5 mm cast). Geometry stays as modelled. |
| 6 | **A real lens.** 50 to 85 mm, camera at standing or seat height, shallow depth of field on details (f/2.8 to 4.5), the room going soft. | 70 mm, infinite depth of field, camera wherever the bounding box put it. | `camera()`: 50 mm heroes at 0.85 to 1.0 m, 85 mm f/2.8 to 3.2 details, focus on the front third, 7 blades. |
| 7 | **Tone.** Deep blacks, highlights that roll off, a narrow cool-neutral palette, fine grain, a little halation. | Standard view transform (needed for 255 white), no grade. | AgX Medium High Contrast, exposure about -0.9 for these rooms, then `env_grade.py` at strength 0.6. |
| 8 | **Detail density where the camera goes close.** Rod ends with clevises and pins, nuts, labels, cables, stitched leather; their close-ups are full of small parts. | Hardware modelled as boxes and plain cylinders. A close-up shows a rod disappearing into a block. | Not a lighting fix. Model real terminations before any close-up: clevis + pin + nut on every rod end, chamfers, a maker's plate. The clipping check below flags embedded joints. |
| 9 | **Context and scale.** Figures sitting in the chairs, a room with architecture. | The piece alone. | Optional: a seated figure or a prop only when the client asks (it breaks the white-background rule). |

What does **not** close the gap: more samples alone, a sharper denoiser, an HDRI on the old cut-out setup, or more
lights. Rows 1 to 3 are most of it.

## Settings that worked (Stay chair, 24 Nov 2026)
- Cycles, 192 spp adaptive (threshold 0.008), OIDN, filter glossy 0.4, indirect clamp 8, caustics off.
- Floor: gallery albedo 0.50, pool 0.24 (at 0.46 the pool clipped to flat white). Metal stainless sRGB 0.58,
  roughness 0.13 to 0.25. Black GFRC specular 0.18 (at 0.4 the strips turned it grey).
- Lights: gallery softbox 4 x 4 m at 3.4 m, 520 W, spread 120; pool disk 0.9 m at 3.3 m, 330 W, spread 24; strips
  0.35 x 2.2 m, 70 to 90 W, diffuse off, light-linked to the piece; exposure -0.9.
- Timing on a 4-core cloud CPU: 1200 x 1500 at 192 spp, about 7 min a still with OIDN (three stills in 21 min, 24 Nov).

## When to use which look
- **Site product squares and spec images:** still white (house rule). Use `look.py` or a near-white cyc.
- **Hero stills, Instagram, press, reels:** `photoreal.py` gallery (light) or pool (dark), after the client OKs the
  look for that project.

## Check (every pass)
1. Side by side with a reference photo or the reference account: could this pass as a photo? Name the row that fails.
2. Look for: a hot blob in the floor (unlinked reflector), metal that reads grey plastic (nothing to reflect) or
   black (reflects the dark room), a clipped flat-white pool, smudges that read as dirt.
3. Crop a detail at 100%: every edge should carry a highlight line; any rod that ends inside a block is a modelling
   fix (row 8), not a render fix.
4. Clipping: run the pairwise overlap check on the GLB (manifold3d, overlaps over 1 mm3). The model's own check must
   not exempt hardware: stays, collars, lugs and straps are where the interpenetration hides.

## What the home server's RTX 4090 unlocks
- Cycles OptiX on the 4090 is roughly 15 to 30x the 4-core cloud CPU: 2400 x 3000 at 1024 spp heroes in minutes,
  so final stills can stop trading samples for resolution. `photoreal.py --device GPU`.
- Real geometry instead of shader tricks: true bevels and micro-displacement on floors and cast parts, which cost too
  much memory and time on the cloud CPU.
- Cloth and upholstery: CLO3D on the Windows side for leather seats and cushions (stitched, creased), exported to
  Blender; the CPU route can only approximate it.
- Fast look development: interactive viewport rendering for lighting, instead of 15-second test frames.
- Animations stay on the farm when they're long; the 4090 takes the test passes and short reels.

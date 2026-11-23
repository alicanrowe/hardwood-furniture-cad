# Keeping the project site current

Every model change that alters what a visitor sees is also a site update. Do it in the same session as the model change, from the same file and hash.

This file covers what the furniture model hands to the site. How the page is laid out, how media is sized, how it's checked and how it goes live is in the **website-publishing** skill (https://github.com/alicanrowe/website-publishing): use it for the page itself.

## What to export from the model
- **Viewer GLB:** from the current model with `scripts/web_glb.py` (one mesh per part, grain from the cadcheck spec, straight grain on long faces, end grain on ends), and it must pass `scripts/web_grain_check.py`. Then look at it in the site's own viewer from two sides. Remove parts a visitor never sees (screws inside, hidden faces), decimate if needed. A viewer still showing removed parts (old stretchers, old fittings) is the most common miss.
- **Dimension drawings:** elevation, plan and section regenerated from the same model, as SVG. Note the hash on each.
- **Spec table:** sizes, species and cut, joinery, hardware (maker and model), finish, from the current cut list. Add the model version and hash.
- **Images:** final stills only after the design is locked (see rendering-wood.md, When to render); previews until then.

## Then
Hand these to the website-publishing skill: its inline layout puts the render, 3D viewer and dimension drawing side by side with the spec table, and its check loop compares them against each other before the PR. Viewer, drawing and spec table must agree: same parts, same sizes, same version.

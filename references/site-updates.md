# Keeping the project site current

Every model change that alters what a visitor sees is also a site update. Do it in the same session as the model change, from the same file and hash.

## What to update
- **3D viewer:** export the viewer GLB from the current model (decimated if needed), with the same materials as the renders. A viewer still showing removed parts (old stretchers, old fittings) is the most common miss.
- **Dimension drawings:** regenerate the elevation, plan and section from the same model. Note the hash on each.
- **Spec table:** sizes, species, finish and hardware from the current cut list.
- **Images:** replace stills only after the design is locked (see rendering-wood.md, When to render).

## Layout
- Put the 3D viewer and its dimension drawing inline, side by side on wide screens and stacked on phones, so the viewer and the drawing are read together. Don't put them in separate sections.
- Use the site's own theme (fonts, colours) for drawings and captions.

## Check before publishing
Open the page and compare viewer, drawing and spec table against each other and against the model: same parts, same sizes, same version.

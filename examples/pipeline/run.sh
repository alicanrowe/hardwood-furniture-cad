#!/bin/sh
# The whole pipeline on the test table (inches, Z up). Swap in your own model, spec, look and anim files.
set -e
cd "$(dirname "$0")/../.."
M=scripts/tests/fixtures/table_good.glb
[ -f $M ] || python3 scripts/tests/make_fixtures.py
O=examples/pipeline/out; mkdir -p $O
python3 scripts/cadcheck.py $M --units in --up z --spec examples/pipeline/table.cadcheck.json
python3 scripts/cutlist.py $M --units in --up z --spec examples/pipeline/table.cadcheck.json --out $O --title "Walnut side table"
python3 scripts/printouts.py $M --units in --up z --spec examples/pipeline/table.cadcheck.json --cutlist $O/cutlist.json --out $O --title "Walnut side table"
python3 scripts/blender/stills.py $M --up z --units in --look examples/pipeline/look.json --out $O/renders
python3 scripts/build_book.py examples/pipeline/book.json --out $O/Build_book.pdf
python3 scripts/blender/animate_build.py $M --up z --units in --anim examples/pipeline/anim.json --out $O/anim.blend --render $O/frames
python3 scripts/overlay.py $O/frames $O/anim.track.json --out $O/build.mp4

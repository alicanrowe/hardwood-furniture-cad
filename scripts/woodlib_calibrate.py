#!/usr/bin/env python3
"""Calibrate a house studio so library wood rendered there reads like the photo (references/woods.json "photo").

Why: the studios render through AgX with bright soft lights tuned for white and pale pieces, which lifts and greys
dark wood. The PM case's walnut texture was right (median 0.39 0.29 0.21) and the site card still showed it pale
pink (0.66 0.52 0.44; client review, 26 Nov 2026). A photographer would expose and grade for the
wood; we do the same once per studio and species, measured, and store the gain in woods.json "house".

  python3 scripts/woodlib_calibrate.py --studio card --glb PLAIN_BAKED.glb --spec PIECE.cadcheck.json \
      --card-loop SITE_CARDS/card_loop.py --cards SITE_CARDS/cards.json \
      --card hardwood-furniture-cad [--species walnut ash white oak] [--write]

For each species it re-bakes the GLB in that species (web_laminate.py --all), renders the card's first frame,
measures the median of the opaque wood pixels and scales the per-channel gain until the median is within 0.015 of
the photo. Pass --write to store it. Re-run whenever the studio's lights, exposure or view transform change.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import woodlib as W  # noqa: E402


def wood_median(png):
    a = np.asarray(Image.open(png).convert('RGBA')).astype(float) / 255
    m = a[..., 3] > 0.99
    c = a[..., :3][m]
    # leave out brass and steel: wood is warm and not too bright
    keep = (c[:, 0] - c[:, 2] > 0.04) & (c.max(1) < 0.97)
    c = c[keep] if keep.sum() > 500 else c
    return np.median(c, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--studio', default='card'); ap.add_argument('--glb', required=True); ap.add_argument('--spec', required=True)
    ap.add_argument('--card-loop', required=True); ap.add_argument('--cards', required=True); ap.add_argument('--card', required=True)
    ap.add_argument('--species', nargs='*', default=['walnut', 'ash', 'white oak'])
    ap.add_argument('--rounds', type=int, default=5); ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    lib = json.load(open(W.WOODS)); lib.setdefault('house', {}).setdefault(a.studio, {})
    work = tempfile.mkdtemp(prefix='wlcal_')
    spec0 = json.load(open(a.spec))
    cards = json.load(open(a.cards)); glbname = cards['cards'][a.card]['items'][0]['glb']
    for sp in a.species:
        sk, S = W.species(sp)
        target = np.array(S['photo']['median'])
        spec = json.loads(json.dumps(spec0)); spec['species'] = sk
        for rx, d in spec.get('parts', {}).items(): d.pop('species', None)
        sf = os.path.join(work, f'{sk}.spec.json'); json.dump(spec, open(sf, 'w'))
        cache = os.path.join(work, sk); os.makedirs(cache, exist_ok=True)
        subprocess.run([sys.executable, os.path.join(HERE, 'web_laminate.py'), a.glb, os.path.join(cache, glbname), '--spec', sf, '--all'],
                       check=True, capture_output=True)
        gain = np.array(W.house_gain(sk, a.studio)) if lib['house'][a.studio].get(sk) else np.ones(3)
        for it in range(a.rounds):
            lib['house'][a.studio][sk] = {'gain': [round(float(x), 4) for x in gain]}
            wj = os.path.join(work, 'woods.json'); json.dump(lib, open(wj, 'w'))
            out = os.path.join(work, f'{sk}_{it}')
            env = {**os.environ, 'CARD_CACHE': cache, 'WOODLIB_JSON': wj, 'WOODLIB_SKILL': HERE}
            subprocess.run([sys.executable, a.card_loop, a.cards, a.card, out, '0', '0', str(a.samples), '360'], env=env,
                           check=True, capture_output=True)
            med = wood_median(os.path.join(out, 'f0000.png'))
            err = float(np.abs(med - target).max())
            print(f'{a.studio} {sk} round {it}: gain {gain.round(3)} -> median {med.round(3)} (photo {target}), err {err:.3f}')
            if err < 0.015: break
            gain = gain * (W.srgb2lin(target) / np.maximum(W.srgb2lin(med), 1e-4)) ** 0.85
        lib['house'][a.studio][sk] = {'gain': [round(float(x), 4) for x in gain], 'median': [round(float(x), 3) for x in med],
                                      'err': round(err, 4), 'card': a.card}
    if a.write:
        json.dump(lib, open(W.WOODS, 'w'), indent=1); print('wrote', W.WOODS)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()

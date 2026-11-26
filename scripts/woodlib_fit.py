#!/usr/bin/env python3
"""Fit each photo-measured species' albedo (early, late, sap) so woodlib's own boards land on the photo numbers.

  python3 scripts/woodlib_fit.py [--species walnut ash] [--write]

Measures flat + rift swatches (median, 10th percentile) against references/woods.json "photo" and scales the
early/late albedo per channel, three rounds. --write stores the result in woods.json. Run it after any change to
the wood model (woodlib.color) or to a photo target; never type albedo numbers by hand.
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import woodlib as W


def measure(sp):
    cs = []
    for cut in ('flat', 'rift', 'quarter'):
        for seed in (3, 11):
            im, _ = W.swatch(sp, cut, res=(360, 120), seed=seed); cs.append(im.reshape(-1, 3) / 255)
    c = np.vstack(cs)
    return np.median(c, 0), np.percentile(c, 10, 0), np.percentile(c, 90, 0)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--species', nargs='*'); ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    lib = json.load(open(W.WOODS))
    names = a.species or [k for k, v in lib['species'].items() if v.get('photo')]
    for sp in names:
        S = W.LIB['species'][sp]; ph = S['photo']
        for it in range(4):
            med, p10, p90 = measure(sp)
            # median follows mostly the earlywood, the 10th percentile the latewood
            ge = (W.srgb2lin(ph['median']) / W.srgb2lin(med)) ** 0.9
            gl = (W.srgb2lin(ph['p10']) / W.srgb2lin(p10)) ** 0.9
            A = S['albedo']
            A['early'] = [round(float(x), 4) for x in W.lin2srgb(np.clip(W.srgb2lin(A['early']) * ge, 0, 1))]
            # latewood never darker than half the earlywood (linear): past that the rings read as painted stripes and
            # flat-sawn apexes as dark flames (PM case card, 26 Nov); the rest of the spread comes from figure and streaks
            lt = np.maximum(W.srgb2lin(A['late']) * gl, 0.5 * W.srgb2lin(A['early']))
            A['late'] = [round(float(x), 4) for x in W.lin2srgb(np.clip(lt, 0, 1))]
        med, p10, p90 = measure(sp)
        dE = float(np.abs(med - ph['median']).max())
        print(f'{sp}: median {med.round(3)} (photo {ph["median"]}), p10 {p10.round(3)} ({ph["p10"]}), p90 {p90.round(3)} ({ph["p90"]}), max err {dE:.3f}')
        lib['species'][sp]['albedo'] = S['albedo']
        lib['species'][sp]['fit'] = dict(median=[round(float(x), 3) for x in med], p10=[round(float(x), 3) for x in p10],
                                        p90=[round(float(x), 3) for x in p90], max_err=round(dE, 4))
    if a.write:
        json.dump(lib, open(W.WOODS, 'w'), indent=1); print('wrote', W.WOODS)


if __name__ == '__main__':
    main()

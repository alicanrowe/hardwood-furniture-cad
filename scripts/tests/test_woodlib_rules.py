#!/usr/bin/env python3
"""Cathedrals point up on upright parts; ..._L/_R door leaves are bookmatched (client review, 26 Nov 2026)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import woodlib as W


def box(x0, x1, y0=-0.44, y1=0.44, z0=0.0, z1=12.0):
    return np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])


def main():
    bad = 0
    for seed in range(40):          # an upright flat-sawn board: arches always point up, whatever the seed
        lam = W.board(box(-5, 0), grain='z', cut='flat', seed=seed, name='Side')
        if W.apex(lam)[2] < 0.99: bad += 1; print('FAIL apex down, seed', seed)
    # the lint catches a board made without the rule
    lam = W.board(box(-5, 0), grain='z', cut='flat', seed=3, up=None); lam['tilt'][1] = abs(lam['tilt'][1])
    if not any(k == 'WOODAPEX' for k, *_ in W.check_boards({'Side_Left': lam})): bad += 1; print('FAIL WOODAPEX not raised')
    # bookmatch: b's show face is a's mirrored across the joint, even with b 2 mm proud of a
    PA, PB = box(-5, 0), box(0.1, 5.1, -0.36, 0.52)
    la = W.board(PA, grain='z', cut='flat', seed=7, name='Door_Board_L'); lb = W.bookmatch(la, PA, PB, name='Door_Board_R')
    z = np.linspace(0.5, 11.5, 60); x = np.linspace(-4.5, -0.5, 9)
    X, Z = np.meshgrid(x, z); pa = np.stack([X.ravel(), np.full(X.size, 0.44), Z.ravel()], 1)
    pb = pa.copy(); pb[:, 0] = 0.1 - pa[:, 0]; pb[:, 1] = 0.52
    N = np.tile([0, 1.0, 0], (len(pa), 1))
    err = float(np.abs(W.color(pa, N, la) - W.color(pb, N, lb)).max())
    if err > 0.01: bad += 1; print(f'FAIL bookmatch mirror off by {err:.3f}')
    if any(k == 'WOODMATCH' for k, *_ in W.check_boards({'Door_Board_L': la, 'Door_Board_R': lb})): bad += 1; print('FAIL WOODMATCH on a match')
    lc = W.board(PB, grain='z', cut='flat', seed=9, name='Door_Board_R')
    if not any(k == 'WOODMATCH' for k, *_ in W.check_boards({'Door_Board_L': la, 'Door_Board_R': lc})): bad += 1; print('FAIL WOODMATCH not raised')
    print('PASS' if not bad else f'{bad} fails'); sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

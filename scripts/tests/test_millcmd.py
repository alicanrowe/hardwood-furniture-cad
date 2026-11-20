"""millcmd.py must flag a strip too short for two parts and a missing wide strip (Moth, 20 Nov 2026)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from millcmd import plan

rows = [dict(name='Side_L_Rail_Top', quantity=1, length_in=15.40625, width_in=1.75, thickness_in=1.0),
        dict(name='Side_R_Rail_Top', quantity=1, length_in=15.40625, width_in=1.75, thickness_in=1.0),
        dict(name='Front_Rail_Top', quantity=1, length_in=10.21875, width_in=1.75, thickness_in=1.0),
        dict(name='Mullion', quantity=2, length_in=9.25, width_in=1.0, thickness_in=1.0)]
strips = [dict(label='24(C)', length=24, width=1.75), dict(label='18(D)', length=18, width=1.21875)]
out = plan(rows, strips)
print(out)
assert 'Anything thicker than 1, plane to 1' in out
assert 'anything wider than 1 3/4, rip to 1 3/4' in out
assert out.count('NEED WOOD') == 3, 'two top rails and one mullion have no strip'  # 24 holds one 15 13/32 only; 18 holds one 9 1/4 only
assert '18 5/8' in out  # two mullions need 18 5/8
print('ok')

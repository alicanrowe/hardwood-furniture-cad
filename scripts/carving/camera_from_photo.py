"""Solve a photo's camera from four known floor points and write a Blender camera JSON for render.py.
usage: python3 camera_from_photo.py points.json out_cam.json
points.json: {"image_size": [W, H], "lens_mm": 27, "sensor_mm": 36,
              "world_in": [[x, y, z], ... 4+ points, inches], "pixels": [[u, v], ...]}
iPhone main camera: 27 mm equivalent on a 36 mm sensor. Use the corners of the largest known footprint
(a log, a slab, a rug) and check the printed reprojection error is a few pixels."""
import json, sys, numpy as np, cv2
from scipy.spatial.transform import Rotation as Ro
IN = 0.0254
p = json.load(open(sys.argv[1])); W, H = p['image_size']
f = p.get('lens_mm', 27) / p.get('sensor_mm', 36) * W
K = np.array([[f, 0, W/2], [0, f, H/2], [0, 0, 1]])
obj = np.array(p['world_in'], float) * IN; img = np.array(p['pixels'], float)
flag = cv2.SOLVEPNP_IPPE if np.allclose(obj[:, 2], obj[0, 2]) else cv2.SOLVEPNP_ITERATIVE
ok, rv, tv = cv2.solvePnP(obj, img, K, None, flags=flag)
R, _ = cv2.Rodrigues(rv); C = (-R.T @ tv).ravel()
proj, _ = cv2.projectPoints(obj, rv, tv, K, None)
print('camera (in):', (C/IN).round(1), ' reprojection error (px):', np.abs(proj.reshape(-1, 2) - img).max().round(1))
q = Ro.from_matrix(R.T @ np.diag([1, -1, -1])).as_quat()   # OpenCV looks +Z/up -Y; Blender looks -Z/up +Y
json.dump({'loc': C.tolist(), 'quat': [q[3], q[0], q[1], q[2]], 'lens': p.get('lens_mm', 27), 'sensor': p.get('sensor_mm', 36), 'res': [W//2, H//2]}, open(sys.argv[2], 'w'))

"""Laminated and staved wood for Cycles renders: every board in a glue-up gets its own grain.

A stack-laminated, coopered or edge-glued part is many boards, not one board bent into shape. A single procedural
grain stretched over the whole part reads as bent plywood or a carved log. This shader splits the part into its
real boards and gives each one its own log position (pith), ring spacing, tone and pore field, with a faint glue
line between boards. Where a faired surface cuts through the layers at a slant, the rings of each layer show as
long contour bands, exactly as on a real ground stack lamination; real ends show end grain.

Modes (all positions in inches, world Z up; the shader converts from Blender metres):
  'stack'  horizontal layers of thickness `t` from `z0` up, grain along `axis` ('x' or 'y'). Stack-laminated
           planks, seats, sculpted tops.
  'stave'  `n` vertical staves around a centre (cx, cy), their middle at radius `rm`, grain up. Coopered drums, columns, curved backs.
  'panel'  edge-glued boards of width `t` across the part (boards stacked along the axis that is not `axis` and
           not Z), grain along `axis`. Discs, seat blanks, table tops.
  'solid'  one board, grain along `axis` ('x', 'y' or 'z'). Pegs, keys, braces, rails.

Usage inside Blender (Cycles, CPU or OptiX; OSL is switched on for you):
    import sys; sys.path.append('<skill>/scripts/blender'); import laminated_wood as lw
    m = lw.material('plank', 'stack', t=0.875, z0=17.5, axis='x', seed=3, look=lw.WALNUT_TUNG)
    m = lw.material('drum_L', 'stave', n=16, cx=-60, cy=0, rm=9.5, seed=11, look=lw.WALNUT_TUNG)

Check a close-up of one glue line and one oblique cut before final renders: each board must differ a little in
tone and figure (about +-10 % value, never two-tone), and the figure must break at every glue line.
"""
import bpy, os, tempfile

WALNUT_TUNG = dict(dark=(0.016, 0.0065, 0.004), light=(0.058, 0.024, 0.012), tone=0.2, rough=0.42, spec=0.35,
                   rings=2.2, glue=0.04)

OSL = r'''
// laminated_wood.osl (hardwood-furniture-cad). Positions in inches.
float h1(float k, float s) { return cellnoise(point(k * 1.37 + 0.5, s * 3.11 + 0.5, 7.7)); }
shader laminated_wood(
    point Pos = P,
    normal Nrm = N,
    int Mode = 0,           // 0 stack, 1 stave, 2 panel, 3 solid
    int Axis = 0,           // grain axis 0 x, 1 y, 2 z
    float T = 0.875,        // layer / board thickness (in)
    float Z0 = 0.0,         // a layer boundary (in)
    int Nst = 16,           // staves
    float Cx = 0.0, float Cy = 0.0,
    float Rm = 0.0,         // stave mode: radius of the staves' middle (in)
    float Seed = 1.0,
    float Rings = 2.2,      // rings per inch
    float Tone = 0.08,      // board-to-board value spread
    float Glue = 0.025,     // glue line width (in)
    color Dark = color(0.016, 0.0065, 0.004),
    color Light = color(0.058, 0.024, 0.012),
    output color Col = 0,
    output float Height = 0,
    output float Board = 0,
    output float EndG = 0)
{
    point p = Pos * 39.3701;
    vector n = normalize(Nrm);
    float k = 0, gl = 1e6;
    float g = 0, a = 0, b = 0;           // along-grain coordinate and the two cross coordinates
    if (Mode == 0 || Mode == 2) {
        float c = (Mode == 0) ? p[2] : ((Axis == 0) ? p[1] : p[0]);
        float uu = (c - Z0) / T; k = floor(uu); float f = uu - k;
        gl = min(f, 1 - f) * T;
        g = (Axis == 0) ? p[0] : p[1];
        a = (Axis == 0) ? p[1] : p[0];   // across the board's width
        b = c - (k + 0.5) * T - Z0;      // through its thickness, from the board centre
        if (Mode == 2) { float tmp = a; a = p[2]; b = tmp - ((k + 0.5) * T + Z0); }
        EndG = fabs(n[Axis == 0 ? 0 : 1]);
    } else if (Mode == 1) {
        float dx = p[0] - Cx, dy = p[1] - Cy;
        float th = atan2(dy, dx); float s = (th + M_PI) / (2 * M_PI) * Nst;
        k = floor(s); float f = s - k;
        float r = hypot(dx, dy);
        gl = min(f, 1 - f) * (2 * M_PI / Nst) * r;
        float tc = -M_PI + (k + 0.5) * 2 * M_PI / Nst;
        a = -dx * sin(tc) + dy * cos(tc);   // tangential, across the stave
        b = dx * cos(tc) + dy * sin(tc) - Rm;   // radial, through the stave from its middle
        g = p[2];
        EndG = fabs(n[2]);
    } else {
        g = p[Axis]; a = p[(Axis + 1) % 3]; b = p[(Axis + 2) % 3];
        EndG = fabs(n[Axis]);
    }
    Board = k;
    // each board: its own log. Pith 3 to 8 in off the board, sideways anywhere across it, a slight cone so
    // flat faces show cathedrals, its own ring spacing and tone.
    float pa = (h1(k, Seed) - 0.5) * 6.0;
    float pb = (h1(k, Seed + 1) < 0.5 ? -1 : 1) * (3.0 + 5.0 * h1(k, Seed + 2));
    if (Mode == 1) pb = -(5.0 + 4.0 * h1(k, Seed + 2));      // staves are rived/sawn with the bark outward
    float cone = 0.012 + 0.02 * h1(k, Seed + 3);
    float rr = Rings * (0.8 + 0.4 * h1(k, Seed + 4));
    float d = hypot(a - pa, b - pb);
    d += 0.35 * noise("perlin", point(g * 0.06 + k * 13.1, a * 0.25, b * 0.25));
    d += cone * g + 0.03 * noise("perlin", point(g * 0.15, a * 1.5 + k, b * 1.5));
    float ring = d * rr; float fr = ring - floor(ring);
    float late = smoothstep(0.55, 0.95, fr) * (1 - smoothstep(0.95, 1.0, fr));
    float figure = 0.5 + 0.5 * noise("perlin", point(g * 0.02 + k * 5.3, d * 0.8, 0.0));
    float val = clamp(0.08 + 0.62 * (1 - late) * (0.45 + 0.55 * figure), 0, 1);
    color base = mix(Dark, Light, val);
    // board tone: value and a touch of hue (some boards redder, some greyer), never two-tone
    float tv = 1 + Tone * 2 * (h1(k, Seed + 5) - 0.5) * 2;
    float th2 = (h1(k, Seed + 6) - 0.5) * 0.12;
    base = base * tv * color(1 + th2, 1, 1 - th2);
    // pores: long thin streaks along the grain
    float pore = noise("perlin", point(g * 1.2, a * 38.0, b * 38.0));
    float pm = smoothstep(0.12, 0.45, pore);
    base *= mix(0.62, 1.0, pm);
    // end grain: darker, pores open
    base *= mix(1.0, 0.62, smoothstep(0.6, 0.95, EndG));
    // glue line: a fine dark seam
    float gline = 1 - smoothstep(0.0, Glue, gl);
    base *= 1 - 0.55 * gline;
    Col = base;
    Height = 0.6 * pm + 0.2 * (1 - late) - 0.5 * gline;
}
'''

_osl_path = None
def _osl():
    global _osl_path
    if _osl_path is None:
        _osl_path = os.path.join(tempfile.gettempdir(), 'laminated_wood.osl')
        open(_osl_path, 'w').write(OSL)
    return _osl_path

MODES = {'stack': 0, 'stave': 1, 'panel': 2, 'solid': 3}
AXES = {'x': 0, 'y': 1, 'z': 2}

def material(name, mode, t=0.875, z0=0.0, n=16, cx=0.0, cy=0.0, rm=0.0, axis='x', seed=1, look=WALNUT_TUNG):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.shading_system = True
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
    b = N['Principled BSDF']
    sn = N.new('ShaderNodeScript'); sn.mode = 'EXTERNAL'; sn.filepath = _osl(); sn.update()
    geo = N.new('ShaderNodeNewGeometry')
    Lk(geo.outputs['Position'], sn.inputs['Pos']); Lk(geo.outputs['Normal'], sn.inputs['Nrm'])
    vals = dict(Mode=MODES[mode], Axis=AXES[axis], T=t, Z0=z0, Nst=n, Cx=cx, Cy=cy, Rm=rm, Seed=float(seed),
                Rings=look['rings'], Tone=look['tone'], Glue=look['glue'])
    for k_, v_ in vals.items():
        sn.inputs[k_].default_value = v_
    sn.inputs['Dark'].default_value = (*look['dark'], 1)[:len(sn.inputs['Dark'].default_value)]; sn.inputs['Light'].default_value = (*look['light'], 1)[:len(sn.inputs['Light'].default_value)]
    Lk(sn.outputs['Col'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = look['rough']; b.inputs['Specular IOR Level'].default_value = look['spec']
    bm = N.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = 0.05; bm.inputs['Distance'].default_value = 0.0004
    Lk(sn.outputs['Height'], bm.inputs['Height']); Lk(bm.outputs[0], b.inputs['Normal'])
    return m

#!/usr/bin/env python3
"""Fail any wood that doesn't come from the wood library (scripts/woodlib.py, references/woods.json).

  python3 scripts/woodlib_lint.py PATH [PATH ...]      # .py scripts, .glb files, .blend files, or folders of them
  exit 1 on any fail; --json out.json for the list

Why (review, 26 Nov 2026): every pipeline built or copied its own wood shader, so the same walnut came out muddy in one
project, pale pink in the next and grey in a third, and grain ran the wrong way wherever a script laid its own
texture. One library only works if nothing else can make wood. Rules:

  WOODCOLOR   a script hard-codes a wood colour: a species name next to an RGB triple, or a SPECIES-style table
  WOODSHADER  a script builds a wood material itself (materials.new / node tree named for a wood or grain) without
              going through woodlib_bl (material / apply / apply_all / house_glb) or web_laminate --all
  WOODGLB     a GLB wood material (named for a species or grain) without extras "woodlib", or stamped by an
              older library table (re-bake with web_laminate.py --all)
  WOODBLEND   a .blend wood material without the "woodlib" custom property

The library's own files are exempt. A script that only *names* a species (to pass to woodlib) is fine.
"""
import argparse, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import woodlib as W  # noqa: E402

SPECIES_RX = r'walnut|white oak|red oak|\boak\b|\bash\b|maple|cherry|cedar|mahogany|sapele|birch|\bpine\b'
WOODNAME = re.compile(r'(?i)(' + SPECIES_RX + r'|wood|grain|timber|lumber|plank)')
TRIPLE = r'\(\s*0?\.\d+\s*,\s*0?\.\d+\s*,\s*0?\.\d+'
COLOR_LINE = re.compile(r'(?i)(' + SPECIES_RX + r'|wood)[^\n#]{0,40}?' + TRIPLE)
TABLE = re.compile(r'(?i)^\s*(SPECIES|WOODS?|WOOD_COLOU?RS?)\s*=\s*\{')
MATNEW = re.compile(r'materials\.new\(\s*(?:f?["\'])([^"\']*)')
EXEMPT = {'woodlib.py', 'woodlib_bl.py', 'woodlib_fit.py', 'woodlib_calibrate.py', 'woodlib_lint.py'}


def lint_py(path):
    fails = []
    src = open(path, encoding='utf-8', errors='replace').read()
    if os.path.basename(path) in EXEMPT: return fails
    uses_lib = 'woodlib' in src or 'laminated_wood' in src
    for i, line in enumerate(src.splitlines(), 1):
        s = line.split('#', 1)[0]
        if COLOR_LINE.search(s):
            fails.append(('WOODCOLOR', f'{path}:{i}', s.strip()[:120]))
        elif TABLE.search(s) and re.search('(' + SPECIES_RX + r')[^\n]{0,12}' + TRIPLE, src[src.find(line):src.find(line) + 600], re.I):
            fails.append(('WOODCOLOR', f'{path}:{i}', 'species colour table: read references/woods.json via woodlib instead'))
        m = MATNEW.search(s)
        if m and WOODNAME.search(m.group(1)) and not re.search(r'woodlib', s):
            fails.append(('WOODSHADER', f'{path}:{i}', f'builds its own wood material "{m.group(1)}": use woodlib_bl.material/apply'))
    if not uses_lib and re.search(r'ShaderNodeTex(Wave|Noise)', src) and WOODNAME.search(src) and re.search(r'(?i)def [a-z_]*(wood|walnut|grain|ash|oak)', src):
        fails.append(('WOODSHADER', path, 'procedural wood node tree outside the library'))
    return fails


def glb_json(path):
    b = open(path, 'rb').read(); L = struct.unpack('<I', b[12:16])[0]
    return json.loads(b[20:20 + L])


def lint_glb(path, strict_version=False):
    fails = []
    j = glb_json(path)
    for m in j.get('materials', []):
        nm = m.get('name', '') or ''
        st = (m.get('extras') or {}).get('woodlib')
        if not WOODNAME.search(nm) and not st: continue
        if re.search(r'(?i)steel|brass|bronze|alu|metal|leather|felt|glass|acrylic', nm) and not st: continue
        if not st:
            fails.append(('WOODGLB', f'{path} [{nm}]', 'wood material not from the wood library: re-bake with web_laminate.py --all'))
            continue
        p = W.parse_stamp(st)
        if p is None:
            fails.append(('WOODGLB', f'{path} [{nm}]', f'bad woodlib stamp {st!r}')); continue
        lib_table = W.VERSION.split('+')[0]
        if p[3].split('+')[0] != lib_table or (strict_version and p[3] != W.VERSION):
            fails.append(('WOODGLB', f'{path} [{nm}]', f'stamped by library {p[3]}, current is {W.VERSION}: re-bake'))
    return fails


def lint_blend(path):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=path)
    return [('WOODBLEND', f'{path} [{m.name}]', 'wood material without the woodlib property: use woodlib_bl.apply')
            for m in bpy.data.materials if WOODNAME.search(m.name) and not m.get('woodlib') and m.users]


def walk(paths):
    for p in paths:
        if os.path.isdir(p):
            for dp, dn, fs in os.walk(p):
                dn[:] = [d for d in dn if d not in ('__pycache__', '.git', 'node_modules')]
                for f in sorted(fs):
                    if f.endswith(('.py', '.glb', '.blend')): yield os.path.join(dp, f)
        else:
            yield p


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('paths', nargs='+'); ap.add_argument('--json')
    ap.add_argument('--strict-version', action='store_true', help='also fail GLBs baked with an older wood model hash')
    ap.add_argument('--no-blend', action='store_true')
    a = ap.parse_args()
    fails = []
    for f in walk(a.paths):
        try:
            if f.endswith('.py'): fails += lint_py(f)
            elif f.endswith('.glb'): fails += lint_glb(f, a.strict_version)
            elif f.endswith('.blend') and not a.no_blend: fails += lint_blend(f)
        except Exception as e:
            fails.append(('WOODLINT', f, f'could not read: {e}'))
    for k, where, why in fails: print(f'FAIL {k} {where}: {why}')
    print(f'woodlib {W.VERSION}: {len(fails)} fails')
    if a.json: json.dump([dict(kind=k, where=w, why=y) for k, w, y in fails], open(a.json, 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()

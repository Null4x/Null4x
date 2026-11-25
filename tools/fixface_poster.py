"""Fix Face 4:5 product posters — front-facing product sets on unique luxury sets.

Palette is fixed for every poster: ~70% light beige / champagne gold, ~30%
black marble accents. Each poster gets its own texture family + variant so no
two backgrounds repeat. Products are front-facing cut-outs (see parts/),
composed as sets (box + vials) with contact shadows and, on polished black
marble, a soft mirror reflection.

Usage: python3 tools/fixface_poster.py <parts_dir> <out_dir> [product ids...]
"""
import sys, os
import numpy as np
from PIL import Image

W, H = 1600, 2000
OUT = (1600, 2000)

# ---------------------------------------------------------------- palette
def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)

CREAM, SAND, CAMEL, GOLD, GOLD_HI = (hexc(c) for c in ('#f3e9d8', '#e6d4b6', '#c9ab7f', '#c49a55', '#ecd197'))
INK, INK2 = hexc('#141110'), hexc('#2a2420')

# ---------------------------------------------------------------- helpers
def fbm(h, w, seed, octaves=5, base=2, pers=0.5):
    rng = np.random.default_rng(seed)
    tot = np.zeros((h, w), np.float32); amp = 1.0; norm = 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n + 1, int((n + 1) * w / h) + 2)).astype(np.float32)
        tot += np.asarray(Image.fromarray(g, 'F').resize((w, h), Image.BICUBIC), np.float32) * amp
        norm += amp; amp *= pers
    return tot / norm

def _box(a, r, axis):
    r = max(1, int(r))
    pad = [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)]
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis, dtype=np.float64)
    n = c.shape[axis]
    return ((np.take(c, np.arange(2 * r + 1, n), axis=axis) - np.take(c, np.arange(0, n - 2 * r - 1), axis=axis)) / (2 * r + 1)).astype(np.float32)

def blur(a, r):
    if r < 0.6: return a.astype(np.float32)
    a = a.astype(np.float32); br = max(1.0, r * 0.93)
    for ax in (0, 1):
        for _ in range(3): a = _box(a, br, ax)
    return a

def grid(h=H, w=W):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx / w, yy / h

def mixc(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2: t = t[..., None]
    return a * (1 - t) + b * t

def veins(h, w, seed, angle, freq, sharp=70, warp=0.55):
    nx, ny = grid(h, w); s = max(h, w)
    nx, ny = nx * w / s, ny * h / s
    t = (nx * np.cos(angle) + ny * np.sin(angle)) * freq + warp * fbm(h, w, seed, 5, 1)
    v = (1 - np.abs(np.sin(t * np.pi))) ** sharp
    t2 = (nx * np.cos(angle + .55) + ny * np.sin(angle + .55)) * freq * 1.8 + warp * 1.2 * fbm(h, w, seed + 1, 5, 2)
    v2 = (1 - np.abs(np.sin(t2 * np.pi))) ** (sharp * 1.6)
    return np.clip(blur(v + v2 * .55, 1.0), 0, 1)

def black_marble(h, w, seed, angle=0.9, freq=2.2):
    cloud = fbm(h, w, seed + 7, 5, 2)
    base = mixc(INK, INK2, np.clip((cloud - .35) * 2.2, 0, 1))
    v = veins(h, w, seed, angle, freq, 55)
    halo = blur(v, 10) * .5
    col = mixc(base, GOLD * .55, halo * .35)
    col = mixc(col, GOLD_HI * .92, v * .85)
    return col

def cream_marble(h, w, seed, angle=1.1, freq=1.8, vein_col=None, op=.45):
    cloud = fbm(h, w, seed + 3, 5, 2)
    base = mixc(CREAM, SAND, np.clip((cloud - .3) * 1.6, 0, 1))
    v = veins(h, w, seed, angle, freq, 80)
    vc = GOLD if vein_col is None else vein_col
    col = mixc(base, CAMEL, blur(v, 12) * .25)
    return mixc(col, vc, v * op)

def plaster(h, w, seed, a=CREAM, b=SAND, grain=1.0):
    n = fbm(h, w, seed, 6, 3, .55)
    return mixc(a, b, np.clip((n - .3) * 1.5 * grain, 0, 1))

# ---------------------------------------------------------------- wall families
def wall_fluted(seed, v):
    nx, ny = grid(); n = [26, 18, 34][v]
    ph = (nx * n) % 1.0
    shade = 0.80 + 0.28 * np.sin(ph * np.pi) ** .7
    col = plaster(H, W, seed) * shade[..., None]
    if v == 1:  # gold pin line every 6th flute
        k = ((nx * n) // 1) % 6 == 0
        col = mixc(col, GOLD, (k & (np.abs(ph - .5) < .06)) * .7)
    return col

def wall_travertine(seed, v):
    nx, ny = grid()
    warp = fbm(H, W, seed, 4, 1) * .25
    bands = (ny + warp) * [9, 13, 6][v]
    st = (np.sin(bands * np.pi * 2) * .5 + .5) ** 2
    fine = fbm(H, W, seed + 2, 6, 8, .6)
    streak = blur(np.clip((fbm(H, W, seed + 9, 4, 16, .7) - .62) * 6, 0, 1), 1.0)
    streak = np.asarray(Image.fromarray((streak * 255).astype(np.uint8)).resize((W // 6, H)).resize((W, H), Image.BICUBIC), np.float32) / 255
    col = mixc(CREAM, SAND, np.clip(st * .65 + (fine - .5) * .6, 0, 1))
    return mixc(col, CAMEL, streak * .45)

def wall_calacatta(seed, v):
    return cream_marble(H, W, seed, angle=[1.0, 0.35, 2.2][v], freq=[1.6, 2.1, 1.3][v],
                        vein_col=[GOLD, INK2, GOLD][v], op=[.55, .35, .6][v])

def wall_silk(seed, v):
    nx, ny = grid()
    w1 = np.sin((nx * [5, 7, 4][v] + 0.9 * fbm(H, W, seed, 3, 1)) * np.pi * 2 + ny * 2.2)
    w2 = np.sin((nx * 2.3 - ny * 1.1 + .6 * fbm(H, W, seed + 4, 3, 1)) * np.pi * 2)
    f = blur(w1 * .65 + w2 * .35, 6)
    sheen = np.clip(f, 0, 1) ** 3
    col = mixc(SAND, CREAM, (f * .5 + .5))
    return mixc(col, GOLD_HI, sheen * .35) * (0.86 + 0.14 * (f[..., None] * .5 + .5))

def wall_deco(seed, v):
    nx, ny = grid(); cx, cy = 0.5, [0.62, 0.70, 0.58][v]
    ang = np.arctan2(ny - cy, (nx - cx) * W / H); r = np.hypot((nx - cx) * W / H, ny - cy)
    rays = np.abs(((ang + np.pi) / (np.pi / [14, 20, 10][v])) % 1 - .5) < .012
    rings = np.abs((r * [9, 12, 7][v]) % 1 - .5) < .010
    col = plaster(H, W, seed)
    m = blur((rays | rings).astype(np.float32), .8) * (ny < cy)
    return mixc(col, GOLD, m * .8)

def wall_stone(seed, v):
    nx, ny = grid(); rows = [9, 7, 11][v]
    ry = ny * rows; row = ry // 1
    off = (row % 2) * .5
    cols = [3, 4, 2][v]
    rx = nx * cols + off
    jy = np.abs(ry % 1 - .5) > .47; jx = np.abs(rx % 1 - .5) > .485
    tone = fbm(H, W, seed, 5, 3)
    blk = np.asarray(Image.fromarray((np.random.default_rng(seed).random((rows + 1, cols + 2)) * 255).astype(np.uint8)).resize((W, H), Image.NEAREST), np.float32) / 255
    col = mixc(CREAM, SAND, np.clip(tone * .8 + blk * .5 - .3, 0, 1))
    return mixc(col, CAMEL * .8, blur((jy | jx).astype(np.float32), 1.5) * .85)

def wall_ripple(seed, v):
    nx, ny = grid(); cx, cy = [0.5, 0.25, 0.75][v], [0.55, 0.4, 0.45][v]
    r = np.hypot((nx - cx) * W / H, ny - cy) + .03 * fbm(H, W, seed, 3, 1)
    f = np.sin(r * [38, 30, 46][v] * np.pi)
    col = plaster(H, W, seed)
    return col * (0.92 + 0.08 * f[..., None]) + GOLD_HI * (np.clip(f, 0, 1) ** 8)[..., None] * .12

def wall_beams(seed, v):
    col = plaster(H, W, seed, CREAM, SAND, 1.2)
    nx, ny = grid()
    u = nx * .75 + ny * [.66, -.66, .5][v]
    beams = sum(np.exp(-((u - c) / .045) ** 2) for c in ([.55, .78, .98] if v != 1 else [.15, .35, .52]))
    return col * (0.84 + 0.30 * blur(beams, 8)[..., None])

def wall_terrazzo(seed, v):
    from PIL import ImageDraw
    rng = np.random.default_rng(seed)
    base = plaster(H, W, seed)
    m1 = Image.new('L', (W, H), 0); m2 = Image.new('L', (W, H), 0)
    d1, d2 = ImageDraw.Draw(m1), ImageDraw.Draw(m2)
    for _ in range([520, 800, 340][v]):
        x, y = rng.uniform(0, W), rng.uniform(0, H); r = rng.uniform(3, [16, 11, 22][v])
        pts = [(x + r * rng.uniform(.6, 1.2) * np.cos(t), y + r * rng.uniform(.6, 1.2) * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 7)[:-1] + rng.uniform(0, 1)]
        (d2 if rng.random() < .22 else d1).polygon(pts, fill=255)
    c1 = blur(np.asarray(m1, np.float32) / 255, 1.1); c2 = blur(np.asarray(m2, np.float32) / 255, 1.1)
    chip = mixc(INK2, INK, fbm(H, W, seed + 5, 3, 6))
    return mixc(mixc(base, chip, c1 * .9), GOLD, c2 * .85)

def wall_arch(seed, v):
    col = plaster(H, W, seed)
    nx, ny = grid(); r = [.30, .36, .26][v]; top = [.10, .14, .08][v]
    cy = top + r * W / H
    inside = ((np.abs(nx - .5) * W / H <= r) & (ny >= cy)) | (np.hypot((nx - .5) * W / H, ny - cy) <= r)
    m = blur(inside.astype(np.float32), 2)
    niche = black_marble(H, W, seed + 11, .8, 1.6) if v != 1 else cream_marble(H, W, seed + 11, 1.3, 1.5, GOLD, .6)
    col = mixc(col, niche, m)
    edge = np.abs(blur(inside.astype(np.float32), 1.2) - .5) < .35
    return mixc(col, GOLD_HI, edge * .9)

FAMILIES = [wall_fluted, wall_travertine, wall_calacatta, wall_silk, wall_deco,
            wall_stone, wall_ripple, wall_beams, wall_terrazzo, wall_arch]

# ---------------------------------------------------------------- pedestals
def pedestal(kind, top, x0, x1, seed, dark=True):
    """Return (rgb, mask, gloss mask, top-surface y0, y1)."""
    nx, ny = grid(); xx, yy = nx * W, ny * H
    mat = black_marble(H, W, seed, 1.2, 2.4) if dark else cream_marble(H, W, seed, .4, 2.6, INK2, .4)
    surf_tex = black_marble(H, W, seed + 3, .15, 3.4) if dark else cream_marble(H, W, seed + 3, .12, 3.2, GOLD, .5)
    T = top * H; depth = 0.055 * H; E = T + depth
    if kind == 'cylinder':
        r = (x1 - x0) * W / 2; cx = (x0 + x1) * W / 2; ry = depth * .55
        cyc = T + ry
        body = (np.abs(xx - cx) <= r) & (yy >= cyc)
        cap = ((xx - cx) / r) ** 2 + ((yy - cyc) / ry) ** 2 <= 1
        sx = np.clip((xx - cx) / r, -1, 1)
        shade = 0.50 + 0.62 * np.sqrt(np.clip(1 - sx ** 2, 0, 1)) - 0.10 * sx
        col = mat * shade[..., None]
        col[cap] = surf_tex[cap] * 1.18 + 10
        rim = (np.abs(((xx - cx) / r) ** 2 + ((yy - cyc) / ry) ** 2 - 1) < .035) & (yy >= cyc)
        col[rim] = GOLD_HI
        m = (body | cap).astype(np.float32)
        return col, blur(m, .8), cap.astype(np.float32), T + ry * .35, T + ry * 1.65
    if kind == 'slab':
        X0, X1 = 0, W
    else:
        X0, X1 = x0 * W, x1 * W
    inx = (xx >= X0) & (xx <= X1)
    m = inx & (yy >= T)
    col = np.zeros((H, W, 3), np.float32)
    # top surface: compressed polished texture, brighter toward front
    st = (yy >= T) & (yy < E) & inx
    tt = np.clip((yy - T) / depth, 0, 1)
    col = np.where(st[..., None], surf_tex * (1.05 + .25 * tt)[..., None] + 6, col)
    # front face
    ff = (yy >= E) & inx
    sx = np.clip((xx - X0) / max(1, X1 - X0), 0, 1)
    fshade = (0.70 + 0.30 * np.sin(sx * np.pi) ** .5) * np.clip(1 - (yy - E) / (H - E) * .3, .6, 1)
    col = np.where(ff[..., None], mat * fshade[..., None], col)
    edge = (np.abs(yy - E) < 2.2) & inx
    col[edge] = GOLD_HI
    if kind == 'steps':  # lower wider step in front
        S = E + 0.10 * H; a0, a1 = X0 - .10 * W, X1 + .10 * W
        lw = (xx >= a0) & (xx <= a1) & (yy >= S) & ~inx | ((xx >= a0) & (xx <= a1) & (yy >= S + depth * .6))
        st2 = (xx >= a0) & (xx <= a1) & (yy >= S) & (yy < S + depth * .6)
        alt = cream_marble(H, W, seed + 21, .3, 2.4, INK2, .45) if dark else black_marble(H, W, seed + 21, .3, 2.4)
        col = np.where(st2[..., None], alt * 1.08 + 4, col)
        col = np.where((lw & ~st2)[..., None], alt * .86, col)
        col[(np.abs(yy - (S + depth * .6)) < 2) & (xx >= a0) & (xx <= a1)] = GOLD_HI
        m = m | st2 | lw
    return col, blur(m.astype(np.float32), .8), st.astype(np.float32), T + depth * .22, T + depth * .78

# ---------------------------------------------------------------- scenes (30 unique)
# (family index, variant, pedestal kind, pedestal dark?, mirror)
SCENES = {
    'fix-face-ultra':        (2, 0, 'slab', True, False),
    'fix-face-ultra-plus':   (0, 0, 'block', True, False),
    'fix-face-grand':        (9, 0, 'block', False, False),
    'plla':                  (3, 0, 'slab', True, False),
    'fix-face-cpdrn':        (1, 0, 'steps', True, False),
    'fix-face-ha-18':        (7, 0, 'slab', True, False),
    'fix-face-collagen':     (4, 0, 'block', True, False),
    'fix-face-skin-booster': (6, 0, 'slab', True, True),
    'fix-face-pdo':          (5, 0, 'cylinder', True, False),
    'agasthi-h':             (8, 0, 'block', True, False),
    'agasthi-body':          (9, 1, 'cylinder', True, False),
    'agasthi-fine':          (2, 1, 'steps', True, True),
    'agasthi-deep':          (0, 1, 'slab', True, False),
    'agasthi-sub-q':         (3, 1, 'block', True, True),
    'agasthi-s':             (7, 1, 'cylinder', True, False),
    'audrey-h':              (1, 1, 'slab', True, False),
    'audrey-m':              (4, 1, 'steps', True, False),
    'audrey-m-2ml':          (6, 1, 'block', True, False),
    'qf-fi-ne':              (5, 1, 'cylinder', True, False),
    'qf-deep':               (9, 2, 'cylinder', False, False),
    'qf-sub-q':              (8, 1, 'cylinder', True, True),
    'lipo-360':              (2, 2, 'block', True, False),
    'yeellow-drop':          (0, 2, 'steps', True, False),
    'cellix-pn':             (7, 2, 'cylinder', True, True),
    'liporase':              (3, 2, 'slab', True, False),
    'hyalmas':               (1, 2, 'block', True, True),
    'exoroot':               (5, 2, 'slab', True, False),
    'exo-nad':               (4, 2, 'slab', True, True),
    'lxc':                   (6, 2, 'steps', True, False),
    'hyaron':                (8, 2, 'slab', True, False),
}

# ---------------------------------------------------------------- product sets
# each part: (file, height relative to main item, x centre in main-heights, depth: 0 back .. 2 front)
SETS = {
    'plla': [('plla-box', 1.0, 0.0, 0), ('plla-vial-a', .78, 1.02, 1), ('plla-vial-b', .78, 1.55, 1)],
    'fix-face-cpdrn': [('fix-face-cpdrn-box', 1.0, 0.0, 0), ('fix-face-cpdrn-vial', 1.18, 1.05, 1)],
    'fix-face-ha-18': [('fix-face-ha-18-box', 1.0, 0.0, 0), ('fix-face-ha-18-vial', 1.18, 1.05, 1)],
    'fix-face-collagen': [('fix-face-collagen-box', 1.0, 0.0, 0), ('fix-face-collagen-vial', 1.15, 1.05, 1)],
    'fix-face-skin-booster': [('fix-face-skin-booster-box', 1.0, 0.0, 0), ('fix-face-skin-booster-vial', 1.18, 1.05, 1)],
    'lipo-360': [('lipo-360-box', 1.0, 0.0, 0), ('lipo-360-vial', .78, .62, 1)],
    'liporase': [('liporase-box', 1.0, 0.0, 0), ('liporase-vial', .95, 1.02, 1)],
    'exoroot': [('exoroot-box', 1.0, 0.0, 0), ('exoroot-vial-a', .62, .25, 1), ('exoroot-vial-b', .58, .62, 1)],
    'exo-nad': [('exo-nad-bigbox', 1.0, 0.0, 0), ('exo-nad-box', .56, -.98, 1), ('exo-nad-vial-a', .60, .78, 2), ('exo-nad-vial-b', .60, 1.12, 2)],
    'lxc': [('lxc-bigbox', 1.0, 0.0, 0), ('lxc-smallbox', .56, -1.02, 1), ('lxc-vial-a', .64, .66, 2), ('lxc-vial-b', .64, .98, 2)],
    'yeellow-drop': [('yeellow-drop-box', 1.0, 0.0, 0), ('yeellow-drop-vial', 1.32, .85, 1)],
}

def parts_for(pid):
    return SETS.get(pid, [(pid + '-box' if pid != 'yeellow-drop' else 'yeellow-drop-vial', 1.0, 0.0, 0)])

# ---------------------------------------------------------------- compositing
def load(pdir, name):
    im = Image.open(os.path.join(pdir, name + '.png')).convert('RGBA')
    return im

def layout(pid, pdir):
    items = []
    for f, hr, xc, depth in parts_for(pid):
        im = load(pdir, f)
        if 'box' in f and f not in ('fix-face-pdo-box', 'hyalmas-box', 'hyaron-box', 'liporase-box', 'exo-nad-box', 'lxc-smallbox', 'lxc-bigbox', 'yeellow-drop-box', 'audrey-h-box', 'audrey-m-box', 'audrey-m-2ml-box', 'plla-box', 'agasthi-body-box', 'cellix-pn-box'):
            im = box_shading(im)
        items.append([im, hr, xc, depth])
    # extents in "main heights"
    xs = []
    for im, hr, xc, d in items:
        w = im.width / im.height * hr; xs += [xc - w / 2, xc + w / 2]
    gx0, gx1 = min(xs), max(xs); gw = gx1 - gx0
    gh = max(hr for _, hr, _, _ in items)
    s = min((0.74 if len(items) > 1 else 0.64) * W / gw, 0.40 * H / gh, (0.22 * W * H * .5 / (gw * gh * .55)) ** .5)
    cx = (gx0 + gx1) / 2
    out = []
    for im, hr, xc, d in sorted(items, key=lambda t: t[3]):
        ph = hr * s; pw = im.width / im.height * ph
        im2 = im.resize((max(1, int(round(pw))), max(1, int(round(ph)))), Image.LANCZOS)
        out.append((im2, W / 2 + (xc - cx) * s, d))
    return out, gw * s

def box_shading(im):
    """Give a flat rectified box front a sense of volume."""
    a = np.asarray(im, np.float32).copy(); h, w = a.shape[:2]
    x = np.linspace(0, 1, w, dtype=np.float32); y = np.linspace(0, 1, h, dtype=np.float32)
    side = 1 - 0.16 * (np.exp(-x / .02) + np.exp(-(1 - x) / .03))
    vert = 1.05 - 0.14 * y
    a[..., :3] *= (side[None, :] * vert[:, None])[..., None]
    top = np.exp(-y / .012)[:, None] * 0.22
    a[..., :3] += top[..., None] * 255 * .35
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')

def render(pid, pdir, out):
    fam, var, pkind, pdark, mirror = SCENES[pid]
    seed = abs(hash(pid)) % 100000
    wall = FAMILIES[fam](seed, var)
    nx, ny = grid()
    # light: soft key upper-left, warm
    key = np.exp(-(((nx - .35) / .55) ** 2 + ((ny - .25) / .55) ** 2))
    wall = wall * (0.82 + 0.30 * key)[..., None]
    items, gw = layout(pid, pdir)
    top = {'slab': .715, 'block': .69, 'steps': .66, 'cylinder': .69}[pkind]
    half = max(.26, gw / W / 2 + .07)
    pcol, pm, gloss, ty0, ty1 = pedestal(pkind, top, .5 - half, .5 + half, seed + 5, pdark)
    img = mixc(wall, pcol, pm)
    # pedestal casts soft shadow on wall
    sh = blur(pm, 40) * (1 - pm)
    img *= (1 - .35 * sh)[..., None]
    if mirror:
        img = img[:, ::-1].copy(); gloss = gloss[:, ::-1]; pm = pm[:, ::-1]
    # composite each item
    for im, cx, depth in items:
        pw, ph = im.size
        by = ty0 + (ty1 - ty0) * [0.0, 0.55, 1.0][depth]
        x0 = int(round(cx - pw / 2)); y0 = int(round(by - ph))
        a = np.asarray(im, np.float32); A = a[..., 3] / 255
        solid = A > .5
        colsx = np.where(solid.any(0))[0]
        bottom = np.full(pw, -1); bottom[colsx] = ph - 1 - np.argmax(solid[::-1, colsx], axis=0)
        # contact + soft shadows
        occ = np.zeros((H, W), np.float32)
        for x in colsx[::2]:
            X = x0 + x; Y = y0 + bottom[x]
            if 0 <= X < W and 0 <= Y < H: occ[max(0, Y - 2):Y + 3, X] = 1
        k = (np.clip(blur(occ, 3) * 3, 0, 1) * .7 + np.clip(blur(occ, 14) * 5, 0, 1) * .45
             + np.clip(blur(occ, 46) * 9, 0, 1) * .22)
        k = np.clip(k, 0, .9)[..., None]
        img = img * (1 - k) + np.array([10, 8, 6], np.float32) * k
        # reflection on glossy surface
        if pdark:
            depth_px = int(ph * .42)
            d = np.arange(depth_px)[:, None]
            sy = bottom[None, :] - d
            valid = (bottom[None, :] >= 0) & (sy >= 0)
            refl = a[np.clip(sy, 0, ph - 1), np.broadcast_to(np.arange(pw)[None, :], sy.shape)].copy()
            refl[..., 3] *= (np.linspace(.30, 0, depth_px, dtype=np.float32) ** 1.3)[:, None] * valid
            Y = y0 + bottom[None, :] + 1 + d; X = x0 + np.broadcast_to(np.arange(pw)[None, :], sy.shape)
            ok = valid & (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
            layer = np.zeros((H, W, 4), np.float32); layer[Y[ok], X[ok]] = refl[ok]
            la = blur(layer[..., 3], 2) / 255 * gloss
            lc = np.stack([blur(layer[..., i] * layer[..., 3] / 255, 2) for i in range(3)], -1) / np.maximum(la / np.maximum(gloss, 1e-3), 1e-4)[..., None]
            img = img * (1 - la[..., None]) + np.clip(lc, 0, 255) * la[..., None]
        # paste product
        xs0, ys0 = max(0, x0), max(0, y0); xs1, ys1 = min(W, x0 + pw), min(H, y0 + ph)
        sub = a[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
        sa = sub[..., 3:4] / 255
        rgb = sub[..., :3] * np.array([1.015, 1.0, .975], np.float32)
        img[ys0:ys1, xs0:xs1] = img[ys0:ys1, xs0:xs1] * (1 - sa) + rgb * sa
    # global grade: vignette + grain
    v = ((nx - .5) / .8) ** 2 + ((ny - .5) / .85) ** 2
    img *= (1 - .26 * np.clip(v, 0, 1.4) ** 1.5)[..., None]
    img += np.random.default_rng(seed).normal(0, 2.0, (H, W, 1)).astype(np.float32)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out, 'WEBP', quality=88, method=6)

if __name__ == '__main__':
    pdir, odir = sys.argv[1], sys.argv[2]
    ids = sys.argv[3:] or list(SCENES)
    os.makedirs(odir, exist_ok=True)
    for pid in ids:
        render(pid, pdir, os.path.join(odir, pid + '.webp')); print('ok', pid, flush=True)

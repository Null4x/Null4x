"""Fix Face avant-garde 4:5 product posters.

Each product cutout is placed on a procedurally built luxury set:
veined marble wall with sweeping gold-edged marble ribbons, a raking
golden light beam with window-blind shadows, and a glossy marble slab
with a gold trim, real contact shadow and mirror reflection. Marble
tone is matched to the packaging; the set mirrors on alternate products.

Usage: python3 tools/fixface_poster.py <parts_dir> <out_dir> [ids...]
"""
import sys, os, glob
import numpy as np
from PIL import Image

W, H = 2000, 2500
SLAB_TOP, SLAB_EDGE = 0.705, 0.865    # slab surface starts / gold front edge
BASE = 0.815                          # product contact line on the slab


def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


# marble sets: (light, dark, vein, ribbon tint, beam tint)
SETS = {
    'champagne': ('#e6cba3', '#b48a5c', '#7a5130', '#f1dcb9', '#ffe2ad'),
    'onyx':      ('#efd6a8', '#c39a62', '#8c6232', '#f6e3bf', '#ffdc9c'),
    'rose':      ('#ecc9c0', '#b98579', '#7e4c46', '#f4dcd4', '#ffd9c6'),
    'amber':     ('#e9c393', '#b07a45', '#6e4421', '#f3d6ae', '#ffd39a'),
    'steel':     ('#c9ced3', '#8a9097', '#4f565e', '#dde1e4', '#fde7c4'),
    'greige':    ('#d9d0c4', '#a39684', '#6a5d4e', '#e8e1d6', '#ffe6c0'),
    'nero':      ('#3a312a', '#14110e', '#c9a063', '#4a3f35', '#ffcf8a'),
    'midnight':  ('#33405e', '#121a2e', '#c6a466', '#43517a', '#ffd9a0'),
    'graphite':  ('#45474b', '#18191b', '#b9bcc0', '#55585d', '#ffe2b8'),
    'lilac':     ('#ddd3ee', '#a596c8', '#6b5c93', '#ebe5f6', '#ffe6cf'),
    'orchid':    ('#ecd0e2', '#bd88aa', '#7d4a6c', '#f5e2ee', '#ffdccd'),
    'azul':      ('#cfdaf0', '#8aa0cf', '#4b5f93', '#e1e8f6', '#ffe7c8'),
    'blush':     ('#efd8cf', '#c49a8c', '#84594d', '#f6e7e1', '#ffdcc4'),
    'mocha':     ('#d8c3b2', '#977a64', '#5a4334', '#e6d7ca', '#ffdcb2'),
    'calacatta': ('#f4efe7', '#d8cfc2', '#a08455', '#fbf8f2', '#ffe9c2'),
    'travertine':('#efc9a4', '#c4875a', '#83502e', '#f6dcc2', '#ffd2a0'),
    'honey':     ('#f2dc9c', '#c9a24c', '#8a6a22', '#f8e9bf', '#ffe08a'),
    'carrara':   ('#e6e8ea', '#b9bdc2', '#7f858c', '#f1f2f4', '#fff0d8'),
    'sage':      ('#d9dfc4', '#a3ad83', '#66704a', '#e7ebd8', '#fff0c8'),
    'cobalt':    ('#cbd8f2', '#7f98d2', '#3f5596', '#dfe7f7', '#ffe4c0'),
    'plum':      ('#e6ccd9', '#b0809a', '#6f4560', '#f1e0e9', '#ffdccd'),
}

PRODUCT_SET = {
    'fix-face-ultra': 'onyx', 'fix-face-ultra-plus': 'champagne', 'fix-face-grand': 'nero',
    'plla': 'onyx', 'fix-face-collagen': 'rose', 'fix-face-cpdrn': 'amber',
    'fix-face-ha-18': 'steel', 'fix-face-skin-booster': 'champagne', 'fix-face-pdo': 'greige',
    'qf-sub-q': 'nero', 'qf-deep': 'midnight', 'qf-fi-ne': 'calacatta', 'exoroot': 'graphite',
    'agasthi-h': 'lilac', 'agasthi-s': 'orchid', 'agasthi-fine': 'azul', 'agasthi-deep': 'cobalt',
    'agasthi-sub-q': 'azul', 'agasthi-body': 'blush', 'audrey-h': 'mocha', 'audrey-m': 'cobalt',
    'audrey-m-2ml': 'azul', 'lipo-360': 'travertine', 'yeellow-drop': 'honey',
    'cellix-pn': 'carrara', 'liporase': 'lilac', 'hyalmas': 'sage', 'exo-nad': 'onyx',
    'lxc': 'cobalt', 'hyaron': 'plum',
}
DARK_SETS = {'nero', 'midnight', 'graphite'}


# ---------- noise / blur helpers ----------
def fbm(h, w, rng, octaves=6, base=3, persistence=0.55):
    total = np.zeros((h, w), np.float32); amp = 1.0; norm = 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n + 1, int((n + 1) * w / h) + 1)).astype(np.float32)
        up = np.asarray(Image.fromarray(g, 'F').resize((w, h), Image.BICUBIC), np.float32)
        total += up * amp; norm += amp; amp *= persistence
    return total / norm


def _box(a, r, axis):
    r = max(1, int(r))
    c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode='edge'), axis=axis)
    hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
    lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
    return (hi - lo) / (2 * r + 1)


def blur(arr, r):
    a = arr.astype(np.float64); br = max(1.0, float(r) * 0.93)
    for axis in (0, 1):
        for _ in range(3):
            a = _box(a, br, axis)
    return a.astype(np.float32)


def marble(h, w, light, dark, vein, rng, angle=0.6, freq=3.2, turb=4.5, vein_op=0.55):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = xx / max(w, h), yy / max(w, h)
    cloud = fbm(h, w, rng, 5, 2, 0.5)
    warp = fbm(h, w, rng, 5, 1, 0.5)
    t = (nx * np.cos(angle) + ny * np.sin(angle)) * freq + turb * 0.55 * warp
    v1 = (1 - np.abs(np.sin(t * np.pi))) ** 60
    warp2 = fbm(h, w, rng, 5, 2, 0.5)
    t2 = (nx * np.cos(angle + 0.5) + ny * np.sin(angle + 0.5)) * freq * 1.7 + turb * 0.7 * warp2
    v2 = (1 - np.abs(np.sin(t2 * np.pi))) ** 90
    veins = blur(np.clip(v1 + v2 * 0.6, 0, 1), 1.3)
    haze = blur(v1, 18) * 0.5                      # soft cloud around each vein
    m = np.clip((cloud - 0.30) / 0.42, 0, 1) ** 1.2
    col = light * (1 - m[..., None] * 0.75) + dark * (m[..., None] * 0.75)
    col = col * (1 - haze[..., None] * 0.25) + dark * haze[..., None] * 0.25
    vo = (veins * vein_op)[..., None]
    return col * (1 - vo) + vein * vo


# ---------- set construction ----------
def build_set(name, rng):
    light, dark, vein, rib, beam = (hexc(c) for c in SETS[name])
    dark_set = name in DARK_SETS
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = xx / W, yy / H

    img = marble(H, W, light, dark, vein, rng, angle=1.1, freq=2.2)
    img *= (0.80 + 0.20 * (1 - ny))[..., None]          # wall darkens downward

    # sweeping ribbons, rising to the right, stacked back to front
    edges = []
    for k, (y0, slope, curve) in enumerate([(0.40, 0.42, 0.30), (0.53, 0.40, 0.26), (0.66, 0.36, 0.22)]):
        top = (y0 - slope * nx + curve * (nx - 0.25) ** 2) * H
        mask = (yy >= top).astype(np.float32)
        mask = np.clip(blur(mask, 1.2), 0, 1)
        tex = marble(H, W, rib * (0.98 - 0.05 * k), light * (0.86 - 0.04 * k), vein, rng,
                     angle=-0.35, freq=2.8, turb=3.6)
        depth = np.clip((yy - top) / (0.22 * H), 0, 1)
        tex *= (1.06 - 0.30 * depth)[..., None]             # light falls off away from the lip
        img = img * (1 - mask[..., None]) + tex * mask[..., None]
        # occlusion just above the lip on the layer behind
        occ = np.exp(-np.clip(top - yy, 0, None) / 26) * (yy < top)
        img *= (1 - 0.22 * occ)[..., None]
        edges.append(top)

    # brushed gold lips along each ribbon edge
    gold = hexc('#d8b06a')
    for top in edges:
        d = yy - top
        lip = np.exp(-(d / 2.6) ** 2) + 0.35 * np.exp(-((d - 7) / 5) ** 2) * (d > 0)
        sheen = 0.55 + 0.45 * np.sin(nx * 7.0 + 1.3) ** 2
        g = (lip * sheen)[..., None]
        img = img * (1 - np.clip(g, 0, 1) * 0.9) + gold * np.clip(g, 0, 1) * 0.9 + g * 40

    # raking light beam with window-blind shadows
    u = nx * 0.78 - ny * 0.62
    beamm = np.exp(-((u - 0.10) / 0.20) ** 2)
    blinds = 0.78 + 0.22 * (np.sin((nx * 0.62 + ny * 0.78) * 46) > -0.35)
    blinds = blur(blinds.astype(np.float32), 6)
    lightmap = 0.62 + 0.62 * beamm * blinds
    if dark_set:
        lightmap = 0.55 + 1.0 * beamm * blinds
    img *= lightmap[..., None]
    img += (beamm * blinds)[..., None] * beam * (0.10 if not dark_set else 0.16)

    # glossy slab: compressed marble surface, gold trim, front face
    st, se = int(SLAB_TOP * H), int(SLAB_EDGE * H)
    surf_h = se - st
    surf = marble(surf_h * 3, W, light * 1.02, dark * 0.95, vein, rng, angle=0.2, freq=3.0)
    surf = np.asarray(Image.fromarray(np.clip(surf, 0, 255).astype(np.uint8)).resize((W, surf_h), Image.LANCZOS), np.float32)
    sy = np.linspace(0, 1, surf_h, dtype=np.float32)[:, None, None]
    surf *= (0.82 + 0.30 * sy)                          # lighter toward the viewer
    surf *= (0.85 + 0.35 * np.exp(-((np.linspace(0, 1, W) - 0.55) / 0.45) ** 2))[None, :, None]
    if dark_set:
        surf *= 1.25
    img[st:se] = surf
    img[st:st + 3] *= 0.75                              # back edge shadow line
    face = marble(H - se, W, dark * 0.92, dark * 0.78, vein * 0.9, rng, angle=1.4, freq=2.0, vein_op=0.35)
    fy = np.linspace(0, 1, H - se, dtype=np.float32)[:, None, None]
    img[se:] = face * (0.92 - 0.35 * fy)
    trim = np.exp(-((np.arange(H, dtype=np.float32) - se) / 3.2) ** 2)[:, None, None]
    img = img * (1 - trim * 0.95) + (gold * 1.08 + 30) * trim * 0.95

    # vignette + warm grade
    v = ((nx - 0.5) / 0.78) ** 2 + ((ny - 0.5) / 0.80) ** 2
    img *= (1 - 0.30 * np.clip(v, 0, 1.5) ** 1.5)[..., None]
    img = img * np.array([1.03, 1.0, 0.95], np.float32)
    return img, dark_set


# product sets: (part file, height relative to main box, x centre in main-box heights, depth 0 back .. 2 front)
# rule: no vial is taller than its own box
PRODUCT_SETS = {
    'plla': [('plla-box', 1.0, 0.0, 0), ('plla-vial-a', .74, 1.02, 1), ('plla-vial-b', .74, 1.52, 1)],
    'fix-face-cpdrn': [('fix-face-cpdrn-box', 1.0, 0.0, 0), ('fix-face-cpdrn-vial', .94, 1.12, 1)],
    'fix-face-ha-18': [('fix-face-ha-18-box', 1.0, 0.0, 0), ('fix-face-ha-18-vial', .94, 1.12, 1)],
    'fix-face-collagen': [('fix-face-collagen-box', 1.0, 0.0, 0), ('fix-face-collagen-vial', .92, 1.12, 1)],
    'fix-face-skin-booster': [('fix-face-skin-booster-box', 1.0, 0.0, 0), ('fix-face-skin-booster-vial', .94, 1.12, 1)],
    'lipo-360': [('lipo-360-box', 1.0, 0.0, 0), ('lipo-360-vial', .74, .64, 1)],
    'liporase': [('liporase-box', 1.0, 0.0, 0), ('liporase-vial', .86, 1.04, 1)],
    'exoroot': [('exoroot-box', 1.0, 0.0, 0), ('exoroot-vial-a', .60, .30, 1), ('exoroot-vial-b', .60, .64, 1)],
    'exo-nad': [('exo-nad-bigbox', 1.0, 0.0, 0), ('exo-nad-box', .56, -.98, 1), ('exo-nad-vial-a', .60, .78, 2), ('exo-nad-vial-b', .60, 1.12, 2)],
    'lxc': [('lxc-bigbox', 1.0, 0.0, 0), ('lxc-smallbox', .56, -1.02, 1), ('lxc-vial-a', .54, .66, 2), ('lxc-vial-b', .54, .94, 2)],
    'yeellow-drop': [('yeellow-drop-box', 1.0, 0.0, 0), ('yeellow-drop-vial', .92, 1.10, 1)],
}
FLAT_FRONTS = {'fix-face-ultra', 'fix-face-ultra-plus', 'fix-face-grand', 'fix-face-cpdrn', 'fix-face-ha-18',
               'fix-face-collagen', 'fix-face-skin-booster', 'agasthi-h', 'agasthi-s', 'agasthi-fine',
               'agasthi-deep', 'agasthi-sub-q', 'qf-fi-ne', 'qf-deep', 'qf-sub-q', 'lipo-360', 'exoroot'}


def box_shading(im):
    a = np.asarray(im, np.float32).copy(); h, w = a.shape[:2]
    x = np.linspace(0, 1, w, dtype=np.float32); y = np.linspace(0, 1, h, dtype=np.float32)
    side = 1 - 0.16 * (np.exp(-x / .02) + np.exp(-(1 - x) / .03))
    vert = 1.05 - 0.14 * y
    a[..., :3] *= (side[None, :] * vert[:, None])[..., None]
    a[..., :3] += (np.exp(-y / .012)[:, None] * 0.08 * 255)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def layout(pid, pdir):
    parts = PRODUCT_SETS.get(pid, [((pid + '-box') if pid != 'yeellow-drop' else 'yeellow-drop-vial', 1.0, 0.0, 0)])
    items = []
    for f, hr, xc, depth in parts:
        im = Image.open(os.path.join(pdir, f + '.png')).convert('RGBA')
        if f.endswith('-box') and f[:-4] in FLAT_FRONTS:
            im = box_shading(im)
        items.append((im, hr, xc, depth))
    xs = []
    for im, hr, xc, d in items:
        w = im.width / im.height * hr; xs += [xc - w / 2, xc + w / 2]
    gx0, gx1 = min(xs), max(xs); gw = gx1 - gx0; gh = max(t[1] for t in items)
    if pid in ('agasthi-deep', 'agasthi-fine', 'agasthi-sub-q'):
        s = 0.70 * W / gw          # identical boxes -> identical on-screen size
    else:
        s = min((0.80 if len(items) > 1 else 0.72) * W / gw, 0.50 * H / gh, (0.30 * W * H * .55 / (gw * gh)) ** .5)
    cx = (gx0 + gx1) / 2; out = []
    for im, hr, xc, d in sorted(items, key=lambda t: t[3]):
        ph = hr * s; pw = im.width / im.height * ph
        out.append((im.resize((max(1, round(pw)), max(1, round(ph))), Image.LANCZOS), W / 2 + (xc - cx) * s, d))
    return out


def render(pid, pdir, out, index=0):
    rng = np.random.default_rng(abs(hash(pid)) % (2 ** 32))
    bg, dark_set = build_set(PRODUCT_SET.get(pid, 'champagne'), rng)
    if index % 2:
        bg = bg[:, ::-1]
    c = bg
    for prod, cxp, depth in layout(pid, pdir):
        pw, ph = prod.size
        pr = np.asarray(prod, np.float32); A = pr[..., 3] / 255
        solid = A > 0.5; cols = np.where(solid.any(0))[0]
        bottom = np.full(pw, -1); bottom[cols] = ph - 1 - np.argmax(solid[::-1, cols], axis=0)
        yb = int((BASE + 0.014 * depth) * H)
        x0 = int(round(cxp - pw / 2)); y0 = yb - (bottom.max() + 1)
        occ = np.zeros((H, W), np.float32)
        for x in cols:
            X = x0 + x; Y = y0 + bottom[x]
            if 0 <= X < W: occ[Y - 2:Y + 3, X] = 1.0
        span = float(cols.max() - cols.min())
        k = (np.clip(blur(occ, 3.5) * 3.0, 0, 1) * 0.65 + np.clip(blur(occ, max(14, span * .02)) * 5, 0, 1) * 0.45
             + np.clip(blur(occ, max(40, span * .06)) * 9, 0, 1) * 0.25)
        k = np.clip(k, 0, 0.9)[..., None]
        c = c * (1 - k) + np.array([20, 14, 8], np.float32) * k
        depth_px = max(4, min(int(ph * 0.55), int(SLAB_EDGE * H) - yb - 4))
        d = np.arange(depth_px)[:, None]
        src_y = bottom[None, :] - d
        valid = (bottom[None, :] >= 0) & (src_y >= 0)
        xs = np.broadcast_to(np.arange(pw)[None, :], src_y.shape)
        refl = pr[np.clip(src_y, 0, ph - 1), xs].copy()
        strength = 0.42 if dark_set else 0.34
        refl[..., 3] *= (np.linspace(strength * 1.15, 0, depth_px, dtype=np.float32) ** 1.25)[:, None] * valid
        layer = np.zeros((H, W, 4), np.float32)
        ys = y0 + bottom[None, :] + 1 + d; X = x0 + xs
        ok = valid & (ys < H) & (X >= 0) & (X < W)
        layer[ys[ok], X[ok]] = refl[ok]
        la = blur(layer[..., 3], 2.2)[..., None] / 255
        lc = np.stack([blur(layer[..., i] * layer[..., 3] / 255, 2.2) for i in range(3)], -1) / np.maximum(la, 1e-4)
        c = c * (1 - la) + np.clip(lc, 0, 255) * la
        rgb = pr[..., :3] * np.array([1.02, 1.0, 0.97], np.float32) + 2
        xa, xb = max(0, x0), min(W, x0 + pw)
        a = A[:, xa - x0:xb - x0, None]
        c[y0:y0 + ph, xa:xb] = c[y0:y0 + ph, xa:xb] * (1 - a) + np.clip(rgb[:, xa - x0:xb - x0], 0, 255) * a
    grain = rng.normal(0, 2.4, (H, W, 1)).astype(np.float32)
    Image.fromarray(np.clip(c + grain, 0, 255).astype(np.uint8)).resize((1600, 2000), Image.LANCZOS).save(out, 'WEBP', quality=88, method=6)
    return dark_set


if __name__ == '__main__':
    pdir, outdir = sys.argv[1], sys.argv[2]
    order = sorted(PRODUCT_SET)
    names = sys.argv[3:] or order
    os.makedirs(outdir, exist_ok=True)
    for n in names:
        dark = render(n, pdir, os.path.join(outdir, n + '.webp'), order.index(n))
        print('ok', n, 'dark' if dark else 'light', flush=True)

"""Fix Face avant-garde 4:5 product posters.

Each product cutout is placed on a procedurally built luxury set:
veined marble wall with sweeping gold-edged marble ribbons, a raking
golden light beam with window-blind shadows, and a glossy marble slab
with a gold trim, real contact shadow and mirror reflection. Marble
tone is matched to the packaging; the set mirrors on alternate products.

Usage: python3 tools/fixface_poster.py <cutout_dir> <out_dir> [ids...]
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


def fit(prod):
    bb = prod.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox()
    prod = prod.crop(bb); w, h = prod.size
    s = (0.30 * W * H * 0.55 / (w * h)) ** 0.5
    s = min(s, 0.80 * W / w, 0.56 * H / h)
    return prod.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)


def render(src, out, index=0):
    name = os.path.splitext(os.path.basename(src))[0]
    rng = np.random.default_rng(abs(hash(name)) % (2 ** 32))
    bg, dark_set = build_set(PRODUCT_SET.get(name, 'champagne'), rng)
    if index % 2:
        bg = bg[:, ::-1]
    prod = fit(Image.open(src).convert('RGBA'))
    pw, ph = prod.size
    pr = np.asarray(prod, np.float32)
    A = pr[..., 3] / 255
    solid = A > 0.5
    cols = np.where(solid.any(0))[0]
    bottom = np.full(pw, -1)
    bottom[cols] = ph - 1 - np.argmax(solid[::-1, cols], axis=0)
    yb = int(BASE * H)
    x0 = (W - pw) // 2
    y0 = yb - (bottom.max() + 1)

    # contact + ambient shadows following the product's own footprint
    occ = np.zeros((H, W), np.float32)
    for x in cols:
        by = y0 + bottom[x]
        occ[by - 2:by + 3, x0 + x] = 1.0
    span = float(cols.max() - cols.min())
    k = (np.clip(blur(occ, 3.5) * 3.0, 0, 1) * 0.65 + np.clip(blur(occ, max(14, span * .02)) * 5, 0, 1) * 0.45
         + np.clip(blur(occ, max(40, span * .06)) * 9, 0, 1) * 0.25)
    k = np.clip(k, 0, 0.9)[..., None]
    shadow = np.array([20, 14, 8], np.float32)
    c = bg * (1 - k) + shadow * k

    # mirror reflection on the glossy slab (stops at the gold edge)
    depth = min(int(ph * 0.55), int(SLAB_EDGE * H) - yb - 4)
    d = np.arange(depth)[:, None]
    src_y = bottom[None, :] - d
    valid = (bottom[None, :] >= 0) & (src_y >= 0)
    xs = np.broadcast_to(np.arange(pw)[None, :], src_y.shape)
    refl = pr[np.clip(src_y, 0, ph - 1), xs].copy()
    strength = 0.42 if dark_set else 0.34
    refl[..., 3] *= (np.linspace(strength * 1.15, 0, depth, dtype=np.float32) ** 1.25)[:, None] * valid
    layer = np.zeros((H, W, 4), np.float32)
    ys = y0 + bottom[None, :] + 1 + d
    ok = valid & (ys < H)
    layer[ys[ok], (x0 + xs)[ok]] = refl[ok]
    la = blur(layer[..., 3], 2.2)[..., None] / 255
    lc = np.stack([blur(layer[..., i] * layer[..., 3] / 255, 2.2) for i in range(3)], -1) / np.maximum(la, 1e-4)
    c = c * (1 - la) + np.clip(lc, 0, 255) * la

    # product, lightly graded into the warm light
    rgb = pr[..., :3] * np.array([1.02, 1.0, 0.97], np.float32) + 2
    a = A[..., None]
    region = c[y0:y0 + ph, x0:x0 + pw]
    c[y0:y0 + ph, x0:x0 + pw] = region * (1 - a) + np.clip(rgb, 0, 255) * a

    # specular kiss of the beam across the product's top edge
    grain = rng.normal(0, 2.4, (H, W, 1)).astype(np.float32)
    outimg = Image.fromarray(np.clip(c + grain, 0, 255).astype(np.uint8))
    outimg.resize((1600, 2000), Image.LANCZOS).save(out, 'WEBP', quality=88, method=6)
    return dark_set


if __name__ == '__main__':
    srcdir, outdir = sys.argv[1], sys.argv[2]
    order = [os.path.splitext(os.path.basename(f))[0] for f in sorted(glob.glob(srcdir + '/*.png'))]
    names = sys.argv[3:] or order
    os.makedirs(outdir, exist_ok=True)
    for n in names:
        dark = render(f'{srcdir}/{n}.png', f'{outdir}/{n}.webp', order.index(n) if n in order else 0)
        print('ok', n, 'dark' if dark else 'light', flush=True)

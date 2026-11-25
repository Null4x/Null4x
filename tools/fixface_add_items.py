"""Add companion vials/boxes onto the approved Fix Face marble posters
without moving or restyling the existing product.

The approved posters were rendered by fixface_poster.py @243244b at 2000x2500
and saved at 1600x2000: the product's bottom sits on y = 0.815*H, centred,
scaled by fit(). We rebuild that geometry, then draw extra parts with the same
contact shadow, slab reflection and grading.

Usage: python3 tools/fixface_add_items.py <posters_in> <src_dir> <src2_dir> <posters_out>
"""
import os, sys
import numpy as np
from PIL import Image

SW, SH = 2000, 2500          # render space of the original
W, H = 1600, 2000            # delivered posters
K = W / SW
YB = int(0.815 * SH) * K     # product baseline in poster px
EDGE = 0.865 * H             # gold front edge of the slab
DARK = {'fix-face-grand', 'qf-sub-q', 'qf-deep', 'exoroot'}


def _box(a, r, axis):
    r = max(1, int(r))
    pad = [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)]
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis, dtype=np.float64)
    n = c.shape[axis]
    return ((np.take(c, np.arange(2 * r + 1, n), axis=axis) - np.take(c, np.arange(0, n - 2 * r - 1), axis=axis)) / (2 * r + 1)).astype(np.float32)


def blur(a, r):
    a = a.astype(np.float32); br = max(1.0, r * 0.93)
    for ax in (0, 1):
        for _ in range(3): a = _box(a, br, ax)
    return a


def trim(im):
    im = im.convert('RGBA')
    return im.crop(im.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox())


def load_cut(path):
    im = Image.open(path)
    if im.mode != 'RGBA':           # white-background jpg -> alpha
        rgb = np.asarray(im.convert('RGB')).astype(np.int16)
        import cv2
        mx, mn = rgb.max(-1).astype(np.float32), rgb.min(-1).astype(np.float32)
        sat = (mx - mn) / np.maximum(mx, 1)
        core = ((sat > 0.18) | (mx < 90)).astype(np.uint8)          # coloured box faces
        light = (np.abs(rgb - 255).max(-1) > 12)                    # anything not white (incl. pale top face)
        ys, xs = np.nonzero(core)
        x_lo, x_hi = np.percentile(xs, 0.2), np.percentile(xs, 99.8)
        colbot = np.full(core.shape[1], -1)
        cols = np.where(core.any(0))[0]
        colbot[cols] = core.shape[0] - 1 - np.argmax(core[::-1, cols], axis=0)
        yy = np.arange(core.shape[0])[:, None]
        inside = (np.arange(core.shape[1])[None, :] >= x_lo) & (np.arange(core.shape[1])[None, :] <= x_hi) & (yy <= colbot[None, :])
        m = ((light & inside) | core.astype(bool)).astype(np.uint8)  # keep the top face, drop the floor shadow
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        m = (lab == keep).astype(np.uint8)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        m = np.zeros_like(m); cv2.drawContours(m, cnts, -1, 1, thickness=cv2.FILLED)   # fill white lettering
        a = cv2.GaussianBlur(m.astype(np.float32) * 255, (3, 3), 0).astype(np.uint8)
        im = im.convert('RGBA'); im.putalpha(Image.fromarray(a))
    return trim(im)


def main_geom(src):
    """Size and placement of the product exactly as the original fit() did."""
    im = trim(Image.open(src))
    w, h = im.size
    s = min((0.30 * SW * SH * 0.55 / (w * h)) ** 0.5, 0.80 * SW / w, 0.56 * SH / h)
    pw, ph = round(w * s * K), round(h * s * K)
    return im, pw, ph, (W - pw) / 2, YB


def draw(c, im, cx, base, dark, rng, shadow=True):
    pw, ph = im.size
    pr = np.asarray(im, np.float32); A = pr[..., 3] / 255
    solid = A > 0.5; cols = np.where(solid.any(0))[0]
    bottom = np.full(pw, -1); bottom[cols] = ph - 1 - np.argmax(solid[::-1, cols], axis=0)
    x0 = int(round(cx - pw / 2)); y0 = int(round(base)) - (bottom.max() + 1)
    if shadow:
        occ = np.zeros((H, W), np.float32)
        for x in cols:
            X, Y = x0 + x, y0 + bottom[x]
            if 0 <= X < W: occ[Y - 2:Y + 3, X] = 1.0
        span = float(cols.max() - cols.min())
        k = (np.clip(blur(occ, 3.5 * K) * 3.0, 0, 1) * 0.65 + np.clip(blur(occ, max(14, span * .02) * K) * 5, 0, 1) * 0.45
             + np.clip(blur(occ, max(40, span * .06) * K) * 9, 0, 1) * 0.25)
        k = np.clip(k, 0, 0.9)[..., None]
        c[:] = c * (1 - k) + np.array([20, 14, 8], np.float32) * k
    depth = max(4, min(int(ph * 0.55), int(EDGE - base) - 4))
    d = np.arange(depth)[:, None]
    sy = bottom[None, :] - d
    valid = (bottom[None, :] >= 0) & (sy >= 0)
    xs = np.broadcast_to(np.arange(pw)[None, :], sy.shape)
    refl = pr[np.clip(sy, 0, ph - 1), xs].copy()
    st = 0.42 if dark else 0.34
    refl[..., 3] *= (np.linspace(st * 1.15, 0, depth, dtype=np.float32) ** 1.25)[:, None] * valid
    layer = np.zeros((H, W, 4), np.float32)
    Y = y0 + bottom[None, :] + 1 + d; X = x0 + xs
    ok = valid & (Y < H) & (X >= 0) & (X < W)
    layer[Y[ok], X[ok]] = refl[ok]
    la = blur(layer[..., 3], 2.2 * K)[..., None] / 255
    lc = np.stack([blur(layer[..., i] * layer[..., 3] / 255, 2.2 * K) for i in range(3)], -1) / np.maximum(la, 1e-4)
    c[:] = c * (1 - la) + np.clip(lc, 0, 255) * la
    rgb = pr[..., :3] * np.array([1.02, 1.0, 0.97], np.float32) + 2 + rng.normal(0, 2.4, (ph, pw, 1)).astype(np.float32)
    xa, xb = max(0, x0), min(W, x0 + pw)
    a = A[:, xa - x0:xb - x0, None]
    c[y0:y0 + ph, xa:xb] = c[y0:y0 + ph, xa:xb] * (1 - a) + np.clip(rgb[:, xa - x0:xb - x0], 0, 255) * a


def by_height(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), round(h)), Image.LANCZOS)


def by_width(im, w):
    return im.resize((round(w), max(1, round(im.height * w / im.width))), Image.LANCZOS)


FRONT = 22   # vials in front of a box stand slightly lower on the slab


def build(pid, src, src2):
    """Return list of (image, centre x, baseline, shadow) to draw on top of the poster."""
    main, pw, ph, x0, yb = main_geom(f'{src}/{pid}.png')
    x1 = x0 + pw
    v = lambda n: load_cut(f'{src2}/{n}.png')
    if pid in ('fix-face-cpdrn', 'fix-face-ha-18', 'fix-face-collagen', 'fix-face-skin-booster'):
        vial = {'fix-face-cpdrn': 'cpdrn-vial', 'fix-face-ha-18': 'ha18-vial',
                'fix-face-collagen': 'collagen-vial', 'fix-face-skin-booster': 'skinbooster-vial'}[pid]
        im = by_height(v(vial), ph * 0.78)
        return [(im, x1 - im.width * 0.50, yb + FRONT, True)]
    if pid == 'plla':
        a = by_height(v('plla-vial-powder'), ph * 0.72); b = by_height(v('plla-vial-liquid'), ph * 0.72)
        return [(a, x1 - a.width * 0.30, yb + FRONT, True), (b, x1 + b.width * 0.78, yb + FRONT, True)]
    if pid == 'lipo-360':
        box = by_height(main, ph * 1.08); bx1 = W / 2 + box.width / 2
        im = by_height(v('lipo-vial'), ph * 0.60)
        return [(box, W / 2, yb, True), (im, bx1 - im.width * 0.05, yb + FRONT, True)]
    if pid == 'liporase':
        im = by_height(v('liporase-vial'), ph * 0.86)
        return [(im, x1 + im.width * 0.12, yb + FRONT, True)]
    if pid == 'exoroot':
        h = ph * 0.58
        a = by_height(v('exoroot-vial-solution'), h); b = by_height(v('exoroot-vial-powder'), h)
        return [(a, x1 - a.width * 1.55, yb + FRONT, True), (b, x1 - b.width * 0.55, yb + FRONT, True)]
    if pid == 'lxc':
        h = ph * 0.60          # vials never taller than the small 1-set box
        a = by_height(v('lxc-vials'), h)
        return [(a, x1 - a.width * 0.42, yb + FRONT, True)]
    if pid == 'exo-nad':
        # same structure and on-screen sizes as the LXC poster (lxc.png: 1280x395 group, centred)
        _, lw, lh, lx0, _ = main_geom(f'{src}/lxc.png'); lx1 = lx0 + lw
        big = by_height(load_cut(f'{src2}/exonad-bigbox.jpg'), lh * 0.99)
        small = by_height(main, lh * 0.65)
        vh = lh * 0.60                                   # same vial height as LXC, below the small box
        va = by_height(v('exonad-vial-1'), vh); vb = by_height(v('exonad-vial-2'), vh)
        return [(big, lx1 - big.width / 2, yb, True),                     # big box behind, right
                (small, lx0 + small.width / 2, yb + 6, True),             # small box in front, left
                (va, lx1 - va.width * 1.45, yb + FRONT, True),            # vials front, right
                (vb, lx1 - vb.width * 0.45, yb + FRONT, True)]
    if pid == 'yeellow-drop':
        vial = by_height(main, ph * 0.55)                # clearly smaller vial
        box = by_width(v('yellowdrop-box'), ph * 0.98)
        bcx = W * 0.45
        return [(box, bcx, yb - 30, True), (vial, bcx + box.width * 0.47, yb + FRONT, True)]
    if pid == 'yeellow-drop-old':
        box = by_width(v('yellowdrop-box'), ph * 1.0)                         # box as long as the vial is tall
        vial = by_height(main, ph)
        return [(box, box.width / 2 + 34, yb - 30, True),                     # box behind, kept inside the frame
                (vial, x0 + pw / 2, yb, False)]                                # existing vial redrawn on top
    if pid in ('agasthi-deep', 'agasthi-fine', 'agasthi-sub-q'):
        # one physical box -> one on-screen size for all three
        return [(main.resize((1100, 512), Image.LANCZOS), W / 2, yb, True)]
    if pid in ('agasthi-deep-old',):
        # same box as Sub-Q: match Sub-Q's on-screen front length (drawn over the original, which it fully covers)
        _, spw, _, _, _ = main_geom(f'{src}/agasthi-sub-q.png')
        front_ratio_self, front_ratio_subq = 0.893, 0.914   # front-face share of each cut-out's width
        target = spw * front_ratio_subq / front_ratio_self
        im = by_width(main, target)
        return [(im, W / 2, yb, True)]
    return []


REBUILD = {'yeellow-drop', 'exo-nad', 'agasthi-deep', 'agasthi-fine', 'agasthi-sub-q'}


def fresh_background(pid, src):
    """Same marble set the approved poster used, rebuilt (needed where the product shrinks)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fixface_poster as fp
    import glob as g
    order = sorted(os.path.splitext(os.path.basename(f))[0] for f in g.glob(src + '/*.png'))
    rng = np.random.default_rng(sum(map(ord, pid)) * 7919)
    bg, _ = fp.build_set(fp.PRODUCT_SET[pid], rng)
    if order.index(pid) % 2:
        bg = bg[:, ::-1]
    bg = bg + rng.normal(0, 2.4, (SH, SW, 1)).astype(np.float32)
    return np.asarray(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS), np.float32).copy()


if __name__ == '__main__':
    pin, src, src2, pout = sys.argv[1:5]
    os.makedirs(pout, exist_ok=True)
    ids = ['plla', 'fix-face-cpdrn', 'fix-face-ha-18', 'fix-face-collagen', 'fix-face-skin-booster', 'lipo-360',
           'liporase', 'exoroot', 'exo-nad', 'lxc', 'yeellow-drop', 'agasthi-deep', 'agasthi-fine', 'agasthi-sub-q']
    for pid in sys.argv[5:] or ids:
        c = fresh_background(pid, src) if pid in REBUILD else np.asarray(Image.open(f'{pin}/{pid}.webp').convert('RGB'), np.float32).copy()
        rng = np.random.default_rng(7)
        for im, cx, base, sh in build(pid, src, src2):
            draw(c, im, cx, base, pid in DARK, rng, sh)
        Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save(f'{pout}/{pid}.webp', 'WEBP', quality=88, method=6)
        print('ok', pid, flush=True)

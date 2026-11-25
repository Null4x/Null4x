"""Render a consistent luxury 4:5 studio poster for each product cutout."""
import sys, os, glob
import numpy as np
from PIL import Image, ImageFilter

W, H = 2000, 2500
HORIZON = 0.635          # wall meets floor
BASE = 0.775             # product stands on this line
rng = np.random.default_rng(7)

def lerp(a, b, t):
    return a + (b - a) * t

def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)], dtype=np.float32)

TONES = {
    # dark sets for black / deep packaging, light tinted sets for the rest
    'fix-face-ultra': ('dark', '#3a3128'), 'fix-face-ultra-plus': ('dark', '#3a3128'),
    'fix-face-grand': ('dark', '#3a3128'), 'plla': ('dark', '#3b3226'),
    'fix-face-collagen': ('dark', '#3e2a30'), 'fix-face-cpdrn': ('dark', '#3f2f22'),
    'fix-face-ha-18': ('dark', '#25313f'), 'fix-face-skin-booster': ('dark', '#3b3324'),
    'fix-face-pdo': ('dark', '#34353b'), 'qf-deep': ('dark', '#1f2a45'),
    'qf-sub-q': ('dark', '#2f2a24'), 'exoroot': ('dark', '#2e3136'),
    'agasthi-h': ('light', '#8f86c9'), 'agasthi-s': ('light', '#c47aa8'),
    'agasthi-fine': ('light', '#7f9fd8'), 'agasthi-deep': ('light', '#7282d0'),
    'agasthi-sub-q': ('light', '#7aa3dc'), 'agasthi-body': ('light', '#b9837f'),
    'audrey-h': ('light', '#8a7566'), 'audrey-m': ('light', '#7b92e0'),
    'audrey-m-2ml': ('light', '#7b92e0'), 'qf-fi-ne': ('light', '#e0c58a'),
    'lipo-360': ('light', '#d9824a'), 'yeellow-drop': ('light', '#e6c84a'),
    'cellix-pn': ('light', '#9aa0a8'), 'liporase': ('light', '#a183c4'),
    'hyalmas': ('light', '#a9c46a'), 'exo-nad': ('light', '#5f86d6'),
    'lxc': ('light', '#5b7fe0'), 'hyaron': ('light', '#b56a92'),
}

def mix(a, b, t):
    return hexc(a) * (1 - t) + hexc(b) * t

def set_palette(name):
    global WALL_TOP, WALL_LOW, NICHE_TOP, NICHE_LOW, FLOOR_FAR, FLOOR_NEAR, GLOW, LINE, SHADOW, MODE
    MODE, tone = TONES.get(name, ('light', '#d8c3a0'))
    T = hexc(tone)
    if MODE == 'light':
        WALL_TOP, WALL_LOW = mix('#f2ebe0', tone, .34), mix('#e2d5c2', tone, .44)
        NICHE_TOP, NICHE_LOW = mix('#fcf8f2', tone, .15), mix('#efe5d6', tone, .30)
        FLOOR_FAR, FLOOR_NEAR = mix('#e0d2bc', tone, .42), mix('#cdb99d', tone, .52)
        GLOW, LINE = np.array([26, 20, 12], np.float32), np.array([176, 136, 72], np.float32)
        SHADOW = T * 0.25
    else:
        WALL_TOP, WALL_LOW = T * 1.05, T * 0.72
        NICHE_TOP, NICHE_LOW = T * 1.9 + 18, T * 1.15
        FLOOR_FAR, FLOOR_NEAR = T * 1.25, T * 0.78
        GLOW, LINE = np.array([70, 54, 30], np.float32), np.array([212, 170, 98], np.float32)
        SHADOW = np.array([6, 5, 4], np.float32)

set_palette('')

def background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ny, nx = yy / H, xx / W
    img = np.zeros((H, W, 3), np.float32)
    # wall
    t = np.clip(ny / HORIZON, 0, 1)[..., None]
    wall = lerp(WALL_TOP, WALL_LOW, t)
    # arched niche
    cx, aw = 0.5, 0.36          # half width as fraction of W
    top = 0.13                  # top of arch
    r = aw * W
    cy = top * H + r
    dx = (xx - cx * W)
    inside_rect = (np.abs(dx) <= r) & (yy >= cy)
    inside_circ = (dx ** 2 + (yy - cy) ** 2) <= r ** 2
    niche = (inside_rect | inside_circ) & (ny < HORIZON)
    nt = np.clip((ny - top) / (HORIZON - top), 0, 1)[..., None]
    niche_col = lerp(NICHE_TOP, NICHE_LOW, nt)
    mask = Image.fromarray((niche * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    m = np.asarray(mask, np.float32)[..., None] / 255
    img = wall * (1 - m) + niche_col * m
    # soft inner shadow on the left edge of the niche (light from upper right)
    edge = Image.fromarray((niche * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(60))
    e = 1 - np.asarray(edge, np.float32)[..., None] / 255
    side = np.clip((cx * W - xx) / r, 0, 1)[..., None]
    img -= m * e * (18 + 26 * side)
    # fine brushed-gold inlay tracing the arch
    dist = np.where(yy >= cy, np.abs(np.abs(dx) - r), np.abs(np.sqrt(dx ** 2 + (yy - cy) ** 2) - r))
    line = np.exp(-(dist / 1.6) ** 2) * (ny < HORIZON) * ((yy >= cy) | (yy <= cy))
    sheen = 0.55 + 0.45 * np.exp(-((nx - 0.62) / 0.22) ** 2 - ((ny - 0.25) / 0.25) ** 2)
    gold = LINE
    lw = (line * 0.85 * sheen)[..., None]
    img = img * (1 - lw) + gold * lw
    # floor
    ft = np.clip((ny - HORIZON) / (1 - HORIZON), 0, 1)[..., None]
    floor = lerp(FLOOR_FAR, FLOOR_NEAR, ft ** 0.8)
    fm = (ny >= HORIZON)[..., None].astype(np.float32)
    fmask = Image.fromarray((fm[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    fm = np.asarray(fmask, np.float32)[..., None] / 255
    img = img * (1 - fm) + floor * fm
    # contact line where wall meets floor
    band = np.exp(-((ny - HORIZON) * H / 10) ** 2)[..., None]
    img -= band * 14
    # key light: warm pool behind and around product
    d = ((nx - 0.56) / 0.42) ** 2 + ((ny - 0.42) / 0.36) ** 2
    img += np.exp(-d)[..., None] * GLOW
    fl = ((nx - 0.5) / 0.38) ** 2 + ((ny - BASE) / 0.07) ** 2
    img += np.exp(-fl)[..., None] * GLOW * 0.85 * fm
    # diagonal window light streak on wall (very soft)
    s = (nx * 0.9 + ny * 0.55)
    streak = np.exp(-((s - 0.98) / 0.05) ** 2) * (ny < HORIZON)
    img += Image_blur(streak, 40)[..., None] * np.array([14, 11, 6], np.float32)
    # vignette
    v = ((nx - 0.5) / 0.75) ** 2 + ((ny - 0.48) / 0.72) ** 2
    img *= (1 - 0.20 * np.clip(v, 0, 1.4) ** 1.6)[..., None]
    return img

def _box(a, r, axis):
    r = max(1, int(r))
    c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode='edge'), axis=axis)
    hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
    lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
    return (hi - lo) / (2 * r + 1)

def Image_blur(arr, r):
    """Float gaussian approximation: three box passes per axis."""
    a = arr.astype(np.float64)
    br = max(1.0, float(r) * 0.93)
    for axis in (0, 1):
        for _ in range(3):
            a = _box(a, br, axis)
    return a.astype(np.float32)

def fit(prod):
    a = prod.getchannel('A')
    bb = a.point(lambda v: 255 if v > 10 else 0).getbbox()
    prod = prod.crop(bb)
    w, h = prod.size
    target_area = 0.26 * W * H * 0.55       # consistent visual mass
    s = (target_area / (w * h)) ** 0.5
    s = min(s, 0.74 * W / w, 0.50 * H / h)
    return prod.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)

def render(src, out):
    set_palette(os.path.splitext(os.path.basename(src))[0])
    bg = background()
    prod = fit(Image.open(src).convert('RGBA'))
    pw, ph = prod.size
    x0 = (W - pw) // 2
    y0 = int(BASE * H) - ph
    canvas = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert('RGBA')
    alpha = prod.getchannel('A')

    A = np.asarray(alpha, np.float32) / 255
    solid = A > 0.5
    cols = np.where(solid.any(0))[0]
    bottom = np.full(pw, -1)
    bottom[cols] = ph - 1 - np.argmax(solid[::-1, cols], axis=0)
    # shift so the lowest point sits on the base line
    yb = int(BASE * H)
    y0 = yb - (bottom.max() + 1)

    c = np.asarray(canvas.convert('RGB'), np.float32)
    dark = SHADOW
    # ambient occlusion: wide soft shadow spanning the footprint
    occ = np.zeros((H, W), np.float32)
    span = float(cols.max() - cols.min())
    for x in cols[::2]:
        by = y0 + bottom[x]
        occ[by - 2:by + 3, x0 + x] = 1.0
    occ_wide = Image_blur(np.clip(occ, 0, 1), max(14, span * 0.018)) * 1.0
    occ_soft = Image_blur(np.clip(occ, 0, 1), max(40, span * 0.06))
    # squash the soft shadow vertically (ellipse feel)
    occ_tight = Image_blur(np.clip(occ, 0, 1), 3.5)
    k = (np.clip(occ_tight * 3.0, 0, 1) * 0.55 + np.clip(occ_wide * 5.0, 0, 1) * 0.50
         + np.clip(occ_soft * 9.0, 0, 1) * 0.28)
    k = np.clip(k, 0, 0.86)[..., None]
    c = c * (1 - k) + dark * k

    # per-column mirror reflection about each column's own contact point
    pr = np.asarray(prod, np.float32)
    depth = int(ph * 0.38)
    refl = np.zeros((depth, pw, 4), np.float32)
    d = np.arange(depth)[:, None]
    src_y = bottom[None, :] - d
    valid = (bottom[None, :] >= 0) & (src_y >= 0)
    src_y = np.clip(src_y, 0, ph - 1)
    xs = np.broadcast_to(np.arange(pw)[None, :], src_y.shape)
    refl = pr[src_y, xs]
    fade = (np.linspace(0.26, 0, depth, dtype=np.float32) ** 1.5)[:, None]
    refl[..., 3] *= fade * valid
    # paste: reflection column x starts at y0+bottom[x]+1
    layer = np.zeros((H, W, 4), np.float32)
    ys = (y0 + bottom[None, :] + 1 + d)
    ok = valid & (ys < H)
    layer[ys[ok], (x0 + xs)[ok]] = refl[ok]
    rl = Image.fromarray(layer.astype(np.uint8), 'RGBA').filter(ImageFilter.GaussianBlur(3))
    base = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).convert('RGBA')
    base = Image.alpha_composite(base, rl)

    # product with a whisper of warm grading
    rgb = pr[..., :3] * np.array([1.012, 1.0, 0.978], np.float32) + 2
    pr2 = pr.copy(); pr2[..., :3] = np.clip(rgb, 0, 255)
    prod2 = Image.fromarray(pr2.astype(np.uint8), 'RGBA')
    pl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pl.paste(prod2, (x0, y0), prod2)
    base = Image.alpha_composite(base, pl)
    out_rgb = np.asarray(base.convert('RGB'), np.float32)

    # film grain
    grain = rng.normal(0, 2.2, (H, W, 1)).astype(np.float32)
    out_rgb = np.clip(out_rgb + grain, 0, 255).astype(np.uint8)
    im = Image.fromarray(out_rgb)
    im = im.resize((1600, 2000), Image.LANCZOS)
    im.save(out, 'WEBP', quality=88, method=6)

if __name__ == '__main__':
    srcdir, outdir = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or [os.path.splitext(os.path.basename(f))[0] for f in sorted(glob.glob(srcdir + '/*.png'))]
    os.makedirs(outdir, exist_ok=True)
    for n in names:
        render(f'{srcdir}/{n}.png', f'{outdir}/{n}.webp')
        print('ok', n)

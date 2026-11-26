"""Fix face brand QR generator -> qr_card.html (styled card) + fixface_qr.svg (QR only)."""
import segno

URL = "https://www.instagram.com/fix.face.aesthetic/"
qr = segno.make(URL, error="h", boost_error=False)
M = [list(r) for r in qr.matrix]
N = len(M)
INK, CREAM = "#0b0b0b", "#f4f1ea"

def in_finder(r, c):
    return (r < 7 and c < 7) or (r < 7 and c >= N - 7) or (r >= N - 7 and c < 7)

# centre logo hole (in modules) – H level tolerates this easily (~6% of area)
HOLE = 9 if N % 2 else 10
h0 = (N - HOLE) // 2
def in_hole(r, c):
    return h0 - 0 <= r < h0 + HOLE and h0 <= c < h0 + HOLE

def qr_svg(size_px, with_logo=True, bg=CREAM):
    q = 4  # quiet zone
    V = N + 2 * q
    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {V} {V}" width="{size_px}" height="{size_px}" shape-rendering="geometricPrecision">')
    s.append('''<defs>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#c9a15a"/><stop offset=".45" stop-color="#8f6524"/><stop offset="1" stop-color="#5e3f12"/></linearGradient>
  <linearGradient id="goldL" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#f6e7c1"/><stop offset=".55" stop-color="#d9b36c"/><stop offset="1" stop-color="#a87b33"/></linearGradient>
</defs>''')
    if bg:
        s.append(f'<rect width="{V}" height="{V}" rx="3" fill="{bg}"/>')
    # data modules: rounded squares
    d = []
    for r in range(N):
        for c in range(N):
            if not M[r][c] or in_finder(r, c) or (with_logo and in_hole(r, c)):
                continue
            x, y = c + q + 0.06, r + q + 0.06
            d.append(f'M{x+0.3:.2f},{y:.2f}h.28a.3,.3 0 0 1 .3,.3v.28a.3,.3 0 0 1 -.3,.3h-.28a.3,.3 0 0 1 -.3,-.3v-.28a.3,.3 0 0 1 .3,-.3z')
    s.append(f'<path fill="{INK}" d="{"".join(d)}"/>')
    # finder eyes: ink rounded ring + gold rounded centre
    for (fr, fc) in [(0, 0), (0, N - 7), (N - 7, 0)]:
        x, y = fc + q, fr + q
        s.append(f'<path fill="{INK}" fill-rule="evenodd" d="M{x+1.8},{y}h3.4a1.8,1.8 0 0 1 1.8,1.8v3.4a1.8,1.8 0 0 1 -1.8,1.8h-3.4a1.8,1.8 0 0 1 -1.8,-1.8v-3.4a1.8,1.8 0 0 1 1.8,-1.8z'
                 f'M{x+1+1.1},{y+1}h2.8a1.1,1.1 0 0 1 1.1,1.1v2.8a1.1,1.1 0 0 1 -1.1,1.1h-2.8a1.1,1.1 0 0 1 -1.1,-1.1v-2.8a1.1,1.1 0 0 1 1.1,-1.1z"/>')
        s.append(f'<rect x="{x+2}" y="{y+2}" width="3" height="3" rx=".85" fill="url(#gold)"/>')
    if with_logo:
        cx = cy = q + N / 2
        R = HOLE / 2 - 0.35
        s.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{INK}"/>')
        s.append(f'<circle cx="{cx}" cy="{cy}" r="{R-0.45}" fill="none" stroke="url(#goldL)" stroke-width=".14"/>')
        s.append(f'<text x="{cx}" y="{cy+0.25}" text-anchor="middle" font-family="Playfair Display" font-style="italic" font-weight="700" font-size="1.9" fill="url(#goldL)">Fix face</text>')
        s.append(f'<line x1="{cx-1.4}" y1="{cy+0.85}" x2="{cx+1.4}" y2="{cy+0.85}" stroke="url(#goldL)" stroke-width=".07"/>')
        s.append(f'<text x="{cx}" y="{cy+1.6}" text-anchor="middle" font-family="Inter Display" font-weight="600" font-size=".52" letter-spacing=".2" fill="#e9d4a3">AESTHETIC</text>')
    s.append('</svg>')
    return "\n".join(s)

open("fixface_qr.svg", "w").write(qr_svg(1200))

card = f'''<!doctype html><html><head><meta charset="utf-8"><title>Fix face QR</title>
<link rel="stylesheet" href="fonts/fonts.css">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1600px;height:2000px;background:#060606}}
.card{{position:relative;width:1600px;height:2000px;overflow:hidden;color:#fff;font-family:'Inter Display','Inter',sans-serif;
  background:radial-gradient(1100px 900px at 50% 46%,#1d160b 0%,#0b0906 55%,#050505 100%)}}
.frame{{position:absolute;inset:44px;border:2px solid rgba(217,179,108,.55);border-radius:28px}}
.frame2{{position:absolute;inset:58px;border:1px solid rgba(217,179,108,.22);border-radius:20px}}
.c{{position:absolute;left:0;right:0;text-align:center}}
.gold{{background:linear-gradient(135deg,#f6e7c1,#d9b36c 55%,#a87b33);-webkit-background-clip:text;background-clip:text;color:transparent}}
.brand{{top:150px;font-family:'Playfair Display',serif;font-style:italic;font-weight:700;font-size:190px;line-height:1.15}}
.rule{{top:395px;left:50%;width:520px;margin-left:-260px;height:3px;background:linear-gradient(90deg,transparent,#d9b36c,transparent)}}
.sub{{top:425px;font-weight:500;font-size:34px;letter-spacing:.55em;color:#e9d4a3;padding-left:.55em}}
.panel{{position:absolute;top:540px;left:50%;margin-left:-480px;width:960px;height:960px;border-radius:44px;padding:18px;
  background:linear-gradient(135deg,#f6e7c1,#d9b36c 50%,#a87b33);box-shadow:0 40px 120px rgba(0,0,0,.7),0 0 140px rgba(217,179,108,.18)}}
.panel svg{{display:block;width:924px;height:924px;border-radius:30px}}
.handle{{top:1560px;font-weight:600;font-size:64px;letter-spacing:.02em}}
.cta{{top:1680px;font-weight:400;font-size:38px;letter-spacing:.32em;color:rgba(255,255,255,.72);padding-left:.32em}}
.tag{{top:1780px;font-family:'Playfair Display',serif;font-style:italic;font-weight:700;font-size:46px}}
</style></head><body><div class="card">
<div class="frame"></div><div class="frame2"></div>
<div class="c brand gold">Fix face</div>
<div class="rule c"></div>
<div class="c sub">AESTHETIC</div>
<div class="panel">{qr_svg(924)}</div>
<div class="c handle gold">@fix.face.aesthetic</div>
<div class="c cta">SKAN ET · BİZİ İZLƏ</div>
<div class="c tag gold">Gözəlliyə dəyər qatırıq!</div>
</div></body></html>'''
open("qr_card.html", "w").write(card)
print("version", qr.version, "modules", N, "hole", HOLE)

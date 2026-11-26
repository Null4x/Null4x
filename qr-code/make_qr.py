"""Fix face brand QR -> fixface_qr.svg (QR only) + qr_card.html (branded card).
Colours, gradient and emblem are taken from fix_face_logo.svg."""
import re, segno

URL = "https://www.instagram.com/fix.face.aesthetic/"
qr = segno.make(URL, error="h", boost_error=False)
M = [list(r) for r in qr.matrix]
N = len(M)
INK, GOLD, PAPER = "#1E1E1C", "#C08329", "#FFFFFF"

# --- emblem paths straight from the logo file ---------------------------------
logo = open("fix_face_logo.svg", encoding="utf-8").read()
paths = re.findall(r'<path class="(fil\d)" d="([^"]+)"', logo)
def emblem_paths(grad_id):
    fill = {"fil1": INK, "fil2": f"url(#{grad_id})", "fil0": GOLD}
    return "".join(f'<path fill="{fill[c]}" fill-rule="evenodd" d="{d}"/>' for c, d in paths)
EMB_VB = "786.6 787.6 6878.2 6878.2"   # outer ring: centre 4225.68,4226.68  r 3439.07

def gold_grad(gid, x1="0", y1=".5", x2="1", y2=".5"):
    stops = [(0,"#CB984D"),(.07,"#CB984D"),(.19,"#EDD089"),(.30,"#F4E8D9"),(.40,"#DAB681"),
             (.62,"#C08329"),(.79,"#D5A055"),(.95,"#EABE81"),(1,"#EABE81")]
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'

def in_finder(r, c):
    return (r < 7 and c < 7) or (r < 7 and c >= N - 7) or (r >= N - 7 and c < 7)

C0 = (N - 1) / 2
HOLE_R = 5.6                       # circular logo hole radius in modules (~6% of symbol, H = 30%)
def in_hole(r, c):
    return (r - C0) ** 2 + (c - C0) ** 2 <= HOLE_R ** 2

def qr_svg(size_px, uid="q", bg=PAPER):
    q = 4
    V = N + 2 * q
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {V} {V}" width="{size_px}" height="{size_px}">',
         "<defs>", gold_grad(f"{uid}g"), gold_grad(f"{uid}eye", "0", "0", "1", "1"), "</defs>"]
    if bg:
        o.append(f'<rect width="{V}" height="{V}" fill="{bg}"/>')
    d = []
    for r in range(N):
        for c in range(N):
            if M[r][c] and not in_finder(r, c) and not in_hole(r, c):
                x, y = c + q + .06, r + q + .06
                d.append(f"M{x+.3:.2f},{y:.2f}h.28a.3,.3 0 0 1 .3,.3v.28a.3,.3 0 0 1-.3,.3h-.28a.3,.3 0 0 1-.3-.3v-.28a.3,.3 0 0 1 .3-.3z")
    o.append(f'<path fill="{INK}" d="{"".join(d)}"/>')
    for fr, fc in [(0, 0), (0, N - 7), (N - 7, 0)]:
        x, y = fc + q, fr + q
        o.append(f'<path fill="{INK}" fill-rule="evenodd" d="M{x+1.8},{y}h3.4a1.8,1.8 0 0 1 1.8,1.8v3.4a1.8,1.8 0 0 1-1.8,1.8h-3.4a1.8,1.8 0 0 1-1.8-1.8v-3.4a1.8,1.8 0 0 1 1.8-1.8z'
                 f'M{x+2.1},{y+1}h2.8a1.1,1.1 0 0 1 1.1,1.1v2.8a1.1,1.1 0 0 1-1.1,1.1h-2.8a1.1,1.1 0 0 1-1.1-1.1v-2.8a1.1,1.1 0 0 1 1.1-1.1z"/>')
        o.append(f'<rect x="{x+2}" y="{y+2}" width="3" height="3" rx=".8" fill="{GOLD}"/>')
    cx = q + C0 + .5
    es = 2 * (HOLE_R - .55)
    o.append(f'<svg x="{cx-es/2}" y="{cx-es/2}" width="{es}" height="{es}" viewBox="{EMB_VB}">{emblem_paths(uid+"g")}</svg>')
    o.append("</svg>")
    return "\n".join(o)

open("fixface_qr.svg", "w", encoding="utf-8").write(qr_svg(1200))

emblem_big = (f'<svg viewBox="{EMB_VB}" width="330" height="330"><defs>{gold_grad("eg")}</defs>'
              f'{emblem_paths("eg")}</svg>')

card = f'''<!doctype html><html lang="az"><head><meta charset="utf-8"><title>Fix face QR</title>
<link rel="stylesheet" href="fonts/fonts.css">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1600px;height:2000px}}
.card{{position:relative;width:1600px;height:2000px;overflow:hidden;color:{INK};font-family:'Montserrat',sans-serif;
  background:radial-gradient(1200px 1000px at 50% 40%,#ffffff 0%,#fbf7f0 55%,#f3ebdd 100%)}}
.frame{{position:absolute;inset:44px;padding:3px;border-radius:30px;
  background:linear-gradient(135deg,#CB984D,#EDD089 19%,#F4E8D9 30%,#C08329 62%,#EABE81);
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude}}
.frame2{{position:absolute;inset:60px;border:1px solid rgba(192,131,41,.35);border-radius:20px}}
.c{{position:absolute;left:0;right:0;text-align:center}}
.gold{{background:linear-gradient(90deg,#CB984D 0%,#EDD089 19%,#F4E8D9 30%,#DAB681 40%,#C08329 62%,#D5A055 79%,#EABE81 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}}
.emb{{top:110px;display:flex;justify-content:center}}
.word{{top:452px;font-family:'Cinzel',serif;font-weight:600;font-size:112px;letter-spacing:.04em;line-height:1;color:{GOLD}}}
.subrow{{top:590px;display:flex;justify-content:center;align-items:center;gap:26px}}
.subrow i{{display:block;width:70px;height:3px;background:{GOLD}}}
.subrow span{{font-weight:400;font-size:33px;letter-spacing:.06em;color:{GOLD}}}
.panel{{position:absolute;top:690px;left:50%;margin-left:-410px;width:820px;height:820px;border-radius:40px;padding:10px;
  background:linear-gradient(135deg,#CB984D,#EDD089 19%,#F4E8D9 30%,#DAB681 40%,#C08329 62%,#D5A055 79%,#EABE81);
  box-shadow:0 30px 80px rgba(110,72,20,.18),0 6px 18px rgba(110,72,20,.12)}}
.panel svg{{display:block;width:800px;height:800px;border-radius:31px}}
.handle{{top:1580px;font-weight:600;font-size:60px;letter-spacing:.01em}}
.cta{{top:1688px;display:flex;justify-content:center;align-items:center;gap:22px;font-weight:500;font-size:32px;letter-spacing:.3em;color:{GOLD}}}
.cta b{{display:block;width:10px;height:10px;transform:rotate(45deg);background:{GOLD}}}
.tag{{top:1790px;font-family:'Montserrat',sans-serif;font-weight:400;font-size:40px;letter-spacing:.04em;color:#6b6457}}
</style></head><body><div class="card">
<div class="frame"></div><div class="frame2"></div>
<div class="c emb">{emblem_big}</div>
<div class="c word">FIX FACE</div>
<div class="c subrow"><i></i><span>AESTHETIC SOLUTIONS</span><i></i></div>
<div class="panel">{qr_svg(800, "c")}</div>
<div class="c handle">@fix.face.aesthetic</div>
<div class="c cta"><span>SKAN ET</span><b></b><span>BİZİ İZLƏ</span></div>
<div class="c tag">Gözəlliyə dəyər qatırıq!</div>
</div></body></html>'''
open("qr_card.html", "w", encoding="utf-8").write(card)
print("version", qr.version, "modules", N, "paths", len(paths))

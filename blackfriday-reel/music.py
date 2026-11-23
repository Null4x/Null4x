# Original synthesized 120 BPM track for the reel (21 s)
import numpy as np, wave
SR=44100; DUR=21.0; N=int(SR*DUR); t=np.arange(N)/SR
out=np.zeros((N,2))
rng=np.random.default_rng(3)
def add(sig,start,gain=1.0,pan=0.0):
    i=int(start*SR); j=min(N,i+len(sig))
    if j<=i: return
    s=sig[:j-i]*gain
    out[i:j,0]+=s*(1-max(0,pan)); out[i:j,1]+=s*(1+min(0,pan))
def env(n,a,d):
    tt=np.arange(n)/SR; return np.minimum(1,tt/max(a,1e-4))*np.exp(-tt/d)
def kick():
    n=int(.45*SR); tt=np.arange(n)/SR
    f=45+110*np.exp(-tt*28); ph=2*np.pi*np.cumsum(f)/SR
    return np.tanh(2.2*np.sin(ph)*np.exp(-tt*7))
def clap():
    n=int(.25*SR); x=rng.standard_normal(n)
    x=np.diff(np.concatenate([[0],x]))
    e=env(n,.001,.07); return x*e*.5
def hat(open_=False):
    n=int((.18 if open_ else .05)*SR); x=rng.standard_normal(n)
    x=np.diff(np.diff(np.concatenate([[0,0],x])))
    return x*env(n,.0005,.06 if open_ else .015)*.12
def impact():
    n=int(2.5*SR); tt=np.arange(n)/SR
    f=30+90*np.exp(-tt*6); boom=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-tt*1.6)
    nz=rng.standard_normal(n); nz=np.convolve(nz,np.ones(30)/30,'same')*np.exp(-tt*3)
    return np.tanh(1.5*boom)+nz*.6
def riser(d):
    n=int(d*SR); tt=np.arange(n)/SR
    nz=rng.standard_normal(n); k=np.linspace(60,4,n).astype(int)
    sm=np.array([nz[max(0,i-k[i]):i+1].mean() for i in range(0,n)]) if n<1 else None
    # cheap rising filter: mix of smoothed noise and raw noise
    lo=np.convolve(nz,np.ones(40)/40,'same'); x=lo*(1-tt/d)+nz*(tt/d)*.5
    sw=np.sin(2*np.pi*np.cumsum(200+1800*(tt/d)**2)/SR)*.15
    return (x+sw)*(tt/d)**2
def whoosh(d=.5):
    n=int(d*SR); tt=np.arange(n)/SR; nz=np.convolve(rng.standard_normal(n),np.ones(12)/12,'same')
    return nz*np.sin(np.pi*tt/d)**2*.9
def bassnote(f,d):
    n=int(d*SR); tt=np.arange(n)/SR
    s=np.sin(2*np.pi*f*tt)+.35*np.sin(2*np.pi*2*f*tt)+.15*np.sign(np.sin(2*np.pi*f*tt))
    return np.tanh(1.4*s)*np.minimum(1,tt/.01)*np.exp(-tt*2.2)
def pad(freqs,d):
    n=int(d*SR); tt=np.arange(n)/SR; s=np.zeros(n)
    for f in freqs:
        for dt in (-.6,0,.6):
            s+=np.sin(2*np.pi*(f+dt)*tt+rng.random()*6)
    a=np.minimum(1,tt/.4)*np.minimum(1,(d-tt)/.4)
    return s*a/(len(freqs)*3)
def pluck(f,d=.35):
    n=int(d*SR); tt=np.arange(n)/SR
    return (np.sin(2*np.pi*f*tt)+.5*np.sin(2*np.pi*2*f*tt)+.2*np.sin(2*np.pi*3*f*tt))*np.exp(-tt*9)*.25

B=.5
chords=[(220,261.63,329.63),(174.61,220,261.63),(130.81,164.81,196),(196,246.94,293.66)]  # Am F C G
bass=[55,43.65,65.41,49]
arp=[[440,523.25,659.25,523.25],[349.23,440,523.25,440],[523.25,659.25,783.99,659.25],[392,493.88,587.33,493.88]]

# pads all the way (bars of 2s)
for bar in range(11):
    add(pad(chords[bar%4],2.05),bar*2,.22)
# impacts
for s,g in [(0.2,.9),(3.0,.5),(6.4,1.0),(14.5,.8),(17.0,1.0)]: add(impact(),s,g)
add(riser(1.4),5.0,.55); add(riser(1.0),13.5,.45); add(riser(.9),16.1,.4)
for s in [2.9,9.8,13.95]: add(whoosh(.45),s,.6)

beat=0
tb=0.0
while tb<19.0:
    b=int(round(tb/B))
    # intro 0-6: kick on every beat, light hats; drop 6.4-14: full; 14-17 full+; 17-19 sparse
    if tb<6.0:
        if tb>=1.0: add(kick(),tb,.7)
        add(hat(),tb+B/2,.6)
    elif 6.0<=tb<17.0:
        add(kick(),tb,.95)
        if b%2==1: add(clap(),tb,.6)
        add(hat(),tb+B/2,1); add(hat(),tb+B/4,.45); add(hat(),tb+3*B/4,.45)
        if b%4==3: add(hat(True),tb+B/2,.8)
        bar=int(tb//2)%4
        add(bassnote(bass[bar],B*.9),tb+B/2,.55)
        add(bassnote(bass[bar],B*.45),tb,.35)
    else:
        if b%2==0: add(kick(),tb,.6)
    # arp everywhere 2..19
    if tb>=2.0:
        bar=int(tb//2)%4
        for k in range(2):
            add(pluck(arp[bar][(b*2+k)%4]),tb+k*B/2,.5 if tb>=6 else .35,pan=.3 if k else -.3)
    tb+=B
# master: fade out tail, soft clip, normalize
fade=np.ones(N); fs=int(19.5*SR); fade[fs:]=np.linspace(1,0,N-fs)
out*=fade[:,None]
out=np.tanh(out*1.1); out/=np.abs(out).max()*1.05
w=wave.open('music.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((out*32767).astype(np.int16).tobytes()); w.close()
print('ok')

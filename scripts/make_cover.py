from PIL import Image, ImageDraw, ImageFont
S=3000; F="/usr/share/fonts/opentype/inter/"
BG=(10,25,46); RING=(77,163,232); ACC=(126,196,255); WHITE=(255,255,255); GOLD=(246,196,83); SOFT=(214,228,245)
im=Image.new("RGB",(S,S),BG); d=ImageDraw.Draw(im)
big=ImageFont.truetype(F+"InterDisplay-Black.otf",1900)
# measure R
bb=d.textbbox((0,0),"R",font=big); rw=bb[2]-bb[0]; rh=bb[3]-bb[1]
dot=300  # diameter of the full stop
gap=70
total=rw+gap+dot
x0=(S-total)//2-bb[0]; y0=330-bb[1]
baseline_y=y0+bb[3]  # bottom of R
cx=(S-total)//2+rw+gap+dot//2; cy=330+rh-dot//2
# ripples from the dot
for i,r in enumerate(range(dot//2+110, 3600, 120)):
    a=max(0.18,1-i*0.045); col=tuple(int(BG[k]+(RING[k]-BG[k])*a) for k in range(3))
    w=7 if i<6 else 5
    d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=col,width=w)
# clear behind R for legibility
d.text((x0,y0),"R",font=big,fill=WHITE)
d.ellipse([cx-dot//2,cy-dot//2,cx+dot//2,cy+dot//2],fill=ACC)
# bottom band
d.rectangle([0,2330,S,S],fill=BG)
d.line([(220,2380),(S-220,2380)],fill=(40,70,105),width=4)
t1=ImageFont.truetype(F+"InterDisplay-ExtraBold.otf",210)
t2=ImageFont.truetype(F+"Inter-Medium.otf",112)
t3=ImageFont.truetype(F+"Inter-Bold.otf",92)
def ctr(y,txt,font,fill,track=0):
    w=d.textlength(txt,font=font)+track*(len(txt)-1)
    x=(S-w)/2
    if not track: d.text((x,y),txt,font=font,fill=fill); return
    for ch in txt:
        d.text((x,y),ch,font=font,fill=fill); x+=d.textlength(ch,font=font)+track
ctr(2450,"RIPPLE DAILY",t1,WHITE,track=24)
ctr(2700,"India's markets in under 10 minutes",t2,SOFT)
ctr(2840,"S × P  ·  10 STORIES  ·  EVERY MORNING",t3,GOLD,track=6)
im.save("cover.jpg",quality=90,optimize=True,progressive=False)
im.resize((1000,1000)).save("preview.png")

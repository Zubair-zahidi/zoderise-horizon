"""Export the authored Z monogram into antialiased PNG/Windows icon sizes."""
from pathlib import Path
from PIL import Image, ImageDraw

ASSETS=Path(__file__).resolve().parent/'assets'
SCALE=4
N=1024*SCALE
im=Image.new('RGBA',(N,N))
mask=Image.new('L',(N,N))
box=lambda xy:tuple(round(v*SCALE) for v in xy)
ImageDraw.Draw(mask).rounded_rectangle(box((28,28,996,996)),radius=224*SCALE,fill=255)
bg=Image.new('RGBA',(N,N)); d=ImageDraw.Draw(bg)
for y in range(N):
    t=y/(N-1)
    color=tuple(round(a+(b-a)*t) for a,b in zip((32,50,76),(8,14,27)))+(255,)
    d.line((0,y,N,y),fill=color)
im.paste(bg,(0,0),mask)
ImageDraw.Draw(im).rounded_rectangle(box((48,48,976,976)),radius=206*SCALE,outline=(70,85,107,255),width=4*SCALE)
zm=Image.new('L',(N,N))
ImageDraw.Draw(zm).polygon([box(p) for p in [(260,264),(758,264),(758,362),(446,660),(758,660),(758,760),(260,760),(260,662),(574,364),(260,364)]],fill=255)
gold=Image.new('RGBA',(N,N));g=ImageDraw.Draw(gold)
for y in range(N):
    t=max(0,min(1,(y/SCALE-264)/496))
    c=tuple(round(a+(b-a)*t) for a,b in zip((255,240,198),(185,137,66)))+(255,)
    g.line((0,y,N,y),fill=c)
im.paste(gold,(0,0),zm)
d=ImageDraw.Draw(im)
pts=[]
for i in range(160):
    t=i/159
    pts.append(box(((1-t)**2*690+2*(1-t)*t*780+t*t*821,(1-t)**2*198+2*(1-t)*t*206+t*t*274)))
d.line(pts,fill=(137,196,223,255),width=16*SCALE,joint='curve')
for x,y in [pts[0],pts[-1]]:
    d.ellipse((x-8*SCALE,y-8*SCALE,x+8*SCALE,y+8*SCALE),fill=(137,196,223,255))
d.ellipse(box((818,294,842,318)),fill=(180,222,239,255))
im=im.resize((1024,1024),Image.Resampling.LANCZOS)
im.save(ASSETS/'zoderise-icon.png')
im.save(ASSETS/'zoderise-icon.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('PNG and seven-resolution ICO exported.')

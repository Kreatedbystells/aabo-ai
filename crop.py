
import glob, os
from PIL import Image, ImageChops
for p in sorted(glob.glob("artifacts/figs/*.png")):
    im = Image.open(p).convert("RGB")
    bg = Image.new("RGB", im.size, (255,255,255))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        pad = 24
        x0,y0,x1,y1 = bbox
        x0,y0 = max(0,x0-pad), max(0,y0-pad)
        x1,y1 = min(im.width,x1+pad), min(im.height,y1+pad)
        im.crop((x0,y0,x1,y1)).save(p)
    print(os.path.basename(p), Image.open(p).size)

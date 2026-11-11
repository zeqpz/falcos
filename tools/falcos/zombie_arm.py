"""PREMIUM's window (owner, 2026-11-10: "make him holding an arm"): the zombie customer's open hand holds a severed
cartoon zombie arm - green, no blood. Run after remove_smoke.py (which rewrites plate_zombie.png from its original).

    .venv/bin/python tools/falcos/zombie_arm.py

The edit was made on a 480 x 480 crop of the 4K plate (art/falcos/work/zarm/crop.png, sent at 1024:
art/falcos/raw/zombie_arm.png); only what changed inside a box round his hand is blended back, with a soft edge.
Then frontend/assets/scene/plate_zombie.webp is written at full size for compress_assets.py to shrink (+ its _m twin).
"""
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOX = (3230, 960, 3710, 1440)
HAND = (3330, 1140, 3590, 1320)
plate_p = os.path.join(ROOT, 'art', 'falcos', 'scene', 'plate_zombie.png')
plate = Image.open(plate_p).convert('RGB')
w, h = BOX[2] - BOX[0], BOX[3] - BOX[1]
edit = Image.open(os.path.join(ROOT, 'art', 'falcos', 'raw', 'zombie_arm.png')).convert('RGB').resize((w, h), Image.LANCZOS)
region = plate.crop(BOX)
diff = np.abs(np.asarray(edit, np.int16) - np.asarray(region, np.int16)).max(axis=2) > 36
diff = ndimage.binary_opening(diff, iterations=1)
inbox = np.zeros_like(diff); inbox[HAND[1] - BOX[1]:HAND[3] - BOX[1], HAND[0] - BOX[0]:HAND[2] - BOX[0]] = True
m = ndimage.binary_closing(diff & inbox, iterations=4)
m = ndimage.binary_fill_holes(ndimage.binary_dilation(m, iterations=6)) & inbox
mask = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
region.paste(edit, (0, 0), mask)
plate.paste(region, BOX[:2])
plate.save(plate_p)
plate.save(os.path.join(ROOT, 'frontend', 'assets', 'scene', 'plate_zombie.webp'), 'WEBP', quality=95, method=4)
print('blended', int(m.sum()), 'px')

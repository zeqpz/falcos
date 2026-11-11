"""The board frame with a smaller FALCOS sign: art/falcos/raw/board_frame_sq.png -> board_frame_sq_small.png

    .venv/bin/python tools/falcos/shrink_topper.py [SCALE]      (default .6; then compress_assets.py)

The page is fitted to the screen's height, and the sign on top of the frame was a sixth of the frame's
height - room the board could not use (owner, 2026-11-10: "make it fill in the screen more"). This:
  * rebuilds the chrome bar under the sign from a plain stretch of it (a strip right of the right wing,
    tiled across: the bar is the same all along);
  * lifts the sign out (everything above the bar, plus whatever differs from the rebuilt bar: the plate,
    its wings and its shadow on the bar);
  * puts it back at SCALE, centred, its foot where it was - so it still overlaps the bar the same way.
compress_assets.py trims the result and measures its glass opening (frame_sq.webp / frame_sq.json).
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'art', 'falcos', 'raw')
SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else .6

src = Image.open(os.path.join(RAW, 'board_frame_sq.png')).convert('RGBA')
a = np.array(src).astype(np.int16)
H, W = a.shape[:2]
A = a[..., 3]

# the bar: its top edge (first solid row at the plain strip) and the foot of its neon glow
STRIP = (1700, 1740)
col = A[:, STRIP[0]]
bar_top = int(np.argmax(col > 40))
bar_bot = bar_top + int(np.argmax(col[bar_top:] < 2)) + 4
# the sign's span: what is solid above the bar
above = A[:bar_top] > 40
xs = np.where(above.any(axis=0))[0]
sx0, sx1 = int(xs.min()) - 8, int(xs.max()) + 9
sy0 = int(np.argmax(above.any(axis=1)))

# the bar rebuilt under the sign: the plain strip tiled across, nothing above the bar
bar = a.copy()
# one column, averaged over the strip, stretched across (a tiled strip showed its seams)
# over the bar's whole straight run, faded into the original over FADE px at each end (no seam)
column = a[bar_top:bar_bot, STRIP[0]:STRIP[1]].mean(axis=1)
RUN, FADE = (230, 1820), 160
k = np.clip(np.minimum(np.arange(W) - RUN[0], RUN[1] - np.arange(W)) / FADE, 0, 1)[None, :, None]
bar[bar_top:bar_bot] = (a[bar_top:bar_bot] * (1 - k) + column[:, None, :] * k).round().astype(np.int16)
bar[:bar_top, sx0:sx1] = 0

# the sign: everything above the bar, plus what differs from the rebuilt bar (the plate, wings, shadow)
diff = np.abs(a - bar).max(axis=2)
m = np.zeros((H, W), np.uint8)
m[:bar_top, sx0:sx1] = 255
# in the bar's rows the sign is what its black outline closes off: flood the bar from the region's sides
# and foot through everything that is not outline - what the flood cannot reach is the plate and the wings
# (and of that, only what differs from the plain bar: the bar's own outline stays with the bar)
from scipy import ndimage
rgb = a[bar_top:bar_bot, sx0:sx1, :3].astype(np.float32)
luma = rgb @ np.array([.299, .587, .114], np.float32)
wall = (luma < 60) & (A[bar_top:bar_bot, sx0:sx1] > 160)
lab, _ = ndimage.label(~wall)
edge = np.unique(np.concatenate([lab[:, 0], lab[:, -1], lab[-1, :]]))
outside = np.isin(lab, edge[edge > 0])
region = ndimage.binary_fill_holes(~outside & ~(wall & (diff[bar_top:bar_bot, sx0:sx1] <= 40)))
m[bar_top:bar_bot, sx0:sx1] = np.where(region, 255, 0)
# only what hangs together with the sign above the bar
lab, _ = ndimage.label(m > 0)
keep = np.unique(lab[bar_top - 1][lab[bar_top - 1] > 0])
m = np.where(ndimage.binary_fill_holes(np.isin(lab, keep)), 255, 0).astype(np.uint8)
mask = Image.fromarray(m).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1))
rows = np.where(np.array(mask).max(axis=1) > 128)[0]
sy1 = int(rows.max()) + 2
sign = src.copy()
sign.putalpha(Image.fromarray((np.array(src.getchannel('A')).astype(np.float32) * np.array(mask) / 255).astype(np.uint8)))
sign = sign.crop((sx0, sy0, sx1, sy1))

out = Image.fromarray(bar.clip(0, 255).astype(np.uint8))
small = sign.resize((round(sign.width * SCALE), round(sign.height * SCALE)), Image.LANCZOS)
cx = (sx0 + sx1) / 2
out.alpha_composite(small, (round(cx - small.width / 2), sy1 - small.height))
dst = os.path.join(RAW, 'board_frame_sq_small.png')
out.save(dst)
print(f'bar {bar_top}-{bar_bot}, sign x {sx0}-{sx1} y {sy0}-{sy1} -> x{SCALE}: top {sy1 - small.height} (was {sy0}); {dst}')

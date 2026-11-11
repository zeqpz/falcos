"""A wider board frame for landscape screens: art/falcos/raw/board_frame_sq_small.png -> board_frame_wide.png

    .venv/bin/python tools/falcos/widen_frame.py [ASPECT]     (default 1.4749; then compress_assets.py)

On a wide screen the board is as tall as it can be, so it grows sideways (owner, 2026-11-10: "make it
wider"): square 134 px cells there instead of 106 x 134, a grid of (7 x 144 + 36 + 12) / (5 x 134 + 34 + 12)
= 1.4749 wide to tall - the glass opening this frame is cut for. The sign keeps its size: the frame gets
wider by repeating one column of plain bezel on each side of it (top bar, glass, bottom bar), half the
extra width each side, so nothing is stretched. Phones (portrait) keep frame_sq and its 106 px cells.
"""
import os, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'falcos'))
from compress_assets import opening, RAW  # noqa: E402

ASPECT = float(sys.argv[1]) if len(sys.argv) > 1 else 1.4749
src = Image.open(os.path.join(RAW, 'board_frame_sq_small.png')).convert('RGBA')
bb = src.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox()
im = src.crop(bb)
W, H = im.size
o = opening(np.array(im.getchannel('A')))
ow, oh = (o[2] - o[0]) * W, (o[3] - o[1]) * H
extra = round(ASPECT * oh - ow)
assert extra > 0, f'already {ow / oh:.3f} wide'
# a plain column each side: well clear of the rounded corners and of the sign in the middle
a = np.array(im)
xl, xr = round(W * .16), round(W * .84)
left, right = extra // 2, extra - extra // 2
out = np.concatenate([a[:, :xl], np.repeat(a[:, xl:xl + 1], left, axis=1), a[:, xl:xr],
                      np.repeat(a[:, xr:xr + 1], right, axis=1), a[:, xr:]], axis=1)
dst = os.path.join(RAW, 'board_frame_wide.png')
Image.fromarray(out).save(dst)
o2 = opening(out[..., 3])
print(f'{W}x{H} opening {ow / oh:.3f} -> {out.shape[1]}x{H} opening '
      f'{(o2[2] - o2[0]) * out.shape[1] / ((o2[3] - o2[1]) * H):.4f} (+{extra}px); {dst}')

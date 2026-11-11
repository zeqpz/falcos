"""LUCKY PUMP's wheel pictures: each slice shows its result's cover art (owner, 2026-11-10: "make each triangle have
the cover photo of each symbol in it").

    .venv/bin/python tools/falcos/wheel_art.py      -> frontend/assets/wheel/{premium,midnight,none}.webp

A slice is a 40-degree wedge, about 3:4 tall (its wide end outward), so each picture is a 3:4 crop around what
reads best at the slice's wide end: PREMIUM's zombie cashier (its menu card, inside the gold border), MIDNIGHT
RUN's token over the night station (its banner), EMPTY's broken fuel gauge (the bust art). 480 x 640: the wheel
is drawn at most ~700 px across, a slice ~250 x 320 of it, so this is sharp at 2x.
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'art', 'falcos', 'raw')
OUT = os.path.join(ROOT, 'frontend', 'assets', 'wheel')
JOBS = {   # name: (raw file, crop box)
    'premium': ('menu_premium.png', (160, 230, 880, 1190)),
    'midnight': ('banner_midnight.png', (552, 0, 1368, 1088)),
    'none': ('menu_bust.png', (0, 0, 1024, 1365)),
}
os.makedirs(OUT, exist_ok=True)
for name, (src, box) in JOBS.items():
    im = Image.open(os.path.join(RAW, src)).convert('RGB').crop(box).resize((480, 640), Image.LANCZOS)
    dst = os.path.join(OUT, name + '.webp')
    im.save(dst, 'WEBP', quality=80, method=6)
    print(name, os.path.getsize(dst) // 1024, 'KB')

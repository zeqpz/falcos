"""Contact sheet of a rendered clip on the board colour: qa_sheet.py <ID> <clip> [every] -> art/falcos/qa/<ID>_<clip>.jpg"""
import sys, os, glob
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sid, clip = sys.argv[1], sys.argv[2]
every = int(sys.argv[3]) if len(sys.argv) > 3 else 2
files = sorted(glob.glob(os.path.join(ROOT, 'art/falcos/renders', sid, clip, '*.png')))[::every]
T = 220; cols = 8; rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * T, rows * T), (20, 18, 26)); d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert('RGBA'); im.thumbnail((T, T))
    x, y = (i % cols) * T, (i // cols) * T
    bg = Image.new('RGBA', im.size, (34, 30, 44, 255)); bg.alpha_composite(im)
    sheet.paste(bg.convert('RGB'), (x, y)); d.rectangle([x, y, x + T - 1, y + T - 1], outline=(60, 55, 70))
    d.text((x + 4, y + 4), os.path.basename(f)[:-4], fill=(200, 200, 200))
os.makedirs(os.path.join(ROOT, 'art/falcos/qa'), exist_ok=True)
out = os.path.join(ROOT, 'art/falcos/qa', f'{sid}_{clip}.jpg'); sheet.save(out, quality=88); print(out)

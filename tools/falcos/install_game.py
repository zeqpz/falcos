"""Copy the packed Falcos art (art/falcos/game, from pack_game.py) into the front end (frontend/assets).

  .venv/bin/python tools/falcos/install_game.py [ui] [scene] [intro] [menu] [symbols]

ui      - plates, logos, win lettering, digits, board frame, bonus banners. Lettering and plates that
          were packed on a big transparent canvas (a faint glow around them) are trimmed to what
          shows (alpha > ALPHA_CUT) plus a small margin, so the stylesheet's boxes fit them as before.
scene   - bonus_wall.webp (the 4K plate) and assets/scene/ (scene.json + overlays, read by scenefx.js)
intro   - assets/intro_letters/ replaced by the FALCOS letters (pieces.json is copied too; its numbers
          are also written into INTRO_SIZE / INTRO_PIECES / INTRO_DROP in index.html by hand)
menu    - the 7x5 board frame (frame_75.webp + .json), the bonus-buy menu (assets/menu: card art as is, the
          logos trimmed) and the load-in screen (assets/load: card art as is, the titles trimmed)
symbols - assets/sym/ (manifest + d10..d24 sheets) and assets/flat/ replaced by the 18 Falcos symbols;
          skipped while art/falcos/game/sym/manifest.json does not exist yet
No argument: all of them.
"""
import os, sys, shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G = os.path.join(ROOT, 'art', 'falcos', 'game')
F = os.path.join(ROOT, 'frontend', 'assets')
ALPHA_CUT, MARGIN = 10, 8

PLAIN = ['bonus_btn_text', 'bonus_btn_bg', 'bonus_panel', 'info_panel', 'feature_box', 'win_box', 'ui_box',
         'plate_grey', 'frame', 'title_logo']
TRIM = ['big_win', 'mega_win', 'xtreme_win', 'total_win', 'tier_bg', 'total_bg', 'banner_box', 'xbonus_text',
        'logo_fillup', 'logo_premium']


def trimmed(src, dst):
    im = Image.open(src).convert('RGBA')
    bb = im.getchannel('A').point(lambda v: 255 if v > ALPHA_CUT else 0).getbbox()
    if bb:
        x0, y0, x1, y1 = bb
        im = im.crop((max(0, x0 - MARGIN), max(0, y0 - MARGIN), min(im.width, x1 + MARGIN), min(im.height, y1 + MARGIN)))
    im.save(dst, quality=88, method=6)
    print('trim', os.path.basename(dst), im.size)


def copytree(src, dst, clean=True):
    if clean and os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    print('tree', os.path.relpath(dst, ROOT))


def ui():
    for n in PLAIN:
        shutil.copyfile(os.path.join(G, n + '.webp'), os.path.join(F, n + '.webp'))
        print('copy', n)
    for n in TRIM:
        trimmed(os.path.join(G, n + '.webp'), os.path.join(F, n + '.webp'))
    copytree(os.path.join(G, 'num'), os.path.join(F, 'num'))
    copytree(os.path.join(G, 'bonus'), os.path.join(F, 'bonus'))


def scene():
    shutil.copyfile(os.path.join(G, 'bonus_wall.webp'), os.path.join(F, 'bonus_wall.webp'))
    copytree(os.path.join(G, 'scene'), os.path.join(F, 'scene'))


def intro():
    copytree(os.path.join(G, 'intro_letters'), os.path.join(F, 'intro_letters'))


def menu():
    for n in ['frame_75.webp', 'frame_75.json']:
        shutil.copyfile(os.path.join(G, n), os.path.join(F, n))
        print('copy', n)
    for sub in ['menu', 'load']:
        os.makedirs(os.path.join(F, sub), exist_ok=True)
        for n in sorted(os.listdir(os.path.join(G, sub))):
            src, dst = os.path.join(G, sub, n), os.path.join(F, sub, n)
            if n.startswith(('logo_', 'title_')):
                trimmed(src, dst)
            else:
                shutil.copyfile(src, dst)
                print('copy', sub + '/' + n)


def symbols():
    if not os.path.exists(os.path.join(G, 'sym', 'manifest.json')):
        print('symbols: art/falcos/game/sym/manifest.json not there yet - skipped')
        return
    copytree(os.path.join(G, 'sym'), os.path.join(F, 'sym'))
    copytree(os.path.join(G, 'flat'), os.path.join(F, 'flat'))


if __name__ == '__main__':
    jobs = sys.argv[1:] or ['ui', 'scene', 'intro', 'menu', 'symbols']
    for j in jobs:
        {'ui': ui, 'scene': scene, 'intro': intro, 'menu': menu, 'symbols': symbols}[j]()

"""Background batch: Blender -b --factory-startup --python run_symbols.py -- H1,H2 [res] [clips] [--blend]"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import symanim

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ids = argv[0].split(',') if argv else list(symanim.P)
res = int(argv[1]) if len(argv) > 1 else 1024
clips = argv[2].split(',') if len(argv) > 2 and argv[2] != 'all' else None
out = os.path.join(symanim.ROOT, 'art', 'falcos', 'renders')
for sid in ids:
    t0 = time.time()
    symanim.build(sid, res)
    if '--blend' in argv:
        os.makedirs(os.path.join(symanim.ROOT, 'art', 'falcos', 'blend'), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(symanim.ROOT, 'art', 'falcos', 'blend', f'sym_{sid}.blend'))
    symanim.render(sid, out, clips)
    print(f'[sym] {sid} done in {time.time() - t0:.0f}s', flush=True)

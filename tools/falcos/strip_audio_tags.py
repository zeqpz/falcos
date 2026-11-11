"""Strip the text tags from every shipped sound (frontend/assets/*.ogg): some still carried the original game's name
in their comment header. The audio itself is untouched (mutagen rewrites only the Ogg comment page).

    .venv/bin/python tools/falcos/strip_audio_tags.py          (needs: pip install mutagen)

Each file keeps only an ENCODER line if it had one, and its vendor string (the encoder's label in the Opus/Vorbis
comment header, where the old name sat) becomes "falcos". AAC (ADTS) files carry no tags.
"""
import glob
import os
import mutagen

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'frontend', 'assets', '**', '*.ogg'), recursive=True)):
    f = mutagen.File(p)
    if f is None or f.tags is None:
        continue
    keep = {k: v for k, v in f.tags.items() if k.lower() == 'encoder'}
    vendor = getattr(f.tags, 'vendor', '')
    if set(k.lower() for k in f.tags.keys()) <= {'encoder'} and 'smuk' not in vendor.lower():
        continue
    f.tags.vendor = 'falcos'
    f.tags.clear()
    for k, v in keep.items():
        f.tags[k] = v
    f.save()
    n += 1
print('stripped', n, 'files')

"""Spectrogram contact sheet of every final take -> art/falcos/previews/sfx_spectrograms.png
(rows = sets, columns = takes; 0-12 kHz, 0-1.6 s on a shared scale; waveform overlaid)."""
import os, sys, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A

BUILD = os.path.join(A.RAW, 'build')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(A.ROOT, 'art', 'falcos', 'previews', 'sfx_spectrograms.png')
rep = json.load(open(os.path.join(BUILD, 'report.json')))
stems = [s for s in rep if len(sys.argv) < 3 or s in sys.argv[2:]]
fig, axs = plt.subplots(len(stems), 3, figsize=(15, 1.05 * len(stems)), squeeze=False, facecolor='#111')
for r, stem in enumerate(stems):
    for c in range(3):
        ax = axs[r, c]; ax.set_facecolor('#000')
        fs = rep[stem]['files']
        if c >= len(fs):
            ax.axis('off'); continue
        f = fs[c]
        x, sr = A.read_wav(os.path.join(BUILD, f['file']))
        m = x.mean(1)
        ax.specgram(m + 1e-9, NFFT=512, Fs=sr, noverlap=448, cmap='magma', vmin=-130, vmax=-40)
        ax.set_xlim(0, 1.6); ax.set_ylim(0, 12000)
        t = np.arange(len(m)) / sr
        ax.plot(t, 6000 + 5500 * m / 0.5, color='#4fd1c5', lw=.25, alpha=.7)
        ax.text(.01, .96, f"{f['file'][:-4]}", transform=ax.transAxes, color='w', fontsize=7, va='top')
        ax.text(.99, .96, f"{f['seconds']:.2f}s {f['lufs']:.1f} LUFS pk {f['peak_db']:.1f}", transform=ax.transAxes,
                color='#ddd', fontsize=6, va='top', ha='right')
        ax.set_xticks([0, .5, 1, 1.5]); ax.set_yticks([0, 4000, 8000])
        ax.tick_params(labelsize=5, colors='#888', length=2)
fig.suptitle('Falcos SFX finals - spectrograms 0-12 kHz, 0-1.6 s (waveform overlaid; full scale = 0.5)', color='w', fontsize=10)
plt.tight_layout(rect=(0, 0, 1, 1 - .5 / (1.05 * len(stems) + .5)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=80, facecolor='#111')
print(OUT)

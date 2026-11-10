"""Review sheet of the cleaned takes of some raw names (waveform + spectrogram, events marked).
  python look.py out.png name [name ...]"""
import os, sys, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A

rep = json.load(open(os.path.join(A.RAW, 'analysis.json')))
out, names = sys.argv[1], sys.argv[2:]
keys = [k for k in rep if rep[k]['name'] in names]
keys.sort(key=lambda k: (names.index(rep[k]['name']), rep[k]['take']))
fig, axs = plt.subplots(len(keys), 1, figsize=(14, 1.35 * len(keys)), squeeze=False)
for ax, k in zip(axs[:, 0], keys):
    x, sr = A.read_wav(os.path.join(A.RAW, 'clean', k + '.wav'))
    m = x.mean(1)
    if np.abs(m).max() > 0:
        ax.specgram(m, NFFT=1024, Fs=sr, noverlap=768, cmap='magma', vmin=-150, vmax=-40)
    ax.set_ylim(0, 10000); ax.set_xlim(0, 4.6)
    ax2 = ax.twinx(); ax2.plot(np.arange(len(m)) / sr, m / (np.abs(m).max() + 1e-9), color='c', lw=.3, alpha=.6); ax2.set_ylim(-1, 1); ax2.set_yticks([])
    r = rep[k]
    for a, b, p in r['events']:
        ax.axvspan(a, b, color='lime', alpha=.12)
    ax.text(.005, .75, f"{k} pk{r['raw_peak']} sp{r['speech']} {'REJ' if r['reject'] else ''}", transform=ax.transAxes, color='w', fontsize=8)
    ax.set_yticks([0, 5000]); ax.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig(out, dpi=70)

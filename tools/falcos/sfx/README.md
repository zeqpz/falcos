# Falcos sound effects pipeline

Makes the Falcos win and feature sounds: `frontend/assets/<stem>_<n>.wav` + `.ogg` (Opus) + `.aac` (AAC-LC, ADTS),
48 kHz stereo, 3 alike takes per set. The brief: soft, short, warm, musical, mixed under the music; no harsh
highs, no loud transients, no hiss, no voices.

Each sound is a short generated foley flavour (OpenRouter `bytedance-seed/seed-audio-1-0`) layered with a
numpy-synthesised musical part. Everything pitched is in **D major pentatonic** (D E F# A B), so wins and features
that overlap stay consonant. The Midnight Token uses B minor (B D F#), which sits inside the same notes. Clear-pitched
foley (the register bell, coin, drip, pop, jerry can) is nudged onto the nearest note in the scale (at most 1.6
semitones). If the game also nudges pitch at playback, the sounds drift off the scale; keep that nudge small for
these sets.

## Run it

Use the repo venv (`.venv`: numpy, scipy, soundfile, noisereduce, pyloudnorm, matplotlib, imageio-ffmpeg).

```
cd tools/falcos/sfx
python gen.py            # generate missing raw takes -> art/falcos/sfx_raw/<name>_<n>.pcm  (resumable, budget guard)
python gen.py --cost     # fill in each logged call's real cost (OpenRouter /generation) and print the total
python analyze.py        # clean + measure every take -> sfx_raw/clean/*.wav, sfx_raw/analysis.json (rejections)
python build.py          # layer, master and measure every set -> sfx_raw/build/*.wav + build/report.json
python sheet.py          # spectrogram contact sheet -> art/falcos/previews/sfx_spectrograms.png
python deliver.py        # copy to frontend/assets, encode .ogg/.aac, write art/falcos/sfx_manifest.json
```

`build.py <stem> ...` and `analyze.py <name> ...` rebuild only those sets or takes. `sheet.py out.png <stem> ...` draws
a sheet of only those sets. `look.py out.png <name> ...` draws the cleaned raw takes with their detected events, for
choosing excerpts.

## Files

- `orapi.py`: OpenRouter text-to-audio. The key is read from `~/.falcos/openrouter-key.txt` and never printed.
- `spec.py`: the prompts (all prefixed "Sound effect only, no voice, no music:"), the number of takes and a kind
  (foley / noisy / whoosh) that sets the cleaning filters.
- `gen.py`: 6 calls in parallel. Every call is logged to `art/falcos/sfx_raw/log.jsonl` (name, take, seconds,
  generation id, cost). It refuses to start a batch that would pass `SFX_BUDGET` (default $8).
- `audio.py`: the DSP. It reads the int16 24 kHz PCM and upsamples it to 48 kHz. Cleaning goes DC → high-pass
  (60-150 Hz by kind) → low-pass (6-9 kHz by kind, for warmth) → noise reduction profiled from the take's own bed
  (its quietest 50 ms windows outside the event, ignoring the digital-silence padding) → a hard gate to exact digital
  zero (12 dB over the residual bed, 150 ms bridge so a sound has no holes in it). It also holds the measures (LUFS,
  peak, tail floor, centroid, 6-12 kHz floor, speech score) and the mastering chain.
- `analyze.py`: cleans every take and rejects it for clipping, a noisy bed or speech-like content.
- `synth.py`: the musical layers. Soft FM bell (raised-cosine attack, the modulation dies before the tone,
  two slightly detuned voices), glass plink, filtered-saw pad, rising blip, neon hum (A2), noise poof (band-limited).
- `build.py`: one recipe per set (`SETS`: builder, target LUFS, fade-out, purpose). It takes excerpts from the
  cleaned takes (first strong onset, longest event, the end of a long event, or each event on its own). It scores
  them on completeness, length and speech, then picks the best and its two most alike siblings from different takes.
  Each excerpt ends on a 90 ms fade. Layers are balanced by loudness, and mastering does the rest: trim, a gentle
  -3 dB shelf at 6 kHz, 4 ms fade-in, a 30-80 ms fade-out, a loudness target, and a look-ahead limiter at -6.5 dBFS.
  `EXCLUDE` holds takes rejected by eye.
- `deliver.py`: copies the WAVs (16-bit) to `frontend/assets` and encodes Opus-in-Ogg (96 kb/s stereo, the
  bitrate `tools/encode_sfx.js` uses) and AAC-LC ADTS (128 kb/s stereo, as in `tools/encode_sfx_aac.js`). It uses the
  imageio-ffmpeg binary because the machine has no system ffmpeg and no node. If a codec's overshoot pushes a decoded
  peak over -6.2 dBFS, it re-encodes that copy slightly quieter. It never overwrites a file in `frontend/assets` that
  is not listed in `art/falcos/sfx_manifest.json`.

## Targets and checks

- Loudness: symbol wins -26 LUFS. Features -24, except mult_double -28 (it is tiny and fires many times at once),
  gauge_tick and midnight_land -25, and the pump grades rising -25 / -24.5 / -24 / -23. Bonus trigger -22.
  Sounds under 0.4 s are measured padded to one 0.5 s gating block.
- Peaks: under -6 dBFS in every format.
- Speech: the score is (share of energy at 300-3400 Hz) × (share of envelope modulation at 3-8 Hz) × syllable-train
  check × voicing (gliding periodicity at 80-400 Hz). Real speech from macOS `say` scores about 0.18-0.20. A take over
  0.08 is rejected. The manifest's `source_speech_score` is the worst raw take a set draws from; synth sets are 0.
- Hiss: the 6-12 kHz floor (the quietest 50 ms of that band, digital silence excluded) and the tail floor are reported.
  Every file ends in exact digital zero.

Raw takes, cleaned takes and builds live in `art/falcos/sfx_raw/`, which git ignores. They can be rebuilt with the
scripts above, and `gen.py` only pays for missing takes.

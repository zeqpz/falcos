"""Assemble every Falcos SFX set from the cleaned takes (art/falcos/sfx_raw/clean) and the synth layers,
master them and write art/falcos/sfx_raw/build/<stem>_<n>.wav + build/report.json.
  python build.py [stem ...]"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A
import synth as S
from audio import SR, hz

CLEAN = os.path.join(A.RAW, 'clean')
BUILD = os.path.join(A.RAW, 'build')
REP = json.load(open(os.path.join(A.RAW, 'analysis.json')))
_cache = {}


# ------------------------------------------------------------------ foley pieces
def clean(key):
    if key not in _cache:
        _cache[key] = A.read_wav(os.path.join(CLEAN, key + '.wav'))[0]
    return _cache[key]


EXCLUDE = {'keys_8'}     # by eye on the review sheet: two thin, far-apart jingles (choppy once normalised)


def takes(name):
    return sorted([k for k, r in REP.items() if r['name'] == name and not r['reject'] and k not in EXCLUDE],
                  key=lambda k: REP[k]['take'])


def _onset(x, a, b):
    """Precise onset inside event [a, b): first point within 30 dB of the event's peak, minus 4 ms."""
    d = A.envelope_db(x[a:b], SR, .002)
    i = int(np.argmax(d > d.max() - 30))
    return max(0, a + i - int(.004 * SR))


def _end_trim(seg, rel=-45):
    d = A.envelope_db(seg, SR, .005)
    on = np.nonzero(d > d.max() + rel)[0]
    return seg[:on[-1] + 1] if len(on) else seg


def tail_fade(seg, t=.09):
    """Every excerpt ends on a raised-cosine fade (over 90 ms or the last quarter): a sound still going
    where the window cuts it fades away instead of stopping dead."""
    seg = seg.copy()
    n = min(len(seg) // 4, int(t * SR))
    if n > 2:
        seg[-n:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, n)))[:, None]
    return seg


def _score(seg, full_after, ideal):
    """Higher is better: complete (decays inside the window), not speech-like, near the ideal length."""
    d = A.envelope_db(seg, SR, .01)
    end_lvl = d[-int(.01 * SR):].mean() - d.max() if len(seg) > SR // 50 else 0
    e_in = np.square(seg).sum(); e_all = np.square(full_after).sum() + 1e-20
    sp = A.speech_score(seg, SR)[0]
    s = 2.0 * (e_in / e_all) - abs(len(seg) / SR - ideal) / ideal - 8 * sp
    if end_lvl > -20:
        s -= .5
    return float(s)


def excerpts(name, maxdur, ideal=None, mode='main', min_peak_rel=-6, min_event=0.0):
    """Candidate excerpts from every good take of `name`.
    mode 'main': from the first event within min_peak_rel dB of the take's loudest, maxdur long.
    mode 'end':  the last maxdur seconds of the longest event (ends on its natural stop).
    mode 'each': every event on its own (trimmed to maxdur).
    mode 'longest': from the onset of the longest continuous event."""
    ideal = ideal or maxdur * .8
    out = []
    for k in takes(name):
        x = clean(k)
        ev = A.events(x, SR, -36, gap=.05, min_len=.02)
        if not ev:
            continue
        top = max(p for _, _, p in ev)
        if mode == 'each':
            for a, b, p in ev:
                if p < top - 12:
                    continue
                s = _onset(x, a, b)
                seg = _end_trim(x[s:min(b + int(.03 * SR), s + int(maxdur * SR))])
                out.append(dict(key=k, at=s / SR, seg=seg, score=_score(seg, x[s:b + int(.05 * SR)], ideal), peak=p))
            continue
        if mode == 'end':
            a, b, p = max(ev, key=lambda e: e[1] - e[0])
            s = max(a, b - int(maxdur * SR))
            seg = _end_trim(x[s:b + int(.03 * SR)])
            out.append(dict(key=k, at=s / SR, seg=seg, score=(b - a) / SR, peak=p))
            continue
        if mode == 'longest':          # the longest continuous event (a whoosh, not the click before it)
            a, b, p = max(ev, key=lambda e: e[1] - e[0])
            if (b - a) / SR < min_event:
                continue
        else:
            a, b, p = next(e for e in ev if e[2] >= top + min_peak_rel)
        s = _onset(x, a, b)
        seg = _end_trim(x[s:s + int(maxdur * SR)])
        out.append(dict(key=k, at=s / SR, seg=seg, score=_score(seg, x[s:s + int(2.5 * SR)], ideal), peak=p))
    for c in out:
        c['sp'] = A.speech_score(c['seg'], SR)[0]
        c['seg'] = tail_fade(c['seg'])
    return sorted([c for c in out if c['sp'] <= .08], key=lambda c: -c['score'])


def choose(cands, n=3, distinct=True):
    """Best candidate, then the most alike of the next best (duration and brightness), distinct takes."""
    if not cands:
        raise RuntimeError('no candidates')
    best = cands[0]
    cands_all = list(cands)
    feat = lambda c: (np.log(len(c['seg']) / SR + .02), np.log(A.centroid(c['seg'], SR) + 1))
    fb = feat(best)
    dmin = .6 * len(best['seg'])
    cands = [c for c in cands if len(c['seg']) >= dmin] or cands
    pool = [c for c in cands[1:10] if c['score'] > best['score'] - 1.2]
    pool.sort(key=lambda c: abs(feat(c)[0] - fb[0]) + .7 * abs(feat(c)[1] - fb[1]) - .15 * c['score'])
    pick, used = [best], {best['key']}
    for rnd in (0, 1, 2):          # 0: alike + distinct takes; 1: any length, distinct; 2: any
        src = pool + cands if rnd == 0 else (cands_all if rnd == 1 else cands_all)
        for c in src:
            if len(pick) == n:
                break
            if any(c is p for p in pick) or (rnd < 2 and c['key'] in used):
                continue
            pick.append(c); used.add(c['key'])
    return pick


def tune(seg, min_peaky=18, max_shift=1.6):
    """If the excerpt has a clear pitch, nudge it (by resampling) onto D major pentatonic."""
    f, pk = A.dominant_pitch(seg, SR)
    if pk < min_peaky:
        return seg, 0.0
    _, sh = A.penta_snap(f)
    if abs(sh) > max_shift:
        return seg, 0.0
    return A.pitch_shift_resample(seg, sh), float(sh)


# ------------------------------------------------------------------ mixing
def st(m, width=.35):
    return A.to_stereo(m, width) if m.ndim == 1 else m


def lvl(x, rel_db, ref=-24.0):
    """Scale a layer so its loudness is ref + rel_db LUFS (relative balance between layers)."""
    if np.abs(x).max() == 0:
        return x
    return x * 10 ** ((ref + rel_db - A.lufs(st(x), SR)) / 20)


def mix(layers, cap=None):
    """layers: [(signal, at_seconds, rel_db)] -> stereo sum, cut at cap seconds (with a fade)."""
    n = max(int(at * SR) + len(x) for x, at, _ in layers)
    out = np.zeros((n, 2))
    for x, at, rel in layers:
        y = lvl(st(x), rel)
        i = int(at * SR)
        out[i:i + len(y)] += y
    if cap and len(out) > cap * SR:
        out = out[:int(cap * SR)]
        nf = int(.08 * SR)
        out[-nf:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, nf)))[:, None]
    return out


def fade_in(x, t):
    n = int(t * SR); x = x.copy()
    x[:n] *= np.linspace(0, 1, n)[:, None] if x.ndim == 2 else np.linspace(0, 1, n)
    return x


def soft(x, f=6500):
    return A.lp(x, f, SR, 2)


# ------------------------------------------------------------------ the sets
WIN_CHIME = {   # notes, gap, tau, bright, sub (a soft low octave under it), chime level vs foley (dB), cap s
    'h1': (['D5', 'F#5', 'A5', 'D6'], .05, .32, .5, 'D4', 0, .95),
    'h2': (['A5', 'D6', 'F#6'], .045, .26, .42, None, -1, .85),
    'h3': (['F#5', 'B5'], .05, .24, .38, None, -1, .75),
    'h4': (['D5', 'A5'], .05, .22, .35, None, -1.5, .75),
    'l1': (['A5'], 0, .18, .28, None, -2, .62),
    'l2': (['B5'], 0, .18, .28, None, -2, .62),
    'l3': (['E5'], 0, .18, .28, None, -2, .62),
    'l4': (['F#5'], 0, .18, .28, None, -2, .62),
    'l5': (['D6'], 0, .18, .28, None, -2, .62),
}
WIN_FOLEY = {   # raw name(s), excerpt max seconds, foley level (dB), extra low-pass
    'h1': (['reg_bell', 'reg_drawer'], .85, 0, 8000),
    'h2': (['keys'], .65, 0, 8000),
    'h3': (['nozzle'], .5, -1, 7500),
    'h4': (['jerry'], .6, -1, 7500),
    'l1': (['soda'], .45, -2, 6500),
    'l2': (['slushie'], .5, -3, 6000),
    'l3': (['sizzle'], .45, -5, 5000),
    'l4': (['chips'], .45, -4, 5500),
    'l5': (['pop'], .3, -1, 6500),
}
TUNED = {'reg_bell', 'reg_drawer', 'coin', 'drip', 'pop', 'jerry'}


def win_set(sym):
    notes, gap, tau, bright, sub, crel, cap = WIN_CHIME[sym]
    names, mx, frel, lpf = WIN_FOLEY[sym]
    cands = sum((excerpts(n, mx) for n in names), [])
    cands.sort(key=lambda c: -c['score'])
    out = []
    for i, c in enumerate(choose(cands, 3)):
        fol = c['seg']
        sh = 0.0
        if REP[c['key']]['name'] in TUNED:
            fol, sh = tune(fol)
        fol = soft(fol, lpf)
        ch = S.chime(notes, gap=gap * (1 + .12 * (i - 1)), dur=cap, tau=tau, bright=bright, seed=10 * i + 1)
        if sub:
            ch = S.place(ch, S.bell(hz(sub), cap, tau=tau * 1.2, bright=.15, seed=i) * .45, 0)
        # the chime enters on the foley's main hit (a few ms in), never before it
        x = mix([(fol, 0, frel), (ch, .012, crel)], cap)
        out.append((x, dict(src=c['key'], at=round(c['at'], 3), tuned_st=round(sh, 2))))
    return out


def zippo_flick():
    clicks = [c for c in excerpts('zippo', .12, .06, mode='each') if len(c['seg']) < .15 * SR]
    clicks.sort(key=lambda c: -c['peak'])
    wh = excerpts('whoomp', .55, .5, mode='longest', min_event=.5)
    out = []
    for i in range(3):
        c, w = clicks[i * 2 % len(clicks)], wh[i]
        ws = fade_in(soft(w['seg'], 3500), .04)
        t = np.arange(len(ws)) / SR
        ws = ws * np.exp(-np.maximum(0, t - .06) / .16)[:, None]      # a puff that dies away, not a held roar
        x = mix([(soft(c['seg'], 7000), 0, -1), (ws, .07, -2)], .7)
        out.append((x, dict(src=[c['key'], w['key']])))
    return out


def zippo_burn():
    wh = choose(excerpts('whoomp', 1.0, .9, mode='longest', min_event=.6), 3)
    out = []
    for i, w in enumerate(wh):
        swell = S.pad([hz('D3'), hz('A3')], .9, att=.06, rel=.5, cutoff=500, saw=.25, seed=i)
        ws = soft(w['seg'], 4000)
        t = np.arange(len(ws)) / SR
        ws = ws * np.exp(-np.maximum(0, t - .3) / .22)[:, None]      # the spread blooms, then settles away
        x = mix([(ws, 0, 0), (swell, .02, -7)], 1.05)
        out.append((x, dict(src=w['key'])))
    return out


def strokes():
    c = [s for s in excerpts('scratch', .3, .2, mode='each') if .1 * SR < len(s['seg'])]
    return sorted(c, key=lambda s: -s['score'])


def scratch():
    sk = strokes()
    out = []
    for i in range(3):
        a, b, c = sk[i], sk[(i + 3) % len(sk)], sk[(i + 6) % len(sk)]
        L = [(soft(fade_in(s['seg'][:int(.22 * SR)], .01), 6000), t, g) for s, t, g in ((a, 0, 0), (b, .19, -1.5), (c, .38, -1))]
        x = mix(L, .64)
        out.append((x, dict(src=[a['key'], b['key'], c['key']])))
    return out


def scratch_reveal():
    out = []
    starts = [['A5', 'B5', 'D6', 'E6', 'F#6', 'A6'], ['B5', 'D6', 'E6', 'F#6', 'A6', 'B6'], ['A5', 'D6', 'E6', 'F#6', 'A6', 'D7']]
    for i, notes in enumerate(starts):
        sp = np.zeros(int(.9 * SR))
        for j, n in enumerate(notes):
            S.place(sp, S.bell(hz(n), .5, att=.004, tau=.16, bright=.25, warm=False, seed=i * 10 + j), j * .045, .9 ** j)
        pad = S.pad([hz('D5'), hz('A5'), hz('F#6')], .75, att=.12, rel=.4, cutoff=2600, saw=.2, seed=i)
        x = mix([(sp, 0, 0), (pad, 0, -9)], .85)
        out.append((x, dict(src='synth')))
    return out


def gold_scratch():
    sk = strokes()
    out = []
    for i in range(3):
        rng = np.random.default_rng(40 + i)
        sh = np.zeros(int(1.2 * SR))
        pool = ['D6', 'E6', 'F#6', 'A6', 'B6', 'D7']
        for j in range(9):
            t = .12 + j * .085 + rng.uniform(-.015, .015)
            S.place(sh, S.glass(hz(pool[rng.integers(len(pool))]), .35, tau=.1, seed=j), t, .55 + .45 * rng.random())
        pad = S.pad([hz('D5'), hz('A5'), hz('F#6')], 1.05, att=.25, rel=.45, cutoff=3000, saw=.25, seed=i)
        a, b = sk[i], sk[(i + 4) % len(sk)]
        x = mix([(soft(a['seg'][:int(.22 * SR)], 6000), 0, 0), (soft(b['seg'][:int(.22 * SR)], 6000), .17, -1.5),
                 (sh, 0, -2), (pad, .1, -6)], 1.25)
        out.append((x, dict(src=[a['key'], b['key']])))
    return out


def pump_roll():
    cs = excerpts('counter', 1.2, mode='end')
    cs = [c for c in cs if len(c['seg']) > 1.0 * SR][:3]
    out = []
    for i, c in enumerate(cs):
        rise = S.sweep(hz('D4'), hz('A4'), 1.15, att=.3, tau=3)
        x = mix([(fade_in(soft(c['seg'], 7000), .08), 0, 0), (rise, 0, -10)], 1.25)
        out.append((x, dict(src=c['key'], at=round(c['at'], 3))))
    return out


PUMP = {   # notes, gap, tau, pad notes, dur
    'regular': (['A4', 'D5'], .09, .28, None, .75),
    'plus': (['D5', 'F#5', 'A5'], .08, .3, None, .85),
    'premium': (['D5', 'F#5', 'A5', 'D6'], .075, .34, ['D4', 'A4'], 1.05),
    'fulltank': (['A4', 'D5', 'F#5', 'A5', 'D6', 'F#6'], .068, .4, ['D4', 'F#4', 'A4', 'D5'], 1.5),
}


def pump(grade):
    notes, gap, tau, padn, dur = PUMP[grade]
    out = []
    for i in range(3):
        g = gap * (1 + .08 * (i - 1))
        ch = S.chime(notes, gap=g, dur=dur, tau=tau, bright=.45, gains=[1] * len(notes), seed=100 + i * 7)
        L = [(ch, 0, 0)]
        if padn:
            end = g * (len(notes) - 1)
            L.append((S.pad([hz(n) for n in padn], dur - end, att=.1, rel=.45, cutoff=1500 if grade == 'premium' else 2200,
                            saw=.45 if grade == 'premium' else .6, seed=i), end, -6 if grade == 'premium' else -3))
            L.append((S.bell(hz('D3'), dur - end, tau=.6, bright=.1, seed=i), end, -8))
        if grade == 'fulltank':
            sp = np.zeros(int(.6 * SR))
            for j, n in enumerate(['A6', 'B6', 'D7']):
                S.place(sp, S.glass(hz(n), .3, tau=.12, seed=j + i), j * .06)
            L.append((sp, g * len(notes) + .05, -10))
        out.append((mix(L, dur), dict(src='synth')))
    return out


def mult_double():
    out = []
    for i, (a, b) in enumerate([('A5', 'D6'), ('B5', 'E6'), ('D6', 'F#6')]):
        x = S.blip_up(a, b, dur=.15, glide=.03, tau=.045, seed=i)
        out.append((mix([(x, 0, 0)]), dict(src='synth')))
    return out


def burn_clear():
    bs = choose(excerpts('burn', .6, .5), 3)
    out = []
    for i, b in enumerate(bs):
        poof = S.soft_noise(.3, 150, 800, att=.015, tau=.07, seed=i)
        x = mix([(soft(b['seg'], 5500), 0, 0), (poof, 0, -6)], .65)
        out.append((x, dict(src=b['key'])))
    return out


def drop_land():
    ds = [c for c in excerpts('drip', .25, .18, mode='each')]
    ds = choose(ds, 3) if ds else []
    out = []
    for i, (d, n) in enumerate(zip(ds, ['F#6', 'A6', 'B6'])):
        g = S.glass(hz(n), .3, tau=.075, seed=i)
        seg, sh = tune(d['seg'])
        x = mix([(soft(seg, 7500), 0, -3), (g, .004, 0)], .32)
        out.append((x, dict(src=d['key'], tuned_st=round(sh, 2))))
    return out


def drop_collect():
    ss = choose(excerpts('suck', .6, .55, mode='longest', min_event=.4), 3)
    out = []
    for i, s in enumerate(ss):
        seg = s['seg'].copy()
        nf = int(.15 * SR)
        seg[-nf:] *= np.linspace(1, 0, nf)[:, None] ** 1.5      # the suck hands over to the gloop
        gl = S.sweep(700, 250, .1, att=.006, tau=.05)
        t_end = len(seg) / SR
        x = mix([(fade_in(soft(seg, 5000), .02), 0, 0), (gl, max(.1, t_end - .06), -3)], .75)
        out.append((x, dict(src=s['key'])))
    return out


def clicks():
    c = [x for n in ('dial_click', 'ratchet') for x in excerpts(n, .08, .05, mode='each') if len(x['seg']) < .1 * SR]
    return sorted(c, key=lambda c: -c['peak'])


def gauge_refill():
    ck = sorted(clicks()[:12], key=lambda c: A.centroid(c['seg'], SR))   # neighbours in brightness = alike clicks
    out = []
    for i in range(3):
        L = []
        for j, n in enumerate(['D5', 'F#5', 'A5']):
            c = ck[(i * 3 + j) % len(ck)]
            L.append((S.norm(soft(c['seg'], 6500), .5), j * .13, -4))
            L.append((S.bell(hz(n), .4, tau=.13, bright=.3, seed=i * 3 + j), j * .13 + .004, -1))
        out.append((mix(L, .75), dict(src=[ck[(i * 3 + j) % len(ck)]['key'] for j in range(3)])))
    return out


def gauge_tick():
    ck = clicks()
    out = []
    for i in range(3):
        c = ck[(i + 1) % len(ck)]
        x = mix([(soft(c['seg'], 6000), 0, -3), (S.bell(hz('A4'), .35, tau=.1, bright=.2, seed=i), .004, 0)], .36)
        out.append((x, dict(src=c['key'])))
    return out


def token_land():
    cs = choose(excerpts('coin', .6, .5), 3)
    out = []
    for i, c in enumerate(cs):
        seg, sh = tune(c['seg'])
        ch = S.chime(['A5', 'D6'], gap=.03, dur=.7, tau=.26, bright=.4, seed=i)
        h = S.hum(hz('A2'), .6, att=.04, rel=.35)
        x = mix([(soft(seg, 7000), 0, 0), (ch, .01, -1), (S.norm(h, .6), 0, -12)], .72)
        out.append((x, dict(src=c['key'], tuned_st=round(sh, 2))))
    return out


def midnight_land():
    ts = choose(excerpts('thud', .5, .4), 3)
    out = []
    for i, t in enumerate(ts):
        pad = S.pad([hz('B2'), hz('F#3'), hz('D4')], 1.0, att=.05, rel=.6, cutoff=800, saw=.3, seed=i)
        low = S.bell(hz('B3'), 1.0, tau=.45, bright=.15, seed=i)
        top = S.glass(hz('F#5'), .6, att=.02, tau=.25, seed=i)
        x = mix([(soft(t['seg'], 3000), 0, 0), (pad, 0, -3), (low, .01, -6), (top, .12, -16)], 1.05)
        out.append((x, dict(src=t['key'])))
    return out


def bonus_trigger():
    out = []
    for i in range(3):
        g = .08 * (1 + .06 * (i - 1))
        arp = S.chime(['D5', 'F#5', 'A5', 'D6'], gap=g, dur=1.4, tau=.4, bright=.5, gains=[1, 1, 1, 1.1], seed=200 + i)
        t1 = g * 3
        brass = S.pad([hz(n) for n in ('D4', 'F#4', 'A4', 'D5')], 1.5 - t1, att=.09, rel=.5, cutoff=2200, saw=.6, seed=i)
        sub = S.bell(hz('D3'), 1.2, tau=.55, bright=.1, seed=i)
        sp = np.zeros(int(.7 * SR))
        for j, n in enumerate(['F#6', 'A6', 'D7']):
            S.place(sp, S.glass(hz(n), .35, tau=.14, seed=j + 3 * i), j * .07)
        x = mix([(arp, 0, 0), (brass, t1, -2), (sub, t1, -7), (sp, t1 + .12, -9)], 1.5)
        out.append((x, dict(src='synth')))
    return out


# stem -> (builder, target LUFS, fade-out s, purpose)
SETS = {f'sfx_win_{s}': (lambda s=s: win_set(s), -26, .07, p) for s, p in {
    'h1': 'H1 Cash Drawer cluster win: register bell + drawer, rich D-major chime (D5 F#5 A5 D6 + low D4)',
    'h2': 'H2 Gold Key cluster win: car keys jingle + 3-note chime (A5 D6 F#6)',
    'h3': 'H3 Pump Nozzle cluster win: nozzle click/gurgle + 2-note chime (F#5 B5)',
    'h4': 'H4 Jerry Can cluster win: metal can tap/slosh + 2-note chime (D5 A5)',
    'l1': 'L1 Energy Drink cluster win: can crack + fizz + single note A5',
    'l2': 'L2 Slushie cluster win: soft ice rattle + single note B5',
    'l3': 'L3 Hot Dog cluster win: small grill sizzle + single note E5',
    'l4': 'L4 Chips cluster win: chip bag crinkle + single note F#5',
    'l5': 'L5 Donut cluster win: soft bouncy pop + single note D6',
}.items()}
SETS.update({
    'sfx_zippo_flick': (zippo_flick, -24, .06, 'Zippo lands/activates: lid click + soft flame whoosh'),
    'sfx_zippo_burn': (zippo_burn, -24, .08, 'Zippo 3x3 burn: warm low whoomp of fire spreading'),
    'sfx_scratch': (scratch, -24, .05, 'Scratch Ticket scratching (3 short strokes, ~0.6 s)'),
    'sfx_scratch_reveal': (scratch_reveal, -24, .08, 'Scratch Ticket reveal: gentle pentatonic sparkle'),
    'sfx_gold_scratch': (gold_scratch, -24, .08, 'Gold Scratch Ticket: scratch strokes + golden shimmer'),
    'sfx_pump_roll': (pump_roll, -24, .06, 'Gas Pump grade roll: mechanical counter winding and stopping (~1.2 s)'),
    'sfx_pump_regular': (lambda: pump('regular'), -25, .07, 'Gas Pump grade REGULAR (x2/x4): 2-note bell'),
    'sfx_pump_plus': (lambda: pump('plus'), -24.5, .07, 'Gas Pump grade PLUS (x8/x16): 3-note bell'),
    'sfx_pump_premium': (lambda: pump('premium'), -24, .08, 'Gas Pump grade PREMIUM (x32/x64): 4-note arpeggio + soft pad'),
    'sfx_pump_fulltank': (lambda: pump('fulltank'), -23, .08, 'Gas Pump FULL TANK: arpeggio, held brass-like chord, sparkle'),
    'sfx_mult_double': (mult_double, -28, .03, 'Cell multiplier doubles: tiny soft tick-up (many overlap; mixed lower)'),
    'sfx_burn_clear': (burn_clear, -24, .06, 'Symbols burning away: soft crackle-poof'),
    'sfx_drop_land': (drop_land, -24, .04, 'Fuel Drop lands: glassy plink'),
    'sfx_drop_collect': (drop_collect, -24, .05, 'Fuel Drops collected: soft whoosh ending in a gloop'),
    'sfx_gauge_refill': (gauge_refill, -24, .06, 'Fuel gauge refills to 3 bars: three soft ratchet clicks rising D5 F#5 A5'),
    'sfx_gauge_tick': (gauge_tick, -25, .04, 'Fuel gauge loses a bar: soft click + low A4'),
    'sfx_token_land': (token_land, -24, .07, 'FALCOS Token lands: soft coin + chime + faint neon hum (A2)'),
    'sfx_midnight_land': (midnight_land, -25, .08, 'Midnight Token lands: low dark thud + B-minor pad (inside the key)'),
    'sfx_bonus_trigger': (bonus_trigger, -22, .08, 'Bonus triggered: tasteful 1.5 s fanfare in D'),
})


def main():
    os.makedirs(BUILD, exist_ok=True)
    rp = os.path.join(BUILD, 'report.json')
    rep = json.load(open(rp)) if os.path.exists(rp) else {}
    want = sys.argv[1:]
    for stem, (fn, tgt, fout, purpose) in SETS.items():
        if want and stem not in want:
            continue
        res = fn()
        files = []
        for i, (x, info) in enumerate(res, 1):
            y = A.master(x, SR, tgt, ceil_db=-6.5, fout=fout)
            p = os.path.join(BUILD, f'{stem}_{i}.wav')
            A.write_wav(p, y)
            m = A.measure(A.read_wav(p)[0])
            src = info.get('src')
            src = [src] if isinstance(src, str) else (src or [])
            sp = [REP[k]['speech'] for k in src if k in REP]
            m['speech'] = round(max(sp), 3) if sp else 0.0      # speech score of the generated source takes (synth: 0)
            files.append(dict(file=os.path.basename(p), **m, info=info))
            print(f"{stem}_{i:<2d} {m['seconds']:5.2f}s  {m['lufs']:6.1f} LUFS  pk {m['peak_db']:6.1f}  tail {m['tail_floor_db']:6.1f}  "
                  f"cen {m['centroid_hz']:5d}  hf {m['hf_floor_db']:6.1f}  sp {m['speech']:.3f}  {info}", flush=True)
        rep[stem] = dict(target=tgt, purpose=purpose, files=files)
    json.dump(rep, open(rp, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()

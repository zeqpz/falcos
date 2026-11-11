"""The game's five music cues: where each plays, what Lyria is asked for, and how build.py cuts it.

Falcos (owner, 2026-11-10: new music, nothing from the game it was forked from): a cartoon night gas station under
red neon - late-night retro synth-funk and synthwave, warm and grooving, never harsh, mixed under the soft sound
effects. Base and menu at 112 BPM in B minor, the bonus intro and the bonus at 128 in B minor (a night drive),
the TOTAL WIN at 112 in D major - all inside the D major / B minor notes the sound effects are pitched in
(tools/falcos/sfx: D major pentatonic). Lyria takes the tempo but not always the key: keep takes for their key.

  bars       the loop's length in bars (4/4)
  head       None: the cue is only the loop. A number: the take's opening plays once and the loop
             starts that many seconds in (snapped to the take's beat), cut from wherever after
             loop_from fits best; the opening keeps ringing under it for `tail` seconds (default 2)
  loop_from  seconds into the take before which no loop may start (past its intro)
  game_lufs  how loud the cue should sit in the game (the music bar at 100); sets its MUSIC level
"""

CUES = {
    "base": {
        "where": "the base game",
        "bpm": 112, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -25,
        "prompt": (
            "Instrumental only. Key: B minor. Tempo: 112 BPM. Late-night retro synth-funk for a cartoon gas station "
            "glowing under red neon at midnight. 112 BPM, B minor, 4/4. A relaxed but bouncy groove: tight dry kick "
            "and snare, soft shaker and closed hi-hats, a round slap-style synth bassline, warm analog Juno pads, "
            "clean funky muted guitar chops, a gentle electric piano playing Bm9 - Gmaj7 - Em9 - F#7sus4, and a "
            "smooth soft lead synth now and then. Cool, friendly, nocturnal and easy to listen to for a long time: "
            "background music for a slot game. Steady energy, no harsh sounds. Structure: [Short intro] -> [Main "
            "groove] -> [Main groove with keys and lead variations] -> [Main groove]. No breakdown, no fade-out."),
    },
    "menu": {
        "where": "the bonus buy menu",
        "bpm": 112, "bars": 16, "head": None, "loop_from": 0, "game_lufs": -27,
        "prompt": (
            "Instrumental only. Key: B minor. Tempo: 112 BPM. Mellow lounge synth-funk heard quietly inside a 24-hour "
            "gas station shop at night, the neon humming outside. 112 BPM, B minor, 4/4. Soft brushed drums and a "
            "gentle shaker, a warm round bass, dreamy Rhodes electric piano chords over Bm9 - Gmaj7 - Em9 - F#7sus4, "
            "airy pads, a little tape warmth. Calm, cosy and a bit mysterious, low energy but still grooving. The "
            "same relaxed groove from start to finish: no build-ups, no drops, no fade-out."),
    },
    "intro": {
        "where": "the bonus intro screen (waits for a click)",
        "bpm": 136, "bars": 8, "head": 5.6, "tail": .6, "loop_from": 10, "game_lufs": -24,
        "prompt": (
            "Instrumental only. Key: B minor. Tempo: 128 BPM. The announcement of a bonus round in a neon-lit retro "
            "racing game at night: 128 BPM synthwave in B minor. It opens instantly with a big warm impact - a "
            "gated-reverb snare hit, a deep synth bass boom and a bright stacked synth chord - then settles into a "
            "steady anticipation groove: a pulsing eighth-note analog bass on B, a soft driving kick, tom fills, "
            "a shimmering arpeggio and wide pads. Exciting, like headlights switching on before a night drive. "
            "Structure: [Impact] -> [Anticipation groove, steady and repeating]. No big drop, no fade-out."),
    },
    "bonus": {
        "where": "the bonus rounds (FILL UP, PREMIUM, MIDNIGHT RUN)",
        "bpm": 136, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -22.5,
        "prompt": (
            "Instrumental only. Key: B minor. Tempo: 128 BPM. A driving outrun synthwave anthem for a slot game's bonus "
            "round: a night drive past glowing gas stations. 128 BPM, B minor, 4/4. Punchy kick and big gated "
            "snare, sixteenth-note pulsing analog bass, bright stacked synth chords over Bm - G - D - A, a catchy "
            "soaring lead synth hook, shimmering arpeggios, crashes on the phrase changes. Exciting, upbeat and "
            "full of momentum, but smooth and never harsh. Full energy from the first bar: [Main section] -> [Main "
            "section with lead variations] -> [Main section]. No intro, no breakdown, no fade-out."),
    },
    "total": {
        "where": "the bonus's TOTAL WIN screen (waits for a click)",
        "bpm": 106, "bars": 8, "head": 8.6, "tail": 1.2, "loop_from": 15, "game_lufs": -23,
        "prompt": (
            "Instrumental only. Key: D major. Tempo: 112 BPM. A joyful celebration of a big win at a neon gas station, "
            "retro synth-funk with a disco lift. 112 BPM, D major, 4/4. It opens with a big happy hit - a crash, a "
            "brass-like synth stab and a sparkling glissando - then a feel-good groove: four-on-the-floor kick, "
            "claps, open hats, a bouncing octave synth bass, bright funky guitar, warm string pads over D - Bm7 - "
            "Gmaj7 - A, and sparkling bells. Uplifting, warm and victorious. Structure: [Celebration hit] -> "
            "[Joyful groove, steady and repeating]. No breakdown, no fade-out."),
    },
}

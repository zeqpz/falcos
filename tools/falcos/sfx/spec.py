"""What the generator is asked for. Each entry: raw name -> (prompt, takes, kind).
Every prompt is prefixed with PREFIX. The kind drives the high-pass / low-pass / event cut in clean.py."""

PREFIX = 'Sound effect only, no voice, no music: '

S = {
    # ---- symbol win foley ----
    'reg_bell':     ('an antique brass cash register, one warm soft bell ding and the cash drawer rolling open, close up, quiet room', 8, 'foley'),
    'reg_drawer':   ('a cash register drawer sliding open with a soft wooden thunk and a gentle bell ring, close up, quiet room', 6, 'foley'),
    'keys':         ('a small bunch of car keys gently jingling once in a hand, soft metallic jingle, close up, quiet room', 8, 'foley'),
    'nozzle':       ('a petrol pump nozzle trigger clicking once, followed by a small soft liquid gurgle, close up, quiet room', 8, 'foley'),
    'jerry':        ('a finger tapping a metal jerry can twice, then a little liquid slosh inside, soft, close up, quiet room', 8, 'foley'),
    'soda':         ('a soda can being opened, one crisp tab crack followed by a short soft fizz, close up, quiet room', 8, 'foley'),
    'slushie':      ('ice crystals rattling softly in a plastic slushie cup shaken once, gentle, close up, quiet room', 8, 'foley'),
    'sizzle':       ('a hot dog sausage briefly sizzling on a hot grill roller, short soft warm sizzle, close up', 6, 'noisy'),
    'chips':        ('a bag of potato chips crinkled softly once by a hand, short, close up, quiet room', 8, 'noisy'),
    'pop':          ('a single soft bouncy rubbery pop, like a gentle cork boop, cute and round, close up, quiet room', 8, 'foley'),
    # ---- features ----
    'zippo':        ('a metal zippo lighter lid flicked open with a click, the wheel struck, and a soft small flame whoosh, close up, quiet room', 8, 'foley'),
    'whoomp':       ('a soft warm low whoomp of a small fire igniting and spreading for a moment, gentle, muffled, no crackle', 8, 'whoosh'),
    'scratch':      ('a coin scratching a lottery scratch card, three quick short scratches, close up, quiet room', 8, 'noisy'),
    'counter':      ('an old mechanical gas pump counter, number wheels rolling and ticking quickly then stopping, close up, quiet room', 8, 'foley'),
    'burn':         ('a small piece of paper burning away quickly with a soft crackle and a gentle poof, close up, quiet room', 8, 'noisy'),
    'drip':         ('a single drop of liquid falling into a glass bottle, a soft glassy plink, close up, quiet room', 8, 'foley'),
    'suck':         ('a soft whoosh of liquid sucked up a tube ending in a gentle round gloop, close up, quiet room', 8, 'whoosh'),
    'ratchet':      ('a small dashboard dial winding up with three soft mechanical ratchet clicks, close up, quiet room', 8, 'foley'),
    'dial_click':   ('a single soft mechanical click of a small car dashboard dial, close up, quiet room', 6, 'foley'),
    'coin':         ('a single coin landing softly on a wooden counter and settling, close up, quiet room', 8, 'foley'),
    'thud':         ('a deep soft muffled thud of a heavy token landing on felt, low and dark, close up, quiet room', 6, 'foley'),
}


def jobs():
    for name, (p, n, kind) in S.items():
        yield name, PREFIX + p, n, kind

import pygame

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

SAMPLE_RATE = 44100
_enabled = True
_sounds = {}
_audio_ready = False


def init():
    global _audio_ready
    if not _HAS_NUMPY:
        _audio_ready = False
        return
    try:
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 256)
        pygame.mixer.init()
        _audio_ready = True
        _build_all()
    except Exception:
        _audio_ready = False


def set_enabled(value):
    global _enabled
    _enabled = value


def is_enabled():
    return _enabled


def toggle():
    global _enabled
    _enabled = not _enabled
    return _enabled


def _envelope(n, attack=0.005, release=0.08):
    env = np.ones(n)
    a = max(1, int(attack * SAMPLE_RATE))
    r = max(1, int(release * SAMPLE_RATE))
    a = min(a, n // 2) if n > 1 else 1
    r = min(r, n // 2) if n > 1 else 1
    env[:a] = np.linspace(0, 1, a)
    env[-r:] = np.linspace(1, 0, r)
    return env


def _tone(freq, duration, volume=0.4, wave='sine', attack=0.005, release=0.08, fm=None):
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        n = 1
    t = np.linspace(0, duration, n, endpoint=False)

    if fm is not None:
        f = np.linspace(freq * fm[0], freq * fm[1], n)
        phase = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
    else:
        phase = 2 * np.pi * freq * t

    if wave == 'sine':
        wav = np.sin(phase)
    elif wave == 'triangle':
        wav = 2 * np.abs(2 * (phase / (2*np.pi) - np.floor(phase / (2*np.pi) + 0.5))) - 1
    elif wave == 'square':
        wav = np.sign(np.sin(phase))
    elif wave == 'noise':
        wav = np.random.uniform(-1, 1, n)
    else:
        wav = np.sin(phase)

    wav *= _envelope(n, attack, release) * volume
    return wav


def _mix(*tracks):
    maxlen = max(len(t) for t in tracks)
    out = np.zeros(maxlen)
    for t in tracks:
        out[:len(t)] += t
    peak = np.max(np.abs(out))
    if peak > 1.0:
        out = out / peak * 0.95
    return out


def _concat(*tracks, gap=0.0):
    if gap > 0:
        silence = np.zeros(int(SAMPLE_RATE * gap))
        parts = []
        for t in tracks:
            parts.append(t)
            parts.append(silence)
        return np.concatenate(parts[:-1])
    return np.concatenate(tracks)


def _to_sound(mono_wave):
    arr = np.clip(mono_wave, -1, 1)
    stereo = np.column_stack([arr, arr])
    int_arr = (stereo * 32767).astype(np.int16)
    int_arr = np.ascontiguousarray(int_arr)
    return pygame.sndarray.make_sound(int_arr)


def _build_all():
    global _sounds
    _sounds = {}

    x1 = _tone(420, 0.045, volume=0.4, wave='triangle', attack=0.001, release=0.035)
    x2 = _tone(380, 0.045, volume=0.35, wave='triangle', attack=0.001, release=0.035)
    _sounds['place_x'] = _to_sound(_concat(x1, x2, gap=0.03))

    o1 = _tone(330, 0.11, volume=0.4, wave='sine', attack=0.005, release=0.09, fm=(1.0, 1.15))
    _sounds['place_o'] = _to_sound(o1)

    notes = [523.25, 659.25, 783.99, 1046.50]  # C5 E5 G5 C6
    parts = [_tone(f, 0.15, volume=0.4, wave='triangle', attack=0.005, release=0.12) for f in notes]
    _sounds['win'] = _to_sound(_concat(*parts, gap=0.01))

    l1 = _tone(392.00, 0.14, volume=0.32, wave='sine', attack=0.005, release=0.1)
    l2 = _tone(293.66, 0.2, volume=0.32, wave='sine', attack=0.005, release=0.16)
    _sounds['lose'] = _to_sound(_concat(l1, l2, gap=0.01))

    d1 = _tone(330, 0.16, volume=0.28, wave='sine', attack=0.01, release=0.13)
    d2 = _tone(294, 0.2, volume=0.28, wave='sine', attack=0.01, release=0.16)
    _sounds['draw'] = _to_sound(_concat(d1, d2, gap=0.02))

    buzz = _tone(130, 0.07, volume=0.22, wave='square', attack=0.002, release=0.055)
    _sounds['illegal'] = _to_sound(buzz)

    ui = _tone(440, 0.03, volume=0.22, wave='triangle', attack=0.001, release=0.025)
    _sounds['ui_click'] = _to_sound(ui)

    # GAME START
    s1 = _tone(440, 0.09, volume=0.28, wave='sine', attack=0.005, release=0.07)
    s2 = _tone(554.37, 0.09, volume=0.28, wave='sine', attack=0.005, release=0.07)
    s3 = _tone(659.25, 0.14, volume=0.28, wave='sine', attack=0.005, release=0.11)
    _sounds['start'] = _to_sound(_concat(s1, s2, s3, gap=0.01))


def play(name):
    if not _audio_ready or not _enabled:
        return
    snd = _sounds.get(name)
    if snd:
        try:
            snd.play()
        except Exception:
            pass

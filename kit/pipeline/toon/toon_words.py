"""Word timings for any voice track: python toon_words.py <reel> [voice.wav]
Bring your own voice (a recorded take or any text-to-speech), one script line per line of <reel>\\script.txt.
faster-whisper (free, local; GPU if available) times every word; the words are matched to the script, so captions show the
script's spelling and every word knows its line. Writes <reel>\\voice_words.json = [{word, start, end, line, i, interp}]
and <reel>\\voice_check.txt (what whisper heard, line by line: check names and numbers there)."""
import difflib
import json
import re
import sys
from pathlib import Path

from faster_whisper import WhisperModel

REEL = Path(sys.argv[1])
WAV = Path(sys.argv[2]) if len(sys.argv) > 2 else REEL / 'voice.wav'
norm = lambda w: re.sub(r'[^a-z0-9]', '', w.lower())


def main():
    lines = [ln.strip() for ln in (REEL / 'script.txt').read_text(encoding='utf-8-sig').splitlines() if ln.strip()]
    script = [(w, n + 1) for n, ln in enumerate(lines) for w in ln.split()]
    heard = None
    for dev, ct in (('cuda', 'float16'), ('cpu', 'int8')):   # the GPU needs CUDA 12 libraries; otherwise the CPU does it
        try:
            segs, _ = WhisperModel('small.en', device=dev, compute_type=ct).transcribe(str(WAV), language='en', word_timestamps=True, beam_size=5)
            heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
            break
        except Exception as e:
            print('whisper on', dev, 'failed:', str(e)[:80])
    # align script words to heard words; unmatched script words are spread over the gap around them
    sm = difflib.SequenceMatcher(a=[norm(w) for w, _ in script], b=[norm(w) for w, _, _ in heard], autojunk=False)
    t = [None] * len(script)
    for a, b, n in sm.get_matching_blocks():
        for j in range(n):
            t[a + j] = heard[b + j][1:]
    known = [i for i, x in enumerate(t) if x]
    if not known:
        sys.exit('no words matched: is script.txt the text that was spoken?')
    out = []
    for i, (w, ln) in enumerate(script):
        interp = t[i] is None
        if interp:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            s0 = t[lo][1] if lo is not None else 0.0
            s1 = t[hi][0] if hi is not None else s0 + .3 * (i - lo)
            span = (hi if hi is not None else i + 1) - (lo if lo is not None else -1)
            k = i - (lo if lo is not None else -1)
            st = s0 + (s1 - s0) * (k - 1) / span
            t[i] = (st, st + (s1 - s0) / span)
        out.append(dict(word=w, start=round(t[i][0], 3), end=round(t[i][1], 3), line=ln, i=i, interp=interp))
    (REEL / 'voice_words.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    rows = []
    for n, ln in enumerate(lines, 1):
        ws = [x for x in out if x['line'] == n]
        miss = [x['word'] for x in ws if x['interp']]
        rows.append(f"L{n} {ws[0]['start']:.2f}-{ws[-1]['end']:.2f}s  {ln}" + (f"   <- not heard: {' '.join(miss)}" if miss else ''))
    rows.append('\nwhisper heard: ' + ' '.join(w for w, _, _ in heard))
    (REEL / 'voice_check.txt').write_text('\n'.join(rows), encoding='utf-8')
    print('WORDS_OK', len(out), 'words,', sum(x['interp'] for x in out), 'not heard (see voice_check.txt)')


if __name__ == '__main__':
    main()

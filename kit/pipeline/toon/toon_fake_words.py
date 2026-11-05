"""Placeholder word timings from a script, one sentence per line of script.txt: python toon_fake_words.py <reel> [wps=3.8] -> <reel>\\voice_words.json. Replaced by align_lines once the voice exists."""
import json
import sys
from pathlib import Path

R = Path(sys.argv[1])
WPS = float(sys.argv[2]) if len(sys.argv) > 2 else 3.8
out, t = [], .05
for i, line in enumerate(x for x in (R / 'script.txt').read_text(encoding='utf-8').splitlines() if x.strip()):
    for w in line.split():
        out.append(dict(word=w, start=round(t, 3), end=round(t + 1 / WPS, 3), line=i))
        t += 1 / WPS
json.dump(out, open(R / 'voice_words.json', 'w', encoding='utf-8'))
print('WORDS_OK', len(out), 'words', round(t, 2), 's', int(t * 30), 'frames')

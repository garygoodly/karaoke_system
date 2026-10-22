"""Read optional experimental MFA word timings without changing the line timeline."""
import json
import re
from pathlib import Path


def load_word_timings(folder):
    root = Path(folder) / 'generated' / 'mfa'
    if not root.is_dir():
        return {}
    runs = sorted((p for p in root.iterdir() if p.is_dir() and re.fullmatch(r'full_song_run_\d+', p.name)),
                  key=lambda p: int(p.name.rsplit('_', 1)[-1]), reverse=True)
    for run in runs:
        path = run / 'lyrics_timeline_mfa.json'
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        found = {}
        for line in data.get('lines', []):
            try:
                line_id = int(line['line_id'])
                tokens = line.get('tokens') or []
                if line.get('reason') or line.get('warnings') or not tokens:
                    continue
                if any(not isinstance(t.get('text'), str) or not t['text'] or
                       not isinstance(t.get('start'), (int, float)) or
                       not isinstance(t.get('end'), (int, float)) or
                       not 0 <= t['start'] < t['end'] for t in tokens):
                    continue
                if any(tokens[i]['end'] > tokens[i + 1]['start'] + .02 for i in range(len(tokens) - 1)):
                    continue
                # Only use complete character coverage; partial results fall back to Line Mode.
                import re as _re
                han = ''.join(_re.findall(r'[\u3400-\u9fff]', line.get('text', '')))
                if han != ''.join(t['text'] for t in tokens):
                    continue
                found[line_id] = tokens
            except (KeyError, TypeError, ValueError):
                continue
        return found
    return {}

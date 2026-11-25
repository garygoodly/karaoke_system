"""Safe, optional line-only CTC timing overlay; never alters word timings."""
import json
import math
from pathlib import Path


def line_start_overrides(song_folder, timeline):
    path = Path(song_folder) / 'generated' / 'lyrics_timeline_hybrid_preview.json'
    if not path.is_file():
        return {}
    try:
        preview = json.loads(path.read_text(encoding='utf-8-sig'))
        meta = preview.get('ctc_preview_metadata', {})
        if meta.get('status') != 'preview_only':
            return {}
        approved = {int(x['line_id']) for x in meta.get('applied', [])}
        originals = {int(x['line_id']): x for x in timeline.get('lines', [])}
        result = {}
        for candidate in preview.get('lines', []):
            i = int(candidate['line_id'])
            old = originals.get(i)
            if i not in approved or old is None or old.get('text') != candidate.get('text'):
                continue
            start, end = float(candidate['start']), float(candidate['end'])
            old_start = float(old['start'])
            if not all(map(math.isfinite, (start, end, old_start))) or not 0 <= start < end:
                continue
            if abs(start - old_start) > 4 or abs(start - old_start) < 0.001:
                continue
            result[i] = start
        return result
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {}

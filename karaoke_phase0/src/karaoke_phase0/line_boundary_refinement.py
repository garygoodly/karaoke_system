"""Conservative line-onset proposals from separated-vocal pitch activity.

Never infer text identity from pitch; do not modify the original timeline.
"""
import json
from pathlib import Path


def voiced_runs(frames, min_periodicity=0.45, max_gap=0.12, min_duration=0.16):
    runs = []
    current = []
    for f in frames:
        t = float(f['time'])
        active = f.get('hz') is not None and float(f.get('periodicity', 0)) >= min_periodicity
        if active:
            if current and t - current[-1] > max_gap:
                if current[-1] - current[0] >= min_duration:
                    runs.append((current[0], current[-1]))
                current = []
            current.append(t)
        elif current and t - current[-1] > max_gap:
            if current[-1] - current[0] >= min_duration:
                runs.append((current[0], current[-1]))
            current = []
    if current and current[-1] - current[0] >= min_duration:
        runs.append((current[0], current[-1]))
    return runs


def propose_line_starts(timeline, pitch, max_shift=3.0, min_gap=0.28):
    runs = voiced_runs(pitch.get('frames', []))
    lines = timeline.get('lines', [])
    proposals = []
    for i, line in enumerate(lines):
        original = float(line['start'])
        # Pitch onsets are *candidates* only; avoid assigning a neighboring phrase.
        previous_start = float(lines[i-1]['start']) if i else -1e9
        next_start = float(lines[i+1]['start']) if i+1 < len(lines) else 1e9
        candidates = [s for s,e in runs if abs(s-original) <= max_shift
                      and s > previous_start+min_gap and s < next_start-min_gap]
        # A unique candidate close to the supplied timestamp is useful as a review hint.
        # Multiple candidates are ambiguous: never guess which one belongs to lyrics.
        chosen = candidates[0] if len(candidates)==1 else None
        proposals.append({'line_id':line.get('line_id',i), 'text':line.get('text',''),
                          'original_start':original,
                          'proposed_start':round(chosen,3) if chosen is not None else None,
                          'delta_seconds':round(chosen-original,3) if chosen is not None else None,
                          'status':'candidate_needs_listening' if chosen is not None else 'ambiguous_or_no_onset',
                          'candidate_count':len(candidates)})
    return {'status':'diagnostic_only','method':'pitch_onset_candidates_not_lyric_identification',
            'warning':'Do not apply automatically; pitch can include residual instruments and sustained syllables.',
            'proposals':proposals}


def build_report(timeline_path, pitch_path, output_path):
    timeline=json.loads(Path(timeline_path).read_text(encoding='utf-8'))
    pitch=json.loads(Path(pitch_path).read_text(encoding='utf-8'))
    result=propose_line_starts(timeline,pitch)
    out=Path(output_path)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

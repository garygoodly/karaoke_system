"""Conservative ASR-guided line-boundary proposals; never edits source timeline."""
import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def norm(s):
    return re.sub(r"[^\w\u3400-\u9fff]+", "", str(s)).lower()


def rank_lines(timeline, diagnostic, search_seconds=4.0):
    segments = diagnostic.get("asr_segments", [])
    matches = {int(m["line_id"]): m for m in diagnostic.get("line_matches", []) if "line_id" in m}
    proposals = []
    for line in timeline.get("lines", []):
        lid = int(line["line_id"])
        original = float(line["start"])
        target = norm(line.get("text", ""))
        match = matches.get(lid, {})
        candidates = []
        for seg in segments:
            start = float(seg["start"])
            if abs(start-original) > search_seconds or not target:
                continue
            stext = norm(seg.get("text", ""))
            if not stext:
                continue
            similarity = SequenceMatcher(None, target, stext).ratio()
            # Partial phrase matches can be useful, but not sufficient for automatic correction.
            containment = min(len(stext),len(target))/max(len(stext),len(target)) if (stext in target or target in stext) else 0.0
            lexical = max(similarity,containment)
            proximity = max(0.0,1.0-abs(start-original)/search_seconds)
            score = round(0.8*lexical+0.2*proximity,4)
            candidates.append({"asr_index":seg.get("index"),"start":start,"end":float(seg["end"]),"text":seg.get("text", ""),"lexical":round(lexical,4),"score":score})
        candidates.sort(key=lambda x:(-x["score"],abs(x["start"]-original)))
        best = candidates[0] if candidates else None
        runner = candidates[1] if len(candidates)>1 else None
        margin = round(best["score"]-runner["score"],4) if best and runner else None
        # Conservative: exact/near-exact text AND unique candidate. ASR time is still not a verified lyric onset.
        confident = bool(best and best["lexical"]>=0.9 and (runner is None or margin>=0.15) and match.get("similarity",0)>=0.8)
        proposals.append({"line_id":lid,"text":line.get("text", ""),"original_start":original,
          "proposed_start":best["start"] if confident else None,
          "delta_seconds":round(best["start"]-original,3) if confident else None,
          "status":"candidate_needs_listening" if confident else "ambiguous_or_weak_asr",
          "asr_match_similarity":match.get("similarity"),"margin":margin,
          "top_candidates":candidates[:3]})
    return {"status":"diagnostic_only","method":"asr_guided_line_candidates",
      "warning":"ASR boundaries are approximate; never apply without listening and reviewing repeated phrases.",
      "proposals":proposals}


def run(timeline_path, asr_path, output_path):
    timeline=json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    asr=json.loads(Path(asr_path).read_text(encoding="utf-8"))
    result=rank_lines(timeline,asr)
    out=Path(output_path);out.parent.mkdir(parents=True,exist_ok=True)
    if out.resolve() in (Path(timeline_path).resolve(),Path(asr_path).resolve()):
        raise ValueError("Output must not overwrite input")
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

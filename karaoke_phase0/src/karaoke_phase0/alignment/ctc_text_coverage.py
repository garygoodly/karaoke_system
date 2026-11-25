"""Conservative Mandarin CTC text coverage with auditable phonetic proxies.

A proxy is NOT an exact lyric transcription. Never auto-adopt a boundary
from a proxy-containing line without separate acoustic validation.
"""
from __future__ import annotations

# Explicit, reviewable approximations only; no arbitrary UNK replacement.
PHONETIC_PROXIES = {'冉': '然', '烬': '尽'}


def prepare_ctc_text(text, converter, tokenizer):
    normalized = ''.join(c for c in converter.convert(text) if c.isalnum())
    def valid(s):
        ids = tokenizer(s, add_special_tokens=False).input_ids
        return bool(ids) and tokenizer.unk_token_id not in ids and tokenizer.decode(ids, skip_special_tokens=True).replace(' ', '') == s, ids
    exact, ids = valid(normalized)
    if exact:
        return {'status': 'exact', 'text': normalized, 'ids': ids, 'proxies': []}
    changed = []
    chars = []
    for i, c in enumerate(normalized):
        if not valid(c)[0] and c in PHONETIC_PROXIES:
            proxy = PHONETIC_PROXIES[c]
            if valid(proxy)[0]:
                changed.append({'index': i, 'original': c, 'proxy': proxy})
                chars.append(proxy)
                continue
        chars.append(c)
    proxy_text = ''.join(chars)
    ok, ids = valid(proxy_text)
    if changed and ok:
        return {'status': 'phonetic_proxy_diagnostic_only', 'text': proxy_text, 'ids': ids, 'proxies': changed}
    return {'status': 'unsupported', 'text': normalized, 'ids': [], 'proxies': changed}

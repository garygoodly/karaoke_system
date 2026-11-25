import json
from pathlib import Path
from opencc import OpenCC
from transformers import AutoTokenizer

model = "wbbbbb/wav2vec2-large-chinese-zh-cn"
path = Path("songs/song-075151e6a644/generated/lyrics_timeline.json")

lines = json.loads(path.read_text(encoding="utf-8"))["lines"]
tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=False)
converter = OpenCC("t2s")

unknown = []
total_tokens = 0

for i, line in enumerate(lines):
    text = converter.convert(line["text"])
    ids = tokenizer(text, add_special_tokens=False).input_ids
    total_tokens += len(ids)

    for char in text:
        char_ids = tokenizer(char, add_special_tokens=False).input_ids
        if tokenizer.unk_token_id in char_ids:
            unknown.append((i, char))

print("Lines:", len(lines))
print("Tokens:", total_tokens)
print("Unknown:", len(unknown))
print("Examples:", unknown[:20])


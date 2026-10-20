import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from karaoke_phase0.core import parse_lyrics,_normalize

def test_txt(tmp_path):
 p=tmp_path/'x.txt';p.write_text('你好\n\n世界\n',encoding='utf8')
 assert [x['text'] for x in parse_lyrics(p)]==['你好','世界']

def test_lrc(tmp_path):
 p=tmp_path/'x.lrc';p.write_text('[ar:artist]\n[00:12.50]你好\n[00:13.25]世界\n',encoding='utf8')
 assert [x['hint_start'] for x in parse_lyrics(p)]==[12.5,13.25]

def test_normalize():
 assert _normalize('我 想，唱歌!')=='我想唱歌'

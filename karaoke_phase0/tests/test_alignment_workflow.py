import json
from pathlib import Path
import pytest
from karaoke_phase0.alignment_workflow import lyrics_path, align_song, read_timeline
from karaoke_phase0.lyrics_preview import render


def test_lyrics_path(tmp_path):
    (tmp_path/'lyrics.txt').write_text('我想唱歌',encoding='utf-8')
    assert lyrics_path(tmp_path).name=='lyrics.txt'
    (tmp_path/'lyrics.lrc').write_text('[00:01.00]我想唱歌',encoding='utf-8')
    with pytest.raises(ValueError): lyrics_path(tmp_path)


def test_missing_vocals(tmp_path):
    (tmp_path/'lyrics.txt').write_text('我想唱歌',encoding='utf-8')
    with pytest.raises(FileNotFoundError): align_song(tmp_path)


def test_preview_escapes_text(tmp_path):
    timeline={'status':'review_required','warnings':[{'reason':'test'}],
              'lines':[{'line_id':0,'start':1.,'end':2.,'text':'<script>','tokens':[]}]}
    out=render(timeline,tmp_path/'preview.html')
    page=out.read_text(encoding='utf-8')
    assert 'Lyrics Alignment QA' in page
    assert 'const DATA=' in page
    assert '<\\/script>' not in page # text is JSON encoded and escaped for embedding


def test_read_timeline(tmp_path):
    generated=tmp_path/'generated'
    generated.mkdir()
    (generated/'lyrics_timeline.json').write_text(json.dumps({'lines':[]}),encoding='utf-8')
    assert read_timeline(tmp_path)=={'lines':[]}

"""Safely change karaoke QA playback clocks to m:ss.xx, preserving seek behavior."""
from pathlib import Path
import argparse
import shutil

OLD_STAMP = "const stamp=t=>Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');"
NEW_STAMP = "const stamp=t=>{const n=Number.isFinite(t)?Math.max(0,t):0;const centis=Math.round(n*100);return Math.floor(centis/6000)+':'+String(Math.floor((centis%6000)/100)).padStart(2,'0')+'.'+String(centis%100).padStart(2,'0');};"
OLD_JUMP = "clock.textContent=next.toFixed(2)+'s';"
NEW_JUMP = "clock.textContent=stamp(next)+' / '+stamp(Number.isFinite(duration)?duration:0);"
OLD_SONG_TIME = "'Song time: '+t.toFixed(2)+'s · '+DATA.status"
NEW_SONG_TIME = "'Song time: '+stamp(t)+' · '+DATA.status"
MARKER = '/* KARAOKE_TIMESTAMP_MMSSCC_V1 */'

def apply(path: Path):
    source=path.read_text(encoding='utf-8')
    if MARKER in source:
        return 'already_applied'
    if source.count(OLD_STAMP)!=1:
        raise RuntimeError('Unknown player clock format; no changes made')
    if source.count('clock.textContent=stamp(instrumental.currentTime)')!=1:
        raise RuntimeError('Unknown player clock update; no changes made')
    if source.count(OLD_SONG_TIME)!=1:
        raise RuntimeError('Unknown song time display; no changes made')
    if source.count(OLD_JUMP)>1:
        raise RuntimeError('Unexpected duplicate jump clocks; no changes made')
    result=source.replace(OLD_STAMP,MARKER+'\n  '+NEW_STAMP,1)
    result=result.replace(OLD_SONG_TIME,NEW_SONG_TIME,1)
    result=result.replace(OLD_JUMP,NEW_JUMP)
    result=result.replace('<span id="playerClock">0:00</span>','<span id="playerClock">0:00.00</span>')
    backup=path.with_suffix(path.suffix+'.before_timestamp_format.bak')
    if backup.exists():
        raise RuntimeError('Backup already exists: '+str(backup))
    shutil.copy2(path,backup)
    try:
        path.write_text(result,encoding='utf-8')
    except BaseException:
        shutil.copy2(backup,path)
        raise
    return 'applied'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--file',type=Path,default=Path(__file__).resolve().parents[1]/'src/karaoke_phase0/lyrics_preview.py')
    args=parser.parse_args()
    print(apply(args.file))

if __name__=='__main__':main()

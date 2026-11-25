"""Incrementally move player clock updates from media timeupdate to a light 33ms timer."""
from pathlib import Path
import argparse
import shutil

MARKER = '/* KARAOKE_SMOOTH_CLOCK_30FPS_V1 */'
OLD = """  instrumental.addEventListener('timeupdate',()=>{
    sync();seek.value=instrumental.duration?String(100*instrumental.currentTime/instrumental.duration):'0';
    clock.textContent=stamp(instrumental.currentTime)+' / '+stamp(instrumental.duration||0);
  });"""
NEW = """  /* KARAOKE_SMOOTH_CLOCK_30FPS_V1 */
  const renderPlayerClock=()=>{
    const position=Number.isFinite(instrumental.currentTime)?instrumental.currentTime:0;
    const duration=Number.isFinite(instrumental.duration)?instrumental.duration:0;
    clock.textContent=stamp(position)+' / '+stamp(duration);
  };
  // Keep expensive media synchronization and seek updates at their existing cadence.
  instrumental.addEventListener('timeupdate',()=>{
    sync();seek.value=instrumental.duration?String(100*instrumental.currentTime/instrumental.duration):'0';
  });
  // Update text only. Do not redraw the lyric view, pitch canvas or run audio sync.
  const clockTimer=setInterval(renderPlayerClock,33);
  window.addEventListener('pagehide',()=>clearInterval(clockTimer),{once:true});
  for(const eventName of ['play','pause','seeked','loadedmetadata','durationchange','ended']){
    instrumental.addEventListener(eventName,renderPlayerClock);
  }
  seek.addEventListener('input',renderPlayerClock);
  renderPlayerClock();"""

def apply(path: Path):
    source=path.read_text(encoding='utf-8')
    if MARKER in source:
        return 'already_applied'
    if source.count(OLD)!=1:
        raise RuntimeError('Expected clock/timeupdate block not found exactly once; no changes made')
    if 'const stamp=' not in source or 'const clock=document.getElementById(\'playerClock\')' not in source:
        raise RuntimeError('Unknown player template; no changes made')
    updated=source.replace(OLD,NEW,1)
    backup=path.with_suffix(path.suffix+'.before_smooth_clock.bak')
    if backup.exists():
        raise RuntimeError(f'Backup exists: {backup}; no changes made')
    shutil.copy2(path,backup)
    try:
        path.write_text(updated,encoding='utf-8')
    except BaseException:
        shutil.copy2(backup,path)
        raise
    return 'applied'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--file',type=Path,default=Path(__file__).resolve().parents[1]/'src/karaoke_phase0/lyrics_preview.py')
    args=p.parse_args()
    print(apply(args.file))

if __name__=='__main__':
    main()

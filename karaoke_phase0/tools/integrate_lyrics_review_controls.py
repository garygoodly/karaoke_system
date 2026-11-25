"""Safely add +/-2s transport and compact lyrics display to existing QA HTML template."""
from pathlib import Path
import argparse
import shutil

MARKER = '/* KARAOKE_REVIEW_CONTROLS_V1 */'
SCRIPT = r'''/* KARAOKE_REVIEW_CONTROLS_V1 */
(function installReviewControls(){
  const controls=document.getElementById('playerControls');
  const lyric=document.getElementById('line');
  const modes=document.querySelector('.modes');
  if(!playerMode||!controls||!lyric||!modes)return;
  const clock=document.getElementById('playerClock');
  const seek=document.getElementById('seek');
  const jumpBy=(seconds)=>{
    const master=playback();
    if(!master)return;
    const current=Number.isFinite(master.currentTime)?master.currentTime:0;
    const duration=Number.isFinite(master.duration)?master.duration:Infinity;
    const next=Math.max(0,Math.min(duration,current+seconds));
    master.currentTime=next;
    if(playerMode && audio!==master)audio.currentTime=next;
    if(seek && Number.isFinite(duration) && duration>0)seek.value=String(100*next/duration);
    if(clock)clock.textContent=next.toFixed(2)+'s';
  };
  const addButton=(label,seconds)=>{
    const b=document.createElement('button');
    b.type='button';b.textContent=label;b.className='review-skip-button';
    b.addEventListener('click',()=>jumpBy(seconds));
    return b;
  };
  const play=document.getElementById('togglePlay');
  if(play){play.insertAdjacentElement('beforebegin',addButton('-2s',-2));
    play.insertAdjacentElement('afterend',addButton('+2s',2));}
  // Move (not clone) the existing lyric node, preserving its render updates.
  lyric.classList.add('review-inline-lyric');
  controls.appendChild(lyric);
  controls.insertAdjacentElement('afterend',modes);
})();'''
CSS = '''/* KARAOKE_REVIEW_CONTROLS_STYLE_V1 */
#playerControls .review-inline-lyric{flex-basis:100%;width:100%;margin:3px 0 0;min-height:42px;font-size:27px;line-height:1.35;text-align:center}
#playerControls .review-skip-button{background:#334155;min-width:56px}
#playerControls #playerClock{font-variant-numeric:tabular-nums;white-space:nowrap}
'''
ANCHOR = 'const playback=()=>playerMode?instrumental:audio;'

def apply(path:Path):
    source=path.read_text(encoding='utf-8')
    if MARKER in source:return 'already_applied'
    if source.count(ANCHOR)!=1 or source.count('</style>')!=1 or source.count('</script>')!=1:
        raise RuntimeError('Unknown template layout; no files modified')
    # Place after playback declaration so it can use playback(), but execute after all DOM nodes exist.
    modified=source.replace(ANCHOR,ANCHOR+'\n'+SCRIPT,1)
    modified=modified.replace('</style>',CSS+'</style>',1)
    backup=path.with_suffix(path.suffix+'.before_review_controls.bak')
    if backup.exists():raise RuntimeError('Backup already exists; no files modified: '+str(backup))
    shutil.copy2(path,backup)
    try:path.write_text(modified,encoding='utf-8')
    except BaseException:
        shutil.copy2(backup,path)
        raise
    return 'applied'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--file',type=Path,default=Path(__file__).resolve().parents[1]/'src/karaoke_phase0/lyrics_preview.py')
    args=p.parse_args()
    print(apply(args.file))
if __name__=='__main__':main()

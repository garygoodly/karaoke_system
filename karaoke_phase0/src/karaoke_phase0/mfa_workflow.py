"""Experimental MFA CLI workflow; never overwrites a song timeline."""
from pathlib import Path
import json
import re
import shutil
import subprocess
from .mfa_g2p import extend_dictionary


def run_benchmark(corpus, output, base_dictionary, mfa_exe, converter,
                  acoustic_model='mandarin_mfa', g2p_model='mandarin_taiwan_mfa',
                  extra_oovs=(), timeout=600):
    corpus, output = Path(corpus).resolve(), Path(output).resolve()
    base_dictionary = Path(base_dictionary).resolve()
    if not corpus.is_dir() or not base_dictionary.is_file():
        raise FileNotFoundError('Corpus or base dictionary not found')
    if output == corpus or corpus in output.parents and output.name == '':
        raise ValueError('Output must not be the source corpus')
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Output directory must be new or empty')
    clips = sorted(w for w in corpus.glob('*.wav') if w.with_suffix('.txt').is_file())
    if not clips:
        raise ValueError('No WAV/TXT pairs found')
    output.mkdir(parents=True, exist_ok=True)
    input_dir = output/'corpus'; input_dir.mkdir()
    texts = []
    for wav in clips:
        txt = wav.with_suffix('.txt')
        shutil.copy2(wav, input_dir/wav.name)
        shutil.copy2(txt, input_dir/txt.name)
        texts.append(txt.read_text(encoding='utf-8-sig').strip())
    dictionary = output/'derived_mandarin.dict'
    report = extend_dictionary(base_dictionary, dictionary, texts, mfa_exe,
                               model=g2p_model, extra_oovs=extra_oovs)
    if report['unresolved']:
        (output/'report.json').write_text(json.dumps({'status':'blocked_oov','dictionary':report},ensure_ascii=False,indent=2),encoding='utf-8')
        raise RuntimeError('Unresolved OOV: '+', '.join(report['unresolved']))
    grid_dir = output/'textgrids'
    # Isolate MFA's internal Kaldi/SQLite state per experiment. Never clean the
    # shared Documents/MFA directory or reuse a prior benchmark's corpus cache.
    mfa_temp = output/'mfa_temp'
    mfa_temp.mkdir(exist_ok=False)
    command = [str(mfa_exe),'align',str(input_dir),str(dictionary),acoustic_model,
               str(grid_dir), '--num_jobs','1',
               '--temporary_directory',str(mfa_temp), '--clean']
    completed = subprocess.run(command,capture_output=True,text=True,timeout=timeout,check=False)
    (output/'mfa.log').write_text((completed.stdout or '')+'\n'+(completed.stderr or ''),encoding='utf-8')
    if completed.returncode:
        raise RuntimeError(f'MFA align failed ({completed.returncode}); inspect mfa.log')
    import importlib.util
    spec=importlib.util.spec_from_file_location('karaoke_mfa_converter',str(converter))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    results={}
    failed_clips=[]
    for wav in clips:
        grids=list(grid_dir.rglob(wav.stem+'.TextGrid'))
        if len(grids)!=1:
            failed_clips.append(wav.stem)
            results[wav.stem] = {'tokens': 0, 'unresolved': [],
                                 'status': 'review_required',
                                 'reason': 'missing_textgrid' if not grids else 'multiple_textgrids',
                                 'textgrid_count': len(grids)}
            continue
        converted=module.convert(module.parse_textgrid(grids[0]))
        (output/(wav.stem+'_mfa_chars.json')).write_text(json.dumps(converted,ensure_ascii=False,indent=2),encoding='utf-8')
        results[wav.stem]={'tokens':len(converted['tokens']),'unresolved':converted['unresolved']}
    summary={'status':'review_required','dictionary':report,'clips':results,'failed_clips':failed_clips,
             'note':'Experimental timings are clip-relative; do not overwrite lyrics_timeline.json.'}
    (output/'report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary

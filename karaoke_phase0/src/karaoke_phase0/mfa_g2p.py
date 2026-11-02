"""MFA G2P adapter. Run via the explicit Conda MFA executable, never uv Python.

The generated pronunciation dictionary is a *derived* artifact. Pretrained files
are read-only. Unknown or invalid outputs are reported, never guessed.
"""
from pathlib import Path
import subprocess
from .process_environment import run_mfa_command
import tempfile
from .pronunciation import read_dictionary, build_dictionary


def generate_pronunciations(words, mfa_executable, model='mandarin_taiwan_mfa', timeout=180):
    """Generate MFA-format phone lists for words, using a temporary word list."""
    words = sorted({w.strip() for w in words if w and w.strip()})
    if not words:
        return {}
    with tempfile.TemporaryDirectory(prefix='karaoke_g2p_') as d:
        src = Path(d) / 'words.txt'
        dst = Path(d) / 'generated.dict'
        src.write_text('\n'.join(words) + '\n', encoding='utf-8')
        command = [str(mfa_executable), 'g2p', str(src), model, str(dst),
                   '--num_jobs', '1', '--no_use_mp']
        result = run_mfa_command(command, capture_output=True, text=True,
                                timeout=timeout, check=False)
        if result.returncode != 0 or not dst.is_file():
            detail = (result.stderr or result.stdout or 'No dictionary produced')[-1200:]
            raise RuntimeError(f'MFA G2P failed ({result.returncode}): {detail}')
        generated = read_dictionary(dst)
        return {w: generated[w][0] for w in words if w in generated and generated[w]}


def extend_dictionary(base_path, output_path, lyrics, mfa_executable,
                      model='mandarin_taiwan_mfa', extra_oovs=(), valid_phones=None):
    """Build augmented dictionary using model-generated pronunciations.

    extra_oovs can contain whole words from MFA's find_oovs report; this is
    important when simple lexicon segmentation splits an OOV compound word.
    """
    base_lexicon = read_dictionary(base_path)
    from .pronunciation import segment
    missing = {w for line in lyrics for w in segment(line, base_lexicon)
               if w not in base_lexicon}
    missing.update(w for w in extra_oovs if w and w not in base_lexicon)
    generated = generate_pronunciations(missing, mfa_executable, model=model)
    report = build_dictionary(base_path, output_path, lyrics,
                              g2p=lambda w: generated.get(w),
                              valid_phones=valid_phones)
    # Extra compound words must be included even if segment() splits them.
    extra_additions = {w: generated[w] for w in extra_oovs
                       if w not in base_lexicon and w in generated
                       and (valid_phones is None or all(p in valid_phones for p in generated[w]))}
    if extra_additions:
        path = Path(output_path)
        existing = read_dictionary(path)
        new_lines = [f"{w}\t0.99\t0.25\t1.0\t1.0\t{' '.join(phones)}"
                     for w, phones in sorted(extra_additions.items()) if w not in existing]
        if new_lines:
            with path.open('a', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(new_lines) + '\n')
    report['added'] = sorted(set(report['added']) | set(extra_additions))
    report['unresolved'] = sorted(set(report['unresolved']) |
                                  {w for w in extra_oovs if w not in base_lexicon and w not in extra_additions})
    report['requires_review'] = bool(report['unresolved'])
    report['g2p_model'] = model
    return report

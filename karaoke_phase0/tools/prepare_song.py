"""CLI entrypoint for resumable local song preparation."""
import argparse
import json
from pathlib import Path
from karaoke_phase0.preparation_pipeline import prepare_song


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--song-folder', required=True, type=Path)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--ctc-shadow', action='store_true', help='Opt in to CTC shadow diagnostics')
    parser.add_argument('--ctc-hybrid-preview', action='store_true', help='Generate automatic non-destructive hybrid preview; implies CTC shadow')
    parser.add_argument('--ctc-shadow-python', help='Python interpreter with CTC dependencies')
    args = parser.parse_args()
    def progress(step, status):
        print(f'{step}: {status}', flush=True)
    try:
        result = prepare_song(args.song_folder, device=args.device, on_progress=progress,
                              ctc_shadow=args.ctc_shadow, ctc_shadow_python=args.ctc_shadow_python,
                              ctc_hybrid_preview=args.ctc_hybrid_preview)
    except Exception as exc:
        parser.exit(1, f'Preparation stopped: {exc}\nSee generated/preparation_status.json\n')
    print(json.dumps({'status': result['status'], 'steps': result['steps'], 'ctc_shadow': result.get('ctc_shadow', {'status': 'disabled'}),
                           'ctc_hybrid_preview': result.get('ctc_hybrid_preview', {'status': 'disabled'})}, indent=2))


if __name__ == '__main__':
    main()

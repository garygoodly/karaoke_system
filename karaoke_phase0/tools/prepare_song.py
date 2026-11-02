"""CLI entrypoint for resumable local song preparation."""
import argparse
import json
from pathlib import Path
from karaoke_phase0.preparation_pipeline import prepare_song


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--song-folder', required=True, type=Path)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    args = parser.parse_args()
    def progress(step, status):
        print(f'{step}: {status}', flush=True)
    try:
        result = prepare_song(args.song_folder, device=args.device, on_progress=progress)
    except Exception as exc:
        parser.exit(1, f'Preparation stopped: {exc}\nSee generated/preparation_status.json\n')
    print(json.dumps({'status': result['status'], 'steps': result['steps']}, indent=2))


if __name__ == '__main__':
    main()

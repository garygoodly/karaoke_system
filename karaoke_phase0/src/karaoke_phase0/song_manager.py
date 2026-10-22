"""Safe local song import; no AI dependency."""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def _rename_staging_with_retry(source, destination, attempts=5, delay=0.1):
    """Retry transient Windows access-denied errors; never overwrite a target."""
    for attempt in range(attempts):
        if destination.exists():
            raise FileExistsError(f'Destination already exists: {destination}')
        try:
            source.rename(destination)
            return
        except PermissionError as exc:
            # WinError 5 (access denied) and 32 (sharing violation) can be transient.
            # Do not retry unrelated permissions errors or non-Windows failures.
            if os.name != 'nt' or getattr(exc, 'winerror', None) not in (5, 32) or attempt == attempts - 1:
                raise
            time.sleep(delay * (attempt + 1))


def database_path(root):
    return Path(root) / 'songs.db'


def init_db(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path(root))) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('CREATE TABLE IF NOT EXISTS songs (id TEXT PRIMARY KEY, title TEXT NOT NULL, artist TEXT NOT NULL, language TEXT NOT NULL, folder TEXT NOT NULL UNIQUE, audio_hash TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)')
        db.commit()


def list_songs(root):
    init_db(root)
    with closing(sqlite3.connect(database_path(root))) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute('SELECT * FROM songs ORDER BY created_at DESC')]


def import_song(root, mp3, title, artist='', language='auto', lyrics_file=None, lyrics_text=None, confirm_move=False):
    """Stage copied inputs, commit DB, then remove originals only on confirmed move.

    If original deletion fails, import succeeds but reports retained source paths.
    """
    root = Path(root).resolve()
    mp3 = Path(mp3).resolve()
    if not mp3.is_file() or mp3.suffix.lower() != '.mp3':
        raise ValueError('Select an existing MP3 file.')
    title = title.strip()
    if not title:
        raise ValueError('Song title is required.')
    if language not in ('auto', 'zh', 'en', 'ja'):
        raise ValueError('Unsupported language.')
    if not confirm_move:
        raise ValueError('Moving source files requires confirmation.')
    if (lyrics_file is None) == (lyrics_text is None):
        raise ValueError('Provide either a TXT/LRC file or pasted lyrics.')
    source_lyrics = None
    if lyrics_file is not None:
        source_lyrics = Path(lyrics_file).resolve()
        if not source_lyrics.is_file() or source_lyrics.suffix.lower() not in ('.txt', '.lrc'):
            raise ValueError('Lyrics file must be TXT or LRC.')
        if source_lyrics == mp3:
            raise ValueError('Audio and lyrics must be different files.')
        text = source_lyrics.read_text(encoding='utf-8-sig')
        extension = source_lyrics.suffix.lower()
    else:
        text = lyrics_text
        extension = '.txt'
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Lyrics cannot be empty.')
    if not mp3.stat().st_size:
        raise ValueError('MP3 is empty.')
    # Prevent source files inside managed library from being accidentally removed.
    for src in (mp3, source_lyrics):
        if src is not None and (src == root or root in src.parents):
            raise ValueError('Source file is already inside the managed songs folder.')
    init_db(root)
    digest = hashlib.sha256()
    with mp3.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    audio_hash = digest.hexdigest()
    with closing(sqlite3.connect(database_path(root))) as db:
        duplicate = db.execute('SELECT title FROM songs WHERE audio_hash=?', (audio_hash,)).fetchone()
        if duplicate:
            raise ValueError(f'This MP3 is already imported: {duplicate[0]}')
    song_id = uuid.uuid4().hex[:12]
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:32] or 'song'
    folder = root / f'{slug}-{song_id}'
    staging = root / f'.import-{song_id}'
    try:
        staging.mkdir()
        shutil.copy2(mp3, staging / 'song.mp3')
        lyrics_name = 'lyrics' + extension
        (staging / lyrics_name).write_text(text, encoding='utf-8')
        (staging / 'generated').mkdir()
        metadata = {'id': song_id, 'title': title, 'artist': artist.strip(), 'language': language,
                    'lyrics_file': lyrics_name, 'audio_hash': audio_hash, 'status': 'imported'}
        (staging / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        # Verify copy before making it visible.
        check = hashlib.sha256((staging / 'song.mp3').read_bytes()).hexdigest()
        if check != audio_hash:
            raise IOError('Audio copy failed checksum validation.')
        _rename_staging_with_retry(staging, folder)
        try:
            with closing(sqlite3.connect(database_path(root))) as db:
                db.execute('INSERT INTO songs VALUES (?,?,?,?,?,?,?,?)',
                           (song_id, title, artist.strip(), language, str(folder), audio_hash,
                            'imported', datetime.now(timezone.utc).isoformat()))
                db.commit()
        except Exception:
            shutil.rmtree(folder)
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    retained = []
    for src in (mp3, source_lyrics):
        if src is not None:
            try:
                src.unlink()
            except OSError:
                retained.append(str(src))
    return {'id': song_id, 'folder': str(folder), 'retained_sources': retained}


def set_song_status(root, song_id, status):
    allowed = {'imported', 'analyzing', 'separated', 'failed'}
    if status not in allowed:
        raise ValueError(f'Invalid separation status: {status}')
    init_db(root)
    with closing(sqlite3.connect(database_path(root))) as db:
        cursor = db.execute('UPDATE songs SET status=? WHERE id=?', (status, song_id))
        if cursor.rowcount != 1:
            raise KeyError(f'Unknown song: {song_id}')
        db.commit()


def get_song(root, song_id):
    init_db(root)
    with closing(sqlite3.connect(database_path(root))) as db:
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT * FROM songs WHERE id=?', (song_id,)).fetchone()
        if row is None:
            raise KeyError(f'Unknown song: {song_id}')
        return dict(row)

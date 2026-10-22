import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from karaoke_phase0.song_manager import import_song, list_songs


class SongManagerTests(unittest.TestCase):
    def test_paste_moves_mp3_creates_txt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / 'source.mp3'
            src.write_bytes(b'fake mp3 test bytes')
            result = import_song(root / 'library', src, '泡沫', 'G.E.M.', lyrics_text='第一句\n第二句', confirm_move=True)
            folder = Path(result['folder'])
            self.assertTrue((folder / 'song.mp3').exists())
            self.assertEqual((folder / 'lyrics.txt').read_text(encoding='utf-8'), '第一句\n第二句')
            self.assertFalse(src.exists())
            self.assertEqual(len(list_songs(root / 'library')), 1)

    def test_lrc_move_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / 'source.mp3'
            lyrics = root / 'source.lrc'
            src.write_bytes(b'audio')
            lyrics.write_text('[00:01.00]Hello', encoding='utf-8')
            result = import_song(root / 'library', src, 'Demo', lyrics_file=lyrics, confirm_move=True)
            self.assertTrue((Path(result['folder']) / 'lyrics.lrc').exists())
            self.assertFalse(lyrics.exists())
            duplicate = root / 'again.mp3'
            duplicate.write_bytes(b'audio')
            with self.assertRaisesRegex(ValueError, 'already imported'):
                import_song(root / 'library', duplicate, 'Again', lyrics_text='Hello', confirm_move=True)
            self.assertTrue(duplicate.exists())

    def test_failed_import_preserves_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / 'source.mp3'
            src.write_bytes(b'audio')
            with self.assertRaises(ValueError):
                import_song(root / 'library', src, 'Demo', lyrics_text='   ', confirm_move=True)
            self.assertTrue(src.exists())
            self.assertEqual(list_songs(root / 'library'), [])

    def test_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'source.mp3'
            src.write_bytes(b'audio')
            with self.assertRaisesRegex(ValueError, 'confirmation'):
                import_song(Path(d) / 'library', src, 'Demo', lyrics_text='abc')
            self.assertTrue(src.exists())


if __name__ == '__main__':
    unittest.main()

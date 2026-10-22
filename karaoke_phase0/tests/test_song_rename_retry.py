import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from karaoke_phase0.song_manager import _rename_staging_with_retry


class RenameRetryTests(unittest.TestCase):
    def test_retry_windows_access_denied(self):
        with TemporaryDirectory() as d:
            src, dst = Path(d) / 'staging', Path(d) / 'song'
            src.mkdir()
            original = Path.rename
            attempts = []

            def flaky(path, target):
                attempts.append(1)
                if len(attempts) < 3:
                    exc = PermissionError('temporarily locked')
                    exc.winerror = 5
                    raise exc
                return original(path, target)

            with patch('karaoke_phase0.song_manager.os.name', 'nt'), \
                 patch('karaoke_phase0.song_manager.time.sleep') as sleep, \
                 patch.object(Path, 'rename', flaky):
                _rename_staging_with_retry(src, dst)
            self.assertTrue(dst.is_dir())
            self.assertEqual(len(attempts), 3)
            self.assertEqual(sleep.call_count, 2)

    def test_existing_destination_is_not_overwritten(self):
        with TemporaryDirectory() as d:
            src, dst = Path(d) / 'staging', Path(d) / 'song'
            src.mkdir(); dst.mkdir()
            with self.assertRaises(FileExistsError):
                _rename_staging_with_retry(src, dst)
            self.assertTrue(src.is_dir())

    def test_non_windows_error_not_retried(self):
        with TemporaryDirectory() as d:
            src, dst = Path(d) / 'staging', Path(d) / 'song'
            src.mkdir()
            with patch.object(Path, 'rename', side_effect=PermissionError('denied')) as rename, \
                 patch('karaoke_phase0.song_manager.time.sleep') as sleep:
                with self.assertRaises(PermissionError):
                    _rename_staging_with_retry(src, dst)
            rename.assert_called_once()
            sleep.assert_not_called()

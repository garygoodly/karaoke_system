import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from karaoke_phase0.mfa_workflow import run_benchmark


class TempIsolationTests(unittest.TestCase):
    def test_mfa_uses_per_run_temp_and_clean(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            corpus = root / "source"
            corpus.mkdir()
            (corpus / "line_000.wav").write_bytes(b"test")
            (corpus / "line_000.txt").write_text("陽光", encoding="utf-8")
            dictionary = root / "base.dict"
            dictionary.write_text("陽 y\n光 g\n", encoding="utf-8")
            output = root / "run"
            commands = []

            def fake_run(cmd, **kwargs):
                commands.append(cmd)
                return type("Result", (), {"returncode": 1, "stdout": "", "stderr": "mock stop"})()

            with patch("karaoke_phase0.mfa_workflow.extend_dictionary",
                       return_value={"unresolved": []}), \
                 patch("karaoke_phase0.mfa_workflow.subprocess.run", side_effect=fake_run):
                with self.assertRaisesRegex(RuntimeError, "MFA align failed"):
                    run_benchmark(corpus, output, dictionary, "mfa", "converter.py")
            self.assertEqual(len(commands), 1)
            cmd = commands[0]
            self.assertIn("--temporary_directory", cmd)
            self.assertIn("--clean", cmd)
            temp_path = Path(cmd[cmd.index("--temporary_directory") + 1])
            self.assertEqual(temp_path, output.resolve() / "mfa_temp")
            self.assertTrue(temp_path.is_dir())

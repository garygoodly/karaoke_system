# Chinese OOV isolation patch

- MODIFY `src/karaoke_phase0/mfa_full_song.py`
- ADD `tests/test_chinese_oov_recovery.py`
- DELETE none.

If MFA G2P cannot resolve some Chinese words, the full-song runner records the affected lines as `unresolved_pronunciation`, removes only those clips from the next MFA attempt, and continues with remaining lines. Failed attempts are preserved in `mfa_run/report.json` and successful retries in `mfa_run_retry_XX/`.

This patch does **not** implement robust normalization or segmentation, and does not guarantee all 35 lines align. It intentionally preserves original lyrics and does not overwrite `lyrics_timeline.json`.

Run tests: `uv run --no-sync python -m pytest -q`.

Run full song with a NEW output directory, such as `full_song_run_06`.

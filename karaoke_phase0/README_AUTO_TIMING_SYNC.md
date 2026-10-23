# Automatic timing synchronization (experimental)

Apply with `apply_patch.ps1 <zip> -RunTests` from karaoke_phase0.

Auto timing sync is enabled by default. It gathers a rolling 14-second history of microphone F0 and compares pitch-change patterns against the reference at offsets from -400 to +400 ms in 25 ms steps. Calibration needs enough pitch changes and a clear best match; otherwise it uses 0 ms or holds the last trusted estimate. The manual slider becomes available when Auto timing sync is unchecked.

This estimates combined performance and system latency, not hardware latency alone. It does not correct wrong harmonics, melody differences, or source separation artifacts. It is an experimental comparison aid, not a scoring-grade alignment algorithm. Re-evaluate during playback; check the displayed status. Existing reference JSON is reused.

# Windows clean-install CI

This patch addresses the Windows PowerShell 5.1 `NativeCommandError` raised by an optional Conda import check, even when `mfa version` prints 3.4.3. The optional check now uses the native process exit code and does not redirect stderr. Genuine nonzero exit codes still fail required steps.

## Install

1. Put `karaoke_windows_ci_setup_fix.zip` in `karaoke_phase0/patches/`.
2. Run `./apply_patch.ps1 ./patches/karaoke_windows_ci_setup_fix.zip -RunTests` from PowerShell.
3. Extract the **separate** `karaoke_windows_ci_workflow.zip` into the Git repository root (parent of `karaoke_phase0`). This is separate because the patch installer intentionally rejects `.github/` paths.
4. Commit `karaoke_phase0/setup_uv.ps1` and `.github/workflows/windows-clean-install.yml` and push.

## What CI validates

- Fresh Windows hosted runner with uv and Miniforge
- Locked project Python packages (including CUDA 12.8 PyTorch wheels, with CPU inference when GPU absent)
- MFA Conda environment and `soundfile`/DLL loading via `conda run`
- Mandarin tokenizer imports
- pytest regression suite

By default, MFA model downloads are skipped to keep normal CI reasonably fast. In GitHub Actions, manually run **Windows clean install** with `download_mfa_models=true` for the full network/model installation test.

## Limitations

- GitHub-hosted Windows runners do not validate NVIDIA CUDA inference, actual microphones, GUI rendering, or GPU VRAM constraints.
- Third-party download/network availability can still fail independently of the setup code.
- The workflow assumes the repository contains `karaoke_phase0/` at its root. If the Git layout differs, adjust `working-directory` and path filters.
- This patch fixes the stderr issue observed on Computer A, but has not yet run on a fresh Windows runner.
- For real end-to-end coverage, add a separate integration test using a licensed short audio fixture after the installer passes.

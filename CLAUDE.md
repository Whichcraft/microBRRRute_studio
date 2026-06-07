# Project instructions: MBSEQ Studio

## Git workflow

- **Always work on the `dev` branch.** All commits go to `dev`.
- **Never push to `main` unless explicitly instructed.** `main` is the release
  branch; merges into it happen only on request.
- Open work, fixes and features all branch from / land on `dev` first.

## Notes

- The app itself depends only on the Python standard library + Tkinter.
  PyInstaller (Windows build) and pytest (tests) are dev-only.
- Run the headless tests with `pytest` (or the stdlib harness) — they need no
  display or audio device. The GUI requires Tkinter (`python3-tk` on Debian).

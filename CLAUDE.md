# Project instructions: microBRRRute Studio

## Git workflow

- **Always work on the `dev` branch.** All commits go to `dev`.
- **Never push to `main` unless explicitly instructed.** `main` is the release
  branch; merges into it happen only on request.
- Open work, fixes and features all branch from / land on `dev` first.

## Versioning & releases

This project follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`). The single
source of truth is `microbrrrute_studio.__version__`; `pyproject.toml` reads it
dynamically — never hard-code the version elsewhere.

**Bump the version on every change that ships, as part of the same work:**

- **PATCH** (`x.y.Z+1`) — bug fixes, doc-only changes, internal refactors with
  no behaviour change.
- **MINOR** (`x.Y+1.0`) — new, backwards-compatible features (new buttons,
  import/export formats, shortcuts, etc.).
- **MAJOR** (`X+1.0.0`) — backwards-incompatible changes to the `.mbseq`
  handling, the public CLI/package API, or saved-file behaviour. (While `0.x`,
  breaking changes may instead bump MINOR.)

Workflow for a change: edit code → bump `__version__` → move the CHANGELOG
`[Unreleased]` items under a new `[x.y.z] - <date>` heading → commit on `dev`.

**Release (CD):** merging `dev` (or `mbuild`) → `main` triggers
`.github/workflows/release.yml`. If `__version__` names a version with no
existing `vX.Y.Z` tag, it builds the Windows `.exe`, Linux, and macOS
executables and publishes a GitHub Release tagged `vX.Y.Z`. So a release happens
exactly when a version-bumped branch reaches `main` (or an `mbuild` branch);
merges without a bump are no-ops for releasing.

## Notes

- The app itself depends only on the Python standard library + Tkinter.
  PyInstaller (Windows build) and pytest (tests) are dev-only.
- Run the headless tests with `pytest` (or the stdlib harness) — they need no
  display or audio device. The GUI requires Tkinter (`python3-tk` on Debian).

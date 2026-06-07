# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

_Nothing yet._

## [0.5.3] - 2026-06-07

### Added
- **Clean exit on Ctrl+C** — the application now exits gracefully without a
  Python traceback when interrupted from the terminal.

### Fixed
- Scrubbed AI assistant names from public-facing code and documentation.

## [0.5.2] - 2026-06-07

### Changed
- **Standardized to 64 steps per bank** — all pattern banks now consistently
  default to, and are padded to, 64 steps (the MicroBrute SE hardware limit).
  This improves compatibility with Arturia's `.mbseq` format and ensures the
  UI always shows the full grid.

## [0.5.1] - 2026-06-07

### Added
- **macOS support in release pipeline** — builds and publishes macOS binaries
  alongside Windows and Linux.
- Added `mbuild` branch as a release trigger.
- Added manual release trigger (`workflow_dispatch`).

## [0.5.0] - 2026-06-07

### Added
- **Undo / redo** (`Ctrl+Z` / `Ctrl+Y`, also in the new Edit menu) across all
  editing operations, with a 100-step history.
- **Transpose** the selected bank by ±1 semitone or ±1 octave (toolbar buttons),
  clamped to the MIDI range.
- **Import a MIDI file** into the selected bank (quantized onto the step grid,
  truncated to 64 steps).
- **Export song** — all non-empty banks concatenated into one MIDI file.
- **Export bank to WAV** — offline render of the selected bank using the current
  oscillator/volume.
- **Space = Play/Stop** (DAW convention); `R` / `Insert` now insert a rest.
- Enforce the MicroBrute SE hardware limit of **64 steps per pattern bank**: the
  editor refuses to grow a bank past 64 (with a status-bar notice) and the
  parser rejects files/raw text that exceed it.
- `pyproject.toml` packaging (installable via `pip install -e .`, with a
  `microbrrrute-studio` entry point) and a **GitHub Actions CI** workflow running
  the headless tests on Linux/Windows/macOS across Python 3.10 and 3.12.
- **CD release pipeline** — on merge to `main`, when `__version__` names a new
  version, builds standalone Windows (`.exe`) and Linux executables with
  PyInstaller and publishes them to a tagged GitHub Release.
- **Single-source versioning** — `microbrrrute_studio.__version__` is the one
  source of truth; `pyproject.toml` reads it dynamically. Project follows
  Semantic Versioning.

### Changed
- **Renamed the project to microBRRRute Studio.** The GitHub repo is now
  `Whichcraft/microBRRRute_studio`, the Python package is `microbrrrute_studio`,
  and the Windows build is `microBRRRute_Studio.exe`. The `.mbseq` file format
  and the `MbseqProject` class keep their names (they refer to Arturia's format).

### Fixed
- Startup crash binding the non-ASCII `ö` PC key; unbindable keys are now
  skipped instead of raising `TclError`.

## [0.4.0] - 2026-06-07

### Fixed
- **Stop now actually stops the sound.** Previously the Stop button only
  cancelled the step scheduler, so the note already playing kept ringing out.
  Playback is now backed by a stoppable engine: `stop_all()` purges Windows
  audio (`SND_PURGE`) and terminates the in-flight `aplay`/`paplay`/`afplay`
  process on Linux/macOS. `Esc` also stops.
- Linux/macOS playback processes are tracked so they can be killed on demand;
  a player terminated by Stop is no longer reported as an audio error.

### Added
- **▶▶ Play All** — chain every non-empty bank into a single song.
- **Loop** toggle for continuous playback (on by default).
- **Green playhead** highlighting the step currently sounding, distinct from
  the blue edit cursor.
- Play/Stop buttons enable/disable to reflect transport state.
- **Unsaved-changes guard** — title bar shows `*` when modified, and the app
  confirms before quitting with unsaved work.
- Headless test suite under `tests/` covering parse/serialize round-trips,
  note-name conversion, MIDI export validity and waveform generation.

### Changed
- `synth.play_note` is now non-blocking on Windows (`SND_ASYNC`), matching the
  MicroBrute's monophonic behaviour (a new note interrupts the previous one).
- README rewritten with full feature overview and per-platform setup.

## [0.3.0] - 2026-06-04

### Added
- Full 8 pattern bank support: banks 1–8 always visible and preserved on
  load/save.
- Bank selector buttons, play selected bank, edit selected bank only.
- Duplicate a bank to another bank.
- Export the selected bank as MIDI, or all 8 banks as separate MIDI files.
- Built-in preview sounds on the 25-key on-screen keyboard.
- Unique per-note temp filenames to avoid a Windows playback race during
  sequencer playback.

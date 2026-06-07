# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

_Nothing yet._

## [0.7.6] - 2026-06-07

### Fixed
- Fixed CI pipeline failure on Windows by calling `ruff` and `mypy` via
  `python -m`.

## [0.7.5] - 2026-06-07

### Added
- **Custom App Icon** — added an official app icon (🎹) generated from the
  system's emoji font. The icon is now visible in the window title bar and
  baked into the standalone executables.

## [0.7.4] - 2026-06-07

### Fixed
- Fixed build pipeline failure by removing a reference to a missing icon file
  in the PyInstaller spec.
- Hardened artifact staging logic in the Release workflow for more reliable
  multi-platform builds.

## [0.7.3] - 2026-06-07

### Changed
- Comprehensive documentation update: README.md now reflects all recent features
  (Dark Mode, Tooltips, Pre-rendering, etc.).
- Refined the roadmap in TODO.md with new planned features like MIDI Input
  and partial Copy/Paste.

## [0.7.2] - 2026-06-07

### Removed
- Removed the "Play All" feature; the app now exclusively plays the currently
  selected pattern bank, aligning with the hardware sequencer's behavior.

### Fixed
- Fixed keyboard visual feedback: black keys no longer "white out" after being
  played; they now correctly return to their original black color.

## [0.7.1] - 2026-06-07

### Added
- **Sample Project** — included `around_the_world.mbseq`, a community-sourced
  transcription of the classic Daft Punk bassline, to help users get started.

## [0.7.0] - 2026-06-07

### Added
- **Rock-solid timing via pre-rendering** — the entire sequence is now
  pre-rendered to a single WAV on Play, eliminating jitter at high BPM.
- **Anti-click protection** — implemented short crossfades between steps to
  prevent audio clicks.
- **Dark Mode** — a high-contrast dark theme available in the View menu.
- **Tooltips** — contextual help on all transport and editor buttons.
- **Click-and-drag reordering** — move pattern steps by dragging them on the
  grid.
- **Count-in** — optional 4-beat metronome lead-in before playback starts.
- **Configurable Bank Settings** — set the active bank length and toggle between
  1/8 and 1/16 note resolutions.
- **Hardware range validation** — warnings in the status bar if notes fall
  outside the MicroBrute's typical playable range (C0–C8).
- **Project quality infra** — added `ruff` and `mypy` to CI for automated linting
  and type-checking.
- **App icon support** — updated PyInstaller spec to support custom icons.

### Changed
- **Resizable reflowing grid** — the step grid now automatically wraps to
  multiple rows based on window width, eliminating horizontal scrolling.

## [0.6.0] - 2026-06-07

### Added
- **Recent files menu** — a new "Open Recent" submenu in the File menu tracks
  the 10 most recently used `.mbseq` files, persisted across app restarts in
  `~/.microbrrrute_studio_recent.json`.

## [0.5.9] - 2026-06-07

### Added
- **Copy / paste banks** — copy a whole pattern bank to the system clipboard and
  paste it back into any bank (or an external text editor) using `Ctrl+C` and
  `Ctrl+V`. Added dedicated buttons to the Edit toolbar.

## [0.5.8] - 2026-06-07

### Changed
- Updated README with a disclaimer that macOS builds are currently untested and
  welcome feedback from Mac users.

## [0.5.7] - 2026-06-07

### Removed
- Removed the experimental "Export song to WAV" feature (concatenating all banks
  into one WAV). Per-bank export remains the correct workflow for patterns.

## [0.5.6] - 2026-06-07

### Added
- **Visual feedback on keyboard** — keys now light up green when played (manually
  or via the sequencer) to provide better visual orientation.

## [0.5.5] - 2026-06-07

### Added
- **Metronome** toggle — audible clicks on quarter-note beats to help with
  composition.

## [0.5.4] - 2026-06-07

### Added
- **Export song to WAV** — concatenates all non-empty banks into a single audio
  render (available in the File menu and the main toolbar).

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

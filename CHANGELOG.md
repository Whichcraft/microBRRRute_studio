# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-06-16

### Fixed
- **Piano Roll ignored bank length** — grid, Piano Roll drawing, hit-testing,
  playback, and selection now share the same active bank-length helper.
- **Exports ignored active length and resolution** — bank MIDI, all-bank MIDI,
  song MIDI, and bank WAV exports now use the active step count and 1/8 vs
  1/16 timing.
- **Count-in and 1/16 controls were hidden** — added top-bar controls for
  count-in and step resolution, with persistent settings.
- **Dark mode startup mismatch** — saved dark-mode settings are now applied
  after widgets are built.
- **Cursor spinbox was off by one** — the visible cursor control is now
  1-based while the internal cursor remains zero-based.
- **Malformed MIDI headers imported silently** — MIDI import now validates the
  full Standard MIDI File header and rejects truncated track chunks.
- **Metronome clicks depended on synth volume** — clicks are mixed
  independently, so note-step clicks remain audible when note volume is zero.
- **Preview notes overlapped on Linux/macOS** — preview audio now uses its own
  tracked subprocess set and stops the previous preview before starting a new
  one.
- **Duplicate-bank default was a no-op** — the dialog now defaults to a
  different target bank and reports invalid/self-copy choices.
- **Per-step attributes were lost on save/load** — gate, accent, and slide now
  round-trip in `.mbseq` using inline step tokens without emitting comments.
- **Parser accepted hidden bank slots** — `.mbseq` parsing now rejects bank
  slots outside 1..8 and duplicate slot lines.
- **WAV export diverged from playback rendering** — offline WAV export now uses
  the same ADSR, accent, slide, metronome, and step-resolution renderer as
  playback.
- **Opening files discarded dirty projects** — opening recent or chosen files
  now asks before replacing unsaved work.
- **Dirty state was not visible in the title bar** — unsaved projects now show
  a leading `*` in the window title.
- **Tooltips assumed text-widget APIs** — tooltip placement now falls back to
  widget geometry for controls that do not support insert bounding boxes.
- **Add/delete step ignored active length** — structural edits now grow/shrink
  the active bank length while preserving the 64-step storage limit.
- **Selection paste partial mutation** — clipboard contents are now fully
  parsed and MIDI-range validated before any selected steps are changed.
- **Whole-bank paste accepted invalid MIDI notes** — pasted bank data now
  rejects malformed and out-of-range notes before replacing the current bank.
- **MIDI SysEx import skipped following events** — Standard MIDI file SysEx
  events now use their VLQ payload length instead of scanning for a literal
  terminator byte, preserving valid later note events.
- **1/16 playback audio drift** — pre-rendered playback audio now uses the same
  step resolution as the playhead timing.
- **Failed raw-text apply polluted undo history** — raw `.mbseq` text is parsed
  before an undo snapshot is pushed.
- **Duplicate-bank dialog was unreachable** — added an Edit-menu entry for the
  existing duplicate-bank workflow.

## [0.13.0] - 2026-06-12

### Added
- Raw-text editor: "Apply raw" button with Ctrl+Enter binding for direct
  `.mbseq` editing with validation.
- Added C♭ (B) and F♭ (E) enharmonic equivalents to note-name parser.

### Changed
- Bank names (`# Name X:` headers) removed from `.mbseq` serialization.
  Bank names are now runtime-only and reset to defaults on reload.
- Metronome click volume reduced from 40% to 10% of full scale.

### Fixed
- **VLQ infinite loop on negative values** — `vlq()` now raises
  `ValueError` for negative input.
- **Gate>1.0 causes IndexError in audio render** — `s.gate` is now
  clamped to [0.0, 1.0] in `render_steps_to_data`.
- **MIDI running status corruption** — status byte is reset to 0 after
  meta, SysEx, and system realtime messages to prevent stale bytes from
  corrupting subsequent event parsing.
- **Transpose aliased rest objects** — `transpose_steps` now copies rest
  `Step` objects instead of returning aliased references.
- **Serialize writes over-length sequences** — `serialize()` now slices
  to `MAX_STEPS`.
- **Unclosed SysEx advances past track end** — terminator skip is guarded
  with a bounds check.
- **Phase reset per step causes audio clicks** — oscillator phase is now
  tracked cumulatively across steps in both `render_steps_to_data` and
  `render_steps_wav`.
- **Bank length spinner had no effect** — `bank_length` is now wired into
  grid display and playback truncation.
- **Paste operations crash on invalid clipboard data** — `ValueError` from
  malformed tokens is now caught with a user-friendly message.
- **Add-step could insert at stale cursor** — now uses selection position
  when selection is active.
- **Copy bank allowed self-copy and invalid targets** — validated bank
  range and rejected self-copy.
- **Ctrl+scroll detection incomplete on Linux** — added `0x20000` mask for
  extended Ctrl key modifier.
- **Step number labels too sparse at small sizes** — visibility threshold
  adjusted for both orientations.
- **Keyboard highlight captured `rect` by reference** — replaced lambda
  default-arg hack with a proper closure.
- **Piano roll note outline was empty string** — `outline` parameter is
  now omitted when not needed instead of passing `""` (which Tk
  interprets as a black border).
- **`make_wave` envelope could never reach full amplitude** — attack and
  release durations are clamped to half the total frame count.
- **Out-of-range MIDI notes corrupt exported file** — `export_midi` now
  clamps notes to 0..127.
- **Thread-unsafe `_last_error` access** — wrapped all reads and writes in
  a threading lock.
- **MIDI import skipped non-MTrk chunks** — now scans past unknown chunk
  types instead of breaking.
- **Context menu lambdas captured `idx` by reference** — all context menu
  commands now use default-argument lambdas.

## [0.12.1] - 2026-06-07

### Added
- The Arpeggiator now provides explicit target start/end controls and a
  multi-select source-note list.
- Source notes can be added directly using note names such as `C3 E3 G3` or
  MIDI note numbers; a pre-existing multi-step selection is no longer required.

### Fixed
- The Piano Roll now redraws immediately after its initial pane layout and on
  canvas resize, so it is visible at startup without requiring a click.

## [0.12.0] - 2026-06-07

### Added
- Independent horizontal Piano Roll zoom and pan controls.
- A Horizontal/Vertical Piano Roll orientation switch with numbered step
  indicators in both layouts.
- Drag-to-select in the Piano Roll, with additive and toggle modifiers.
- An integrated Piano Roll keyboard that highlights cursor, selection, and
  playback notes.

### Fixed
- Restored missing editor methods and MIDI export handlers that prevented the
  application from starting or completing menu actions.
- Fixed WAV bank export after the migration to expressive `Step` objects.
- Fixed the initial Piano Roll layout so the canvas receives visible space when
  the application starts.

## [0.11.5] - 2026-06-07

### Changed
- Final documentation sync for the `v0.11.x` release series, ensuring all
  features and shortcuts are accurately described.

## [0.11.4] - 2026-06-07

### Changed
- Expanded the roadmap in `TODO.md` with a new "Hardware verification" section
  to track testing of arpeggiator patterns on the actual synth.

## [0.11.3] - 2026-06-07

### Changed
- Further refined the roadmap to focus strictly on sequencing and editing
  capabilities, removing sound-design items that aren't supported by the
  `.mbseq` file format.

## [0.11.2] - 2026-06-07

### Changed
- Refined the roadmap in `TODO.md` to better respect the monophonic nature of
  the MicroBrute hardware (removed "unison" in favor of "sub-oscillator").

## [0.11.1] - 2026-06-07

### Added
- **Arpeggiator Tool** — transform selected steps into complex arpeggios (Up,
  Down, Up-Down, Random) with a single click.
- **ADSR Envelope Controls** — Added persistent Attack, Decay, Sustain, and
  Release settings to the software synth.
- **Improved Shortcuts** — added a summary of keyboard shortcuts to the README.

### Changed
- Hardened the release pruning logic to ensure all old releases and orphaned
  tags are removed before a new release is published.

## [0.11.0] - 2026-06-07

### Added
- **Piano Roll Zoom and Pan** — you can now zoom into the Visual Piano Roll
  using `Ctrl + MouseWheel` and pan vertically using the `MouseWheel`.
- **New Keyboard Shortcuts** — added `Ctrl+N` to quickly rename the current bank
   and `Ctrl+R` to open the Pattern Randomizer.
- **Enhanced Drag-and-Drop Feedback** — active drop targets in the step grid
  now highlight with a distinct border and color during reordering.

## [0.10.0] - 2026-06-07

### Added
- **Visual Piano Roll Editor** — a large interactive canvas for viewing and
  editing patterns. Click anywhere to place a note across the full hardware
  range (C0–C8). Syncs in real-time with the step grid and playback.
- **Musical Pattern Randomizer** — generate coherent, scale-aware sequences.
  Includes support for Major, Minor, Pentatonic, Blues, and Phrygian scales.
- **Bank Naming** — give each of the 8 pattern banks a custom descriptive name.
  Names are persisted in `.mbseq` files as standardized comment headers.
- **Toolbar Theme Toggle** — quickly switch between Light and Dark modes using
  the new persistent toggle in the main toolbar.

### Changed
- **Responsive Layout** — implemented a `PanedWindow` to allow users to resize
  the relative space between the step grid and the piano roll.

## [0.9.1] - 2026-06-07

### Added
- **Per-step Expressive Attributes** — right-click any step on the grid to set
  its **Gate Length** (25%–100%), **Accent**, or **Slide/Legato** status.
- **Upgraded Audio Engine** — the built-in synth now audibly respects per-step
  attributes, including volume boosts for accents and smooth transitions for
  slides.
- **Multi-step Selection** — select multiple steps using `Shift+Click` (range)
  or `Ctrl+Click` (toggle). Batch operations like **Transpose** and **Delete**
  now work on the entire selection.
- **Range-based Copy/Paste** — copying multiple selected steps now stores a
  sequence in the clipboard that can be pasted starting at any cursor position.
- Added visual indicators (• for accent, → for slide) directly on the grid.

## [0.9.0] - 2026-06-07

### Added
- **Persistent App Settings** — a new settings dialog (View menu) allows you to
  persist your volume, tempo, theme, and resolution preferences across app
  restarts in `~/.microbrrrute_studio_settings.json`.
- **Granular Copy/Paste** — `Ctrl+C` and `Ctrl+V` now copy and paste individual
  steps, while `Ctrl+Shift+C/V` handles whole banks.
- **Enhanced Drag-and-Drop** — added real-time visual feedback when reordering
  steps on the grid.

### Changed
- **CI Build Verification** — every CI run now performs a test build with
  PyInstaller to ensure build stability across all platforms.

## [0.8.6] - 2026-06-07

### Fixed
- Fixed `mypy` type-checking errors in `synth.py`.
- Added return type hints to core methods in `app.py` to improve static analysis
  coverage.

## [0.8.5] - 2026-06-07

### Changed
- Updated documentation with a note that the application may also work for the
  MiniBrute, though it remains untested as I only have access to a MicroBrute SE.
  Feedback from MiniBrute users is welcome.

## [0.8.4] - 2026-06-07

### Fixed
- Fixed all 63 `ruff` linting errors, including unused imports and formatting
  (multiple statements on one line). This ensures cleaner code and passing CI.

## [0.8.3] - 2026-06-07

### Changed
- Updated README to reflect the new bundled `.zip` release format and the
  inclusion of the `around_the_world.mbseq` example in the download.

## [0.8.2] - 2026-06-07

### Added
- **Bundled Release Archives** — releases now deliver a compressed `.zip` archive
  containing both the standalone executable and the `around_the_world.mbseq`
  example project for each platform.

## [0.8.1] - 2026-06-07

### Changed
- Restricted both CI and Release pipelines to only trigger on pushes or merges
  to the `main` branch. Pushes to `dev` will no longer trigger any automated
  actions.

## [0.8.0] - 2026-06-07

### Fixed
- Fixed CI quality checks by properly defining `ruff` and `mypy` in the `dev`
  optional dependencies in `pyproject.toml`.

## [0.7.9] - 2026-06-07

### Changed
- Final documentation sync: updated `README.md` to reflect the removal of the
  "Play All" feature and the addition of the new 🎹 icon and automated release
  pruning.

## [0.7.8] - 2026-06-07

### Fixed
- Eliminated UI flickering in the step grid during note entry. The grid now
  updates existing widgets incrementally instead of recreating them, providing
  a much smoother composition experience.

## [0.7.7] - 2026-06-07

### Changed
- Updated release workflow to automatically prune all old GitHub Releases and
  tags before publishing a new one. This ensures that the Releases section
  always only contains the latest stable version.

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

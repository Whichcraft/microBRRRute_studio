# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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

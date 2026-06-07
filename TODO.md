# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] **Real-time gapless playback** via an optional `sounddevice` + `numpy`
      backend (fall back to the current WAV-file player when unavailable). This
      removes per-note temp-file churn and tightens timing/latency.
- [ ] Per-step **gate length / accent / slide** to match MicroBrute Seq Step
      controls, instead of a fixed 82% gate.
- [ ] **Pre-render the bank** once on Play instead of generating each WAV on the
      fly, to keep timing rock-solid at high BPM.
- [ ] Anti-click: short crossfade between consecutive notes.

## Editing & workflow
- [ ] **Undo / redo** stack (`Ctrl+Z` / `Ctrl+Y`).
- [ ] **Copy / paste** steps and ranges between banks.
- [ ] **Transpose** selected bank by semitones / octaves.
- [ ] Click-and-drag to **reorder** steps.
- [ ] **Metronome / count-in** option.
- [ ] Configurable **steps-per-bank** and time signature (eighths vs sixteenths).
- [ ] Recent-files menu.

## UI / UX
- [ ] **Space = Play/Stop** (DAW convention); move "insert rest" to another key.
- [ ] Visual feedback on the on-screen keyboard for the playing note.
- [ ] Dark theme / high-contrast option.
- [ ] Resizable, scrollable step grid that reflows on window resize.
- [ ] Tooltips on transport and editor buttons.

## Import / export
- [ ] **Import a MIDI file** into a bank (quantize to steps).
- [ ] Export **all banks as one** multi-track or concatenated MIDI song.
- [ ] Export to **WAV** (bounce the synth render to disk).
- [ ] Drag-and-drop `.mbseq` files onto the window to open.

## Quality / infra
- [ ] Add `pytest` to dev dependencies and a **GitHub Actions CI** workflow
      (lint + headless tests on Linux/Windows/macOS).
- [ ] Type-check with `mypy` / `ruff` in CI.
- [ ] Package metadata (`pyproject.toml`) so it can be `pip install`ed.
- [ ] App icon and Windows version-info resource for the EXE.
- [ ] Validate notes against the MicroBrute's actual playable range.

# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] MIDI Input support: play on a physical MIDI keyboard to record steps (needs
      external libraries like `mido`).
- [ ] **Legato/Slide** support during playback (detect consecutive identical notes
      and skip release/attack).

## Editing & workflow
- [ ] Drag-and-drop `.mbseq` files onto the window to open (requires external lib
      for reliable cross-platform support).

## UI / UX
- [ ] Dark theme toggle in the main toolbar for easier access.
- [ ] Option to name banks (e.g., "Intro", "Verse 1").

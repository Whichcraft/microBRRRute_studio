# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] MIDI Input support: play on a physical MIDI keyboard to record steps (needs
      external libraries like `mido`).
- [ ] **Real-time gapless playback** (optional `sounddevice` + `numpy` backend) to
      further tighten timing.

## Editing & workflow
- [ ] Drag-and-drop `.mbseq` files onto the window to open (requires external lib
      for reliable cross-platform support).
- [ ] Pattern Randomizer: generate random sequences within a scale.

## UI / UX
- [ ] Dark theme toggle in the main toolbar for easier access.
- [ ] Option to name banks (e.g., "Intro", "Verse 1").
- [ ] Visual piano roll editor (vertical or horizontal).

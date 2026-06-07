# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] MIDI Input support: play on a physical MIDI keyboard to record steps (needs
      external libraries like `mido`).
- [ ] ADSR Envelope controls for the synth (currently fixed short decay).

## Editing & workflow
- [ ] Drag-and-drop `.mbseq` files onto the window to open (requires external lib
      for reliable cross-platform support).
- [ ] Arpeggiator: transform simple chords or patterns into complex arpeggios.

## UI / UX
- [ ] Keyboard shortcuts for naming banks and opening the randomizer.
- [ ] Zoom and pan support for the visual Piano Roll.
- [ ] Better visual feedback for drag-and-drop targets on the grid.

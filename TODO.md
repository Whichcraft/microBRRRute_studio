# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] MIDI Input support: play on a physical MIDI keyboard to record steps (needs
      external libraries like `mido`).
- [ ] Visual metronome: a simple flashing indicator for the beat.

## Editing & workflow
- [ ] Drag-and-drop `.mbseq` files onto the window to open (requires external lib
      for reliable cross-platform support).
- [ ] Scale-quantize for free-hand Piano Roll editing.

## Hardware verification
- [ ] Test arpeggiator-generated patterns on actual MicroBrute SE hardware to
      verify playback consistency.

# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] Per-step **gate length / accent / slide** to match MicroBrute Seq Step
      controls (requires research into `.mbseq` support for these attributes).
- [ ] MIDI Input support: play on a physical MIDI keyboard to record steps (needs
      external libraries like `mido`).

## Editing & workflow
- [ ] Drag-and-drop `.mbseq` files onto the window to open (requires external lib
      for reliable cross-platform support).
- [ ] Multi-step selection: select ranges of steps for batch editing/transposing.

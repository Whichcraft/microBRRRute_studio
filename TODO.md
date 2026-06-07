# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] Per-step **gate length / accent / slide** to match MicroBrute Seq Step
      controls.
- [ ] MIDI Input support: play on a physical MIDI keyboard to record steps.

## Editing & workflow
- [ ] Drag-and-drop `.mbseq` files onto the window to open (requires external lib
      for reliable cross-platform support).
- [ ] **Copy/Paste individual steps** or ranges of steps, not just whole banks.

## UI / UX
- [ ] App settings dialog to persist volume, tempo, and theme preferences.
- [ ] Better visual feedback for drag-and-drop targets on the grid.

## Quality / infra
- [ ] Automated build verification in CI (run PyInstaller and check output).

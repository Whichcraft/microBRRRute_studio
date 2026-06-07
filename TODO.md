# Roadmap / TODO

Proposed improvements, roughly ordered by value. Done items move to
[CHANGELOG.md](CHANGELOG.md).

## Audio engine
- [ ] Per-step **gate length / accent / slide** to match MicroBrute Seq Step
      controls, instead of a fixed 82% gate.
- [ ] **Pre-render the bank** once on Play instead of generating each WAV on the
      fly, to keep timing rock-solid at high BPM.
- [ ] Anti-click: short crossfade between consecutive notes.

## Editing & workflow
- [ ] Click-and-drag to reorder steps.
- [ ] **Count-in** option.
- [ ] Configurable steps-per-bank and time signature (eighths vs sixteenths).

## UI / UX
- [ ] Dark theme / high-contrast option.
- [ ] Resizable, scrollable step grid that reflows on window resize.
- [ ] Tooltips on transport and editor buttons.

## Import / export
- [ ] Drag-and-drop `.mbseq` files onto the window to open.
- [ ] Export the whole song to a single WAV (evaluate usefulness).

## Quality / infra
- [ ] Type-check with `mypy` / `ruff` in CI.
- [ ] App icon and Windows version-info resource for the EXE.
- [ ] Validate notes against the MicroBrute's actual playable range.

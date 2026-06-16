# 🎹 microBRRRute Studio

[![CI](https://github.com/Whichcraft/microBRRRute_studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Whichcraft/microBRRRute_studio/actions/workflows/ci.yml)

**A desktop composer for Arturia MicroBrute SE sequences.**

microBRRRute Studio is a lightweight Python/Tkinter app for creating, editing and
auditioning `.mbseq` pattern files — the plain-text sequence format used by the
Arturia MicroBrute SE. (Note: It maybe also works for the MiniBrute, but it's
untested as I only have a MicroBrute SE here. Feel free to test and send me your
feedback, thanks!) Compose on an on-screen 25-key keyboard, hear what you
write through a built-in software synth, juggle all 8 pattern banks, and export
to standard MIDI when you're ready to take it elsewhere.

It runs from source on **Windows, macOS and Linux**, and builds into a
single-file **Windows `.exe`** with PyInstaller.

---

## ⬇️ Download

**Compressed archives (.zip)** for **Windows**, **Linux**, and **macOS** are
attached to each release. Each archive includes:
1. The standalone **microBRRRute Studio** executable (no Python required).
2. The **`around_the_world.mbseq`** example project.

*(Note: macOS binaries are provided by CI but are currently untested as I have
no Mac. Feedback is very welcome!)*

**[→ Latest release](https://github.com/Whichcraft/microBRRRute_studio/releases/latest)**

Every version bump merged to `main` is built and published automatically by CI.

---

## ✨ Features

- **Visual Piano Roll Editor.** An interactive canvas for viewing and editing
  patterns across the full MicroBrute range (C0–C8). Switch between
  **horizontal and vertical layouts**, use numbered step indicators, and
  **zoom and pan** to navigate complex patterns. Click anywhere to place a
  note or drag across notes to select them. The integrated piano keyboard
  highlights cursor, selection, and playback notes, and the view stays
  synchronized with the step grid and playhead.
- **Musical Pattern Randomizer.** Generate coherent sequences within specific
  scales (Major, Minor, Pentatonic, Blues, etc.). Control root note, octave
  range, and density.
- **Arpeggiator Tool.** Choose the exact target step range and source notes,
  including notes entered by name (`C3 E3 G3`) or MIDI number. Generate Up,
  Down, Up-Down, or Random patterns without preparing a multi-step selection
  first.
- **ADSR Envelope Controls.** Fine-tune the synth's character with persistent
  Attack, Decay, Sustain, and Release settings.
- **All 8 pattern banks with Custom Naming.** Switch between banks and give
  them descriptive names (e.g. "Intro", "Verse"). Names are runtime-only and
  reset to defaults on reload. Use **Edit → Duplicate Bank...** to copy the
  current bank to another slot.
- **On-screen 25-key MicroBrute keyboard.** Click to insert + audition a note,
  right-click to preview without editing, or play from your computer keyboard
  (`A W S E D F T G Y H U J K …`).
- **Visual Feedback.** Keys light up and the piano roll highlights in real-time
  during playback.
- **Built-in software synth** with selectable oscillator
  (square / saw / triangle / sine), volume control and octave shift.
- **Reliable transport.**
  - **Rock-solid timing via pre-rendering** — entire sequences are pre-rendered
    to a single audio buffer on Play to eliminate jitter.
  - **■ Stop** (or `Esc`) stops the sound immediately.
  - **Loop**, **Metronome**, and **Count-in** toggles.
  - A green **playhead** highlights the sounding step.
- **App Icon.** Official 🎹 icon visible in the title bar and taskbar.
- **Powerful step editor.**
  - **Click-and-drag reordering** — move steps by dragging them on the grid.
  - **Multi-step Selection** — select ranges using `Shift+Click` or multiple steps
    via `Ctrl+Click`.
  - **Batch Operations** — transpose or delete the entire selection at once,
    including ±1 semitone, ±1 octave, and ±2 octave transpose buttons.
  - **Per-step Attributes** — right-click a step to set its **Gate Length**,
    **Accent**, or **Slide/Legato** status. Visual indicators (• for accent,
    → for slide) show directly on the grid.
  - **Configurable Bank Settings** — set the active bank length (1–64) and
    toggle between 1/8 and 1/16 note resolutions.
  - Add / delete steps, insert rests (`R`).
  - Clipboard paste validates all notes before changing the pattern, so bad
    tokens or out-of-range MIDI values cannot partially overwrite a bank.
  - **Undo / redo** (`Ctrl+Z` / `Ctrl+Y`) across every edit.
- **Dark Mode.** High-contrast dark theme accessible via a toolbar toggle.
- **Recent files menu.** Quick access to your 10 most recently used files.
- **Raw text view and editor.** Edit the underlying `.mbseq` text directly with
  an "Apply raw" button and `Ctrl+Enter` shortcut, including validation feedback.
- **Import & export.** Import MIDI, including length-prefixed SysEx events;
  export bank/song as MIDI; bounce bank to **WAV**. (Anti-click protection and
  expressive rendering included).
- **Unsaved-changes guard.** Title bar shows `*` and app warns before quitting.
- **Tooltips.** Hover over any button for help.

---

## 🎹 Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Space` | Start / Stop playback |
| `Esc` | Stop playback immediately |
| `R` / `Insert` | Set current step to Rest |
| `Left` / `Right` | Move edit cursor |
| `Ctrl + Z` | Undo |
| `Ctrl + Y` | Redo |
| `Ctrl + C` | Copy current step or selection |
| `Ctrl + V` | Paste from clipboard |
| `Ctrl+Shift+C` | Copy entire pattern bank |
| `Ctrl+Shift+V` | Paste entire pattern bank |
| `Ctrl + N` | Rename current bank |
| `Ctrl + R` | Open Pattern Randomizer |
| `Ctrl + Wheel` | Zoom Piano Roll vertically |
| `Ctrl + Shift + Wheel` | Zoom Piano Roll horizontally |
| `Shift + Wheel` | Pan Piano Roll horizontally |
| `MouseWheel` | Pan Piano Roll vertically |

The **Horizontal / Vertical** controls above the Piano Roll transpose the
editor layout. Horizontal mode places time left-to-right; Vertical mode places
time top-to-bottom. The chosen orientation is saved in app settings.

Duplicate banks from **Edit → Duplicate Bank...**. The duplicate command copies
notes and per-step attributes to a different bank slot.

### Arpeggiator

Open **Arpeggiate...** from the edit toolbar. Set the first and last target
steps, click notes in the source-note list to include or exclude them, and use
**Add notes** to enter additional note names or MIDI values. The generated
range becomes the active selection so it can immediately be transposed,
copied, or edited.

---


## 🚀 Run from source

Requires **Python 3.10+** with Tkinter.

```bash
python main.py
```

**Windows** — Tkinter ships with the python.org installer; or just double-click
`run_from_source.bat`.

**macOS** — `brew install python-tk` if Tkinter is missing. (Note: macOS version is currently untested, as I have no Mac. Feel free to test and send me your feedback, you're very welcome!)

**Linux** — Tkinter is a separate package and audio playback uses `aplay` or
`paplay`:

```bash
sudo apt install python3-tk alsa-utils      # Debian/Ubuntu, default python3
# if you run a specific interpreter, install its matching Tk, e.g.:
sudo apt install python3.14-tk
python3 main.py
```

---

## 🛠️ Build a standalone executable

The bundled PyInstaller spec builds a single-file executable for whatever OS you
run it on (`microBRRRute_Studio.exe` on Windows, `microBRRRute_Studio` on Linux):

```bash
pip install pyinstaller
pyinstaller --noconfirm microBRRRute_Studio.spec   # output in dist/
```

On Windows you can instead double-click `build_windows_exe.bat`.

CI builds Windows, Linux, and macOS executables automatically and publishes
them to the [Releases](https://github.com/Whichcraft/microBRRRute_studio/releases)
page on every version bump merged to `main`. To keep downloads simple, CI
automatically prunes old versions to keep only the **latest** release active.

---

## 🧪 Tests

Parsing, serialization, MIDI import/export, waveform generation, playback
timing, clipboard validation, and Piano Roll coordinate logic are covered by
headless tests that need no display or audio device:

```bash
pip install -e ".[dev]"
pytest
```

CI runs these on Linux, Windows and macOS (Python 3.10 & 3.12) on every push.

---

## 📄 The `.mbseq` format

`.mbseq` is plain text — one line per pattern bank, `slot:notes`. Each bank is
standardized to **exactly 64 steps** (padded with `x` if shorter) to ensure full
compatibility with Arturia hardware.

```text
1:53 53 55 x 60 ... (64 tokens total)
2:60 60 x 64 ... (64 tokens total)
```

Numbers are MIDI note values (`0`–`127`); `x` is a rest. 

**Example Project:** A sample project (`around_the_world.mbseq`) is included, featuring a transcription of the iconic Daft Punk bassline. *(Transcription credit: Community-sourced from Arturia MicroBrute user forums).*

---

## 📐 Project layout

```text
microbrrrute_studio/
  app.py          Tkinter UI + transport
  synth.py        Software synth + cross-platform, stoppable playback engine
  mbseq.py        .mbseq parse / serialize, MIDI note-name helpers
  midi_export.py  Standard MIDI File import/export helpers
tests/            Headless data-layer and Piano Roll logic tests
main.py           Entry point
```

See [CHANGELOG.md](CHANGELOG.md) for release history and [TODO.md](TODO.md) for
the roadmap.

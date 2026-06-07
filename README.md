# 🎹 microBRRRute Studio

[![CI](https://github.com/Whichcraft/microBRRRute_studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Whichcraft/microBRRRute_studio/actions/workflows/ci.yml)

**A desktop composer for Arturia MicroBrute SE sequences.**

microBRRRute Studio is a lightweight Python/Tkinter app for creating, editing and
auditioning `.mbseq` pattern files — the plain-text sequence format used by the
Arturia MicroBrute SE. Compose on an on-screen 25-key keyboard, hear what you
write through a built-in software synth, juggle all 8 pattern banks, and export
to standard MIDI when you're ready to take it elsewhere.

It runs from source on **Windows, macOS and Linux**, and builds into a
single-file **Windows `.exe`** with PyInstaller.

---

## ⬇️ Download

Prebuilt standalone executables for **Windows**, **Linux**, and **macOS** are
attached to each release — no Python install required.

*(Note: macOS binaries are provided by CI but are currently untested as I have
no Mac. Feedback is very welcome!)*

**[→ Latest release](https://github.com/Whichcraft/microBRRRute_studio/releases/latest)**

Every version bump merged to `main` is built and published automatically by CI.

---

## ✨ Features

- **All 8 pattern banks**, always visible and preserved on load/save — switch
  banks with the `1`–`8` selector.
- **On-screen 25-key MicroBrute keyboard.** Click to insert + audition a note,
  right-click to preview without editing, or play from your computer keyboard
  (`A W S E D F T G Y H U J K …`).
- **Built-in software synth** with selectable oscillator
  (square / saw / triangle / sine), volume control and octave shift — no audio
  drivers or external soundfonts required.
- **Reliable transport.**
  - **▶ Play Bank** auditions the selected bank.
  - **▶▶ Play All** chains every non-empty bank into one song.
  - **■ Stop** (or `Esc`) *actually stops the sound immediately* — including the
    note currently sounding.
  - **Loop** toggle for continuous playback.
  - A green **playhead** highlights the step that's sounding, distinct from the
    blue edit cursor.
- **Step editor** — add / delete steps, insert rests (`R`), transpose a bank by
  semitone or octave, clear or duplicate a whole bank. Banks are capped at the
  MicroBrute's **64-step** hardware limit.
- **Undo / redo** (`Ctrl+Z` / `Ctrl+Y`) across every edit.
- **Raw text view** — edit the underlying `.mbseq` text directly and apply it
  back, with validation.
- **Import & export** — import a MIDI file into a bank; export the selected
  bank, all 8 banks separately, or the whole song concatenated as MIDI; bounce a
  bank to **WAV**. (Handwritten Standard MIDI File reader/writer — no deps.)
- **Unsaved-changes guard** — the title bar shows a `*` when modified and the
  app asks before you quit on unsaved work.

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

CI builds both the Windows and Linux executables automatically and publishes
them to the [Releases](https://github.com/Whichcraft/microBRRRute_studio/releases)
page on every version bump merged to `main`.

---

## 🧪 Tests

The data layer (parsing, serialization, MIDI export, waveform generation) is
covered by headless tests that need no display or audio device:

```bash
pip install -e ".[dev]"
pytest
```

CI runs these on Linux, Windows and macOS (Python 3.10 & 3.12) on every push.

---

## 📄 The `.mbseq` format

`.mbseq` is plain text — one line per pattern bank, `slot:notes`:

```text
1:53 53 55 x 60
2:60 60 x 64
...
8:48 x x 72
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
  midi_export.py  Standard MIDI File writer
tests/            Headless data-layer tests
main.py           Entry point
```

See [CHANGELOG.md](CHANGELOG.md) for release history and [TODO.md](TODO.md) for
the roadmap.

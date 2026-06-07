# 🎹 MBSEQ Studio

**A desktop composer for Arturia MicroBrute SE sequences.**

MBSEQ Studio is a lightweight Python/Tkinter app for creating, editing and
auditioning `.mbseq` pattern files — the plain-text sequence format used by the
Arturia MicroBrute SE. Compose on an on-screen 25-key keyboard, hear what you
write through a built-in software synth, juggle all 8 pattern banks, and export
to standard MIDI when you're ready to take it elsewhere.

It runs from source on **Windows, macOS and Linux**, and builds into a
single-file **Windows `.exe`** with PyInstaller.

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
- **Step editor** — add / delete steps, insert rests (`Space`), clear or
  duplicate a whole bank.
- **Raw text view** — edit the underlying `.mbseq` text directly and apply it
  back, with validation.
- **MIDI export** — export the selected bank, or all 8 banks as separate `.mid`
  files (handwritten Standard MIDI File writer, no dependencies).
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

**macOS** — `brew install python-tk` if Tkinter is missing.

**Linux** — Tkinter is a separate package and audio playback uses `aplay` or
`paplay`:

```bash
sudo apt install python3-tk alsa-utils    # Debian/Ubuntu
python3 main.py
```

---

## 🛠️ Build a Windows EXE

```bat
build_windows_exe.bat
```

Produces a single-file executable at `dist\MBSEQ_Studio.exe`.

---

## 🧪 Tests

The data layer (parsing, serialization, MIDI export, waveform generation) is
covered by headless tests that need no display or audio device:

```bash
pip install pytest
pytest
```

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

---

## 📐 Project layout

```text
mbseq_studio/
  app.py          Tkinter UI + transport
  synth.py        Software synth + cross-platform, stoppable playback engine
  mbseq.py        .mbseq parse / serialize, MIDI note-name helpers
  midi_export.py  Standard MIDI File writer
tests/            Headless data-layer tests
main.py           Entry point
```

See [CHANGELOG.md](CHANGELOG.md) for release history and [TODO.md](TODO.md) for
the roadmap.

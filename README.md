# MBSEQ Studio v5 - MicroBrute SE Composer

Windows-ready Python/Tkinter app for Arturia MicroBrute SE `.mbseq` files.

## v5 changes

- Proper 8 pattern bank support: banks 1-8 are always visible.
- Load/save preserves all 8 `.mbseq` banks.
- Bank selector buttons 1-8.
- Play selected bank.
- Edit selected bank only.
- Duplicate bank to another bank.
- Export selected bank as MIDI.
- Export all 8 banks as separate MIDI files.
- Built-in preview sounds on the MicroBrute-style 25-key keyboard.

## Run from source

```bat
run_from_source.bat
```

## Build Windows EXE

```bat
build_windows_exe.bat
```

The EXE will be created at:

```text
dist\mbseq_studio.exe
```

## Format

`.mbseq` is plain text:

```text
1:53 53 55 x 60
2:60 60 x 64
...
8:48 x x 72
```

Numbers are MIDI notes. `x` is a rest.

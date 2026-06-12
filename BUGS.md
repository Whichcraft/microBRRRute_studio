# Bug Report

Bugs found via remote LLM (qwen3.6:27b on codebot.ethz.ch) and manual code review.

---

## HIGH

### 1. `vlq()` infinite loop on negative values — `midi_export.py:5-12`

```python
def vlq(value: int) -> bytes:
    b = value & 0x7F
    value >>= 7
    ...
```

Python's `>>=` on a negative integer is an arithmetic shift — it keeps the sign
bit, so `value` never reaches `0` and the loop runs forever. `vlq(-1)` hangs.

**Fix:** Clamp or assert `value >= 0` at the top.

---

### 2. `render_steps_to_data` IndexError on gate > 1.0 — `synth.py:128,154`

```python
note_frames = max(1, int(step_frames * s.gate))     # line 128
render_until = step_frames if has_slide else note_frames  # line 135
frames[i] += val * env                                 # line 154
```

`s.gate > 1.0` makes `note_frames > step_frames`, causing `frames[i]` to
index out of bounds. (`render_steps_wav` at line 204 correctly clamps with
`max(0.0, min(step.gate, 1.0))` but `render_steps_to_data` does not.)

**Fix:** Clamp `s.gate` to `[0.0, 1.0]` before computing `note_frames`.

---

### 3. Running status leaks into meta/SysEx events — `midi_export.py:84-91`

```python
b = data[i]
if b & 0x80:
    status = b
    i += 1
# else: running status reuses the previous `status` byte
ev = status & 0xF0
if status == 0xFF:   # meta event
```

MIDI running status only applies to channel voice messages (`0x80–0xEF`). If
the previous event was a meta event (`0xFF`) or SysEx, and the next event byte
is `< 0x80`, the code incorrectly applies running status with `status == 0xFF`,
corrupting the parse.

**Fix:** Only allow running status when `0x80 <= status <= 0xEF`. Reset
`status = 0` after meta/SysEx/system messages.

---

## MEDIUM

### 4. `transpose_steps` returns aliased rest objects — `mbseq.py:91`

```python
if s.note is None:
    out.append(s)  # same object reference!
```

Rests (`Step` objects with `note=None`) are appended by reference. Mutating
them through the returned list also mutates the input list, violating the
functional contract of a transpose operation.

**Fix:** Copy the Step: `out.append(Step(note=None, gate=s.gate, ...))`.

---

### 5. `serialize` doesn't truncate over-long sequences — `mbseq.py:73`

`serialize()` outputs all steps regardless of length. If a sequence exceeds
`MAX_STEPS` (64), the output file fails to reparse because `parse()` raises
`ValueError` for over-long banks. This breaks save/load round-tripping.

**Fix:** Slice `steps[:MAX_STEPS]` before serializing.

---

### 6. Unclosed SysEx causes `i` to advance past `end` — `midi_export.py:98-101`

```python
while i < end and data[i] != 0xF7:
    i += 1
i += 1  # skip terminator
```

If the SysEx terminator `0xF7` is missing (malformed file), the loop stops at
`i == end`. Then `i += 1` pushes `i` past `end`, exiting the track loop and
potentially skipping events in subsequent tracks.

**Fix:** Check `i < end` before the final `i += 1`.

---

### 7. Phase reset per step causes audio clicks — `synth.py:137-138`

```python
phase = (freq * (i / sample_rate)) % 1.0
```

The oscillator phase resets to 0 at the start of every step. For sustained,
sliding, or legato notes this produces audible clicks at step boundaries.

**Fix:** Track cumulative phase (or sample count) across steps instead of
resetting per step.

---

### 8. Step-length Len spinner does nothing — `app.py:217-222`

The `bank_length` `tk.IntVar` and its `Spinbox` widget are created but never
read anywhere in `refresh_grid()` or `play_sequence()`. Changing the spinner
has no effect on the displayed grid or on playback length.

**Fix:** Either wire the length spinner into the grid rendering (truncate steps
at the user-set length) or remove the widget.

---

## LOW

### 9. `midi_to_name` octave off-by-one for high notes — `mbseq.py:103`

```python
return f'{NOTE_NAMES[n % 12]}{(n // 12) - 1}'
```

MIDI note 127 (the highest) should be `G8` but the formula gives `G9`. The
octave boundary at C8 (MIDI 108) shifts due to sharps/flats — notes above
C8 alias to octave 9.

---

### 10. `_show_step_context_menu` captures `idx` by reference — `app.py:1559-1572`

The context menu `lambda` closures for gate-length radio buttons capture `idx`
and `g` by reference (not value). Fast repeated right-clicks on different steps
may change the wrong step's gate. (Same class as the `highlight_note` bug that
was already fixed.)

**Fix:** Use default arguments: `lambda v=g, i=idx: self.set_step_gate(i, v)`.

---

### 11. `_draw_piano_roll_note` uses empty string outline — `app.py:1464`

```python
outline = (
    "#ffffff" if step.slide else "#ffa500" if idx in self._selection else ""
)
```

When neither slide nor selection, `outline = ""`. Tkinter interprets an empty
outline string as a default color (black), producing a thin black border on
note rectangles. This is likely unintended — the notes should have no border.

**Fix:** Use `outline=""` properly or omit the outline parameter.

---

### 12. `play_pre_rendered_wav` ignores `stop_sequence()` on Windows — `app.py:223-243`

Windows uses `winsound.PlaySound(..., SND_ASYNC)`. If `stop_sequence()` is
called shortly after playback starts, `winsound.PlaySound(None, SND_PURGE)` is
called, but the already-scheduled `after()` tick callbacks continue to fire for
a few cycles before noticing `self.playing == False`, causing visual flicker
of the playhead after stop.

**Fix:** Check `self.playing` both at the top of `_play_tick()` and as the
first action in `stop_sequence()` before purging audio.

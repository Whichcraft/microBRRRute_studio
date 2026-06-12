from __future__ import annotations
from pathlib import Path

# Minimal Standard MIDI File writer, type 0, one track.
def vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError('VLQ value must be non-negative')
    b = value & 0x7F
    value >>= 7
    out = bytearray([b])
    while value:
        out.insert(0, 0x80 | (value & 0x7F))
        value >>= 7
    return bytes(out)

def export_midi(path: str | Path, steps: list[int | None], bpm: int = 120, ticks_per_step: int = 240, gate: float = 0.8) -> None:
    tpq = 480
    us_per_qn = int(60_000_000 / max(1, bpm))
    track = bytearray()
    # Tempo meta
    track += b'\x00\xff\x51\x03' + us_per_qn.to_bytes(3, 'big')
    pending = 0
    note_len = max(1, int(ticks_per_step * gate))
    rest_tail = max(0, ticks_per_step - note_len)
    for note in steps:
        if note is None:
            pending += ticks_per_step
            continue
        track += vlq(pending) + bytes([0x90, note, 100])
        track += vlq(note_len) + bytes([0x80, note, 0])
        pending = rest_tail
    track += vlq(pending) + b'\xff\x2f\x00'
    header = b'MThd' + (6).to_bytes(4,'big') + (0).to_bytes(2,'big') + (1).to_bytes(2,'big') + tpq.to_bytes(2,'big')
    chunk = b'MTrk' + len(track).to_bytes(4,'big') + bytes(track)
    Path(path).write_bytes(header + chunk)


def export_song_midi(path: str | Path, banks: list[list[int | None]], bpm: int = 120,
                     ticks_per_step: int = 240, gate: float = 0.8) -> None:
    """Export several banks concatenated end-to-end into one MIDI file."""
    combined: list[int | None] = []
    for steps in banks:
        combined.extend(steps)
    export_midi(path, combined, bpm=bpm, ticks_per_step=ticks_per_step, gate=gate)


def read_vlq(data: bytes, i: int, limit: int = -1) -> tuple[int, int]:
    end = limit if limit >= 0 else len(data)
    value = 0
    while i < end:
        b = data[i]
        i += 1
        value = (value << 7) | (b & 0x7F)
        if not (b & 0x80):
            return value, i
    raise ValueError('Truncated VLQ in MIDI data')


def import_midi(path: str | Path, ticks_per_step: int | None = None) -> list[int | None]:
    """Parse a Standard MIDI File into a monophonic step list.

    Note-on events are quantized onto a fixed step grid; grid cells with no note
    become rests. This recovers files written by export_midi exactly and gives a
    reasonable approximation for arbitrary monophonic MIDI.
    """
    data = Path(path).read_bytes()
    if data[:4] != b'MThd':
        raise ValueError('Not a Standard MIDI File (missing MThd header)')
    division = int.from_bytes(data[12:14], 'big')
    if division & 0x8000:
        raise ValueError('SMPTE time division is not supported')
    tpq = division or 480
    if ticks_per_step is None:
        ticks_per_step = max(1, tpq // 2)  # eighth-note grid, matching export

    events: list[tuple[int, int]] = []  # (absolute_tick, note)
    i = 14
    while i + 8 <= len(data):
        if data[i:i+4] != b'MTrk':
            i += 1
            continue
        length = int.from_bytes(data[i+4:i+8], 'big')
        i += 8
        end = i + length
        t = 0
        status = 0
        while i < end:
            delta, i = read_vlq(data, i, end)
            t += delta
            b = data[i]
            if b & 0x80:
                status = b
                i += 1
            # Running status is only valid for channel voice messages (0x80-0xEF).
            # Reset status after non-channel events so stale bytes don't corrupt parsing.
            ev = status & 0xF0
            if status == 0xFF:           # meta event
                i += 1
                mlen, i = read_vlq(data, i, end)
                i += mlen
                status = 0
            elif status == 0xF0 or status == 0xF7:  # SysEx
                while i < end and data[i] != 0xF7:
                    i += 1
                if i < end:
                    i += 1  # skip terminator
                status = 0
            elif status in (0xF1, 0xF3):  # 2-byte system messages
                i += 1
                status = 0
            elif status == 0xF2:          # 3-byte system message (song pos)
                i += 2
                status = 0
            elif ev in (0xC0, 0xD0):     # program change / channel pressure: 1 data byte
                i += 1
            elif ev in (0x90, 0x80, 0xA0, 0xB0, 0xE0):
                if i + 1 >= end:
                    break
                note, vel = data[i], data[i+1]
                i += 2
                if ev == 0x90 and vel > 0:
                    events.append((t, note))
                # 0x90 with vel=0 is a note-off per MIDI spec; handled by
                # the step-grid quantizer below (omitted event → rest).
            elif status in (0xF6,) or (0xF8 <= status <= 0xFE):
                status = 0  # realtime messages
            else:
                i += 1
        i = end

    if not events:
        return []
    events.sort()
    last_step = events[-1][0] // ticks_per_step
    steps: list[int | None] = [None] * (last_step + 1)
    for t, note in events:
        steps[t // ticks_per_step] = note  # last note in a grid cell wins
    return steps

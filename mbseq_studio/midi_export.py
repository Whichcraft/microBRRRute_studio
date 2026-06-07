from __future__ import annotations
from pathlib import Path

# Minimal Standard MIDI File writer, type 0, one track.
def vlq(value: int) -> bytes:
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

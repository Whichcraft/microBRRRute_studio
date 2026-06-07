from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

REST = None
MAX_STEPS = 64  # MicroBrute SE hardware limit: 64 steps per pattern bank
# Playable range: C0 (12) to C8 (108) covers the MicroBrute's range with full octave shifts.
MIN_PLAYABLE = 12
MAX_PLAYABLE = 108

@dataclass
class Step:
    note: int | None = None
    gate: float = 0.82  # Default gate length
    accent: bool = False
    slide: bool = False

@dataclass
class MbseqProject:
    sequences: dict[int, list[Step]] = field(default_factory=dict)

    @classmethod
    def empty(cls, slots: int = 8, steps: int = MAX_STEPS) -> 'MbseqProject':
        return cls({i: [Step() for _ in range(steps)] for i in range(1, slots + 1)})

    @classmethod
    def parse(cls, text: str) -> 'MbseqProject':
        seqs: dict[int, list[Step]] = {}
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            if ':' not in line:
                raise ValueError(f'Line {lineno}: missing colon')
            slot_s, data = line.split(':', 1)
            try:
                slot = int(slot_s.strip())
            except ValueError as exc:
                raise ValueError(f'Line {lineno}: bad slot number') from exc
            steps: list[Step] = []
            for tok in data.split():
                if tok.lower() == 'x':
                    steps.append(Step(note=None))
                else:
                    try:
                        note = int(tok)
                    except ValueError as exc:
                        raise ValueError(f'Line {lineno}: bad token {tok!r}') from exc
                    if note < 0 or note > 127:
                        raise ValueError(f'Line {lineno}: MIDI note out of range: {note}')
                    steps.append(Step(note=note))
            if len(steps) > MAX_STEPS:
                raise ValueError(f'Line {lineno}: bank {slot} has {len(steps)} steps; MicroBrute SE allows at most {MAX_STEPS}')
            # Pad to MAX_STEPS
            if len(steps) < MAX_STEPS:
                steps.extend([Step() for _ in range(MAX_STEPS - len(steps))])
            seqs[slot] = steps
        if not seqs:
            return cls.empty()
        # Ensure all banks 1..8 exist.
        for slot in range(1, 9):
            seqs.setdefault(slot, [Step() for _ in range(MAX_STEPS)])
        return cls(dict(sorted(seqs.items())))

    @classmethod
    def load(cls, path: str | Path) -> 'MbseqProject':
        return cls.parse(Path(path).read_text(encoding='utf-8-sig'))

    def serialize(self) -> str:
        lines = []
        # Always write banks 1..8 in Arturia-compatible order, padded to MAX_STEPS.
        for slot in range(1, 9):
            steps = self.sequences.get(slot, [Step() for _ in range(MAX_STEPS)])
            if len(steps) < MAX_STEPS:
                steps = steps + [Step() for _ in range(MAX_STEPS - len(steps))]
            tokens = ['x' if s.note is None else str(s.note) for s in steps]
            lines.append(f'{slot}:{" ".join(tokens)}')
        return '\n'.join(lines) + '\n'

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.serialize(), encoding='utf-8', newline='\n')

def transpose_steps(steps: list[Step], semitones: int) -> list[Step]:
    """Transpose notes by `semitones`, leaving rests untouched.

    Notes that would fall outside the MIDI range 0..127 are clamped.
    """
    out: list[Step] = []
    for s in steps:
        if s.note is None:
            out.append(s)
        else:
            new_note = max(0, min(127, s.note + semitones))
            out.append(Step(note=new_note, gate=s.gate, accent=s.accent, slide=s.slide))
    return out


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_TO_SHARP = {'DB':'C#','EB':'D#','GB':'F#','AB':'G#','BB':'A#'}

def midi_to_name(n: int) -> str:
    return f'{NOTE_NAMES[n % 12]}{(n // 12) - 1}'

def name_to_midi(value: str) -> int:
    s = value.strip().upper()
    if not s:
        raise ValueError('Empty note')
    if s.isdigit():
        n = int(s)
        if 0 <= n <= 127:
            return n
        raise ValueError('MIDI note must be 0..127')
    if len(s) >= 3 and s[1] in ['#', 'B']:
        name, oct_s = s[:2], s[2:]
    else:
        name, oct_s = s[:1], s[1:]
    name = FLAT_TO_SHARP.get(name, name)
    if name not in NOTE_NAMES:
        raise ValueError(f'Unknown note name: {value}')
    octave = int(oct_s)
    n = (octave + 1) * 12 + NOTE_NAMES.index(name)
    if not 0 <= n <= 127:
        raise ValueError('MIDI note out of range')
    return n

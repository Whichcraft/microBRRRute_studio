"""Headless tests for the data layer (no tkinter / no audio device needed)."""
import struct
import wave
from pathlib import Path

from mbseq_studio.mbseq import MbseqProject, midi_to_name, name_to_midi
from mbseq_studio.midi_export import export_midi, vlq
from mbseq_studio.synth import make_wave, midi_freq


def test_parse_roundtrip():
    text = "1:53 53 55 x 60\n2:60 60 x 64\n"
    proj = MbseqProject.parse(text)
    # banks 1..8 always present after parse
    assert set(proj.sequences) == set(range(1, 9))
    assert proj.sequences[1] == [53, 53, 55, None, 60]
    assert proj.sequences[2] == [60, 60, None, 64]
    # serialize -> parse is stable
    assert MbseqProject.parse(proj.serialize()).sequences == proj.sequences


def test_empty_has_eight_banks():
    proj = MbseqProject.empty()
    assert set(proj.sequences) == set(range(1, 9))
    assert all(steps == [None] * 16 for steps in proj.sequences.values())


def test_serialize_always_writes_eight_banks():
    proj = MbseqProject.parse("1:60\n")
    lines = proj.serialize().strip().splitlines()
    assert len(lines) == 8
    assert lines[0].startswith("1:")


def test_parse_rejects_bad_note():
    for bad in ("1:128", "1:-1", "1:abc", "no colon"):
        try:
            MbseqProject.parse(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


def test_parse_rejects_over_64_steps():
    ok = "1:" + " ".join(["60"] * 64) + "\n"
    assert len(MbseqProject.parse(ok).sequences[1]) == 64
    too_many = "1:" + " ".join(["60"] * 65) + "\n"
    try:
        MbseqProject.parse(too_many)
    except ValueError:
        return
    raise AssertionError("expected ValueError for 65 steps")


def test_note_name_roundtrip():
    for n in range(0, 128):
        assert name_to_midi(midi_to_name(n)) == n
    assert name_to_midi("C4") == 60
    assert name_to_midi("Db4") == name_to_midi("C#4")


def test_save_load_roundtrip(tmp_path):
    proj = MbseqProject.parse("1:60 62 64 x\n3:48 x 50\n")
    p = tmp_path / "song.mbseq"
    proj.save(p)
    assert MbseqProject.load(p).sequences == proj.sequences


def test_midi_export_is_valid_smf(tmp_path):
    p = tmp_path / "bank.mid"
    export_midi(p, [60, None, 64, 67], bpm=140)
    data = p.read_bytes()
    assert data[:4] == b"MThd"
    assert b"MTrk" in data
    # tempo meta event present
    assert b"\xff\x51\x03" in data


def test_vlq():
    assert vlq(0) == b"\x00"
    assert vlq(127) == b"\x7f"
    assert vlq(128) == b"\x81\x00"


def test_make_wave_writes_pcm(tmp_path):
    p = tmp_path / "note.wav"
    make_wave(p, 69, duration=0.05, wave_shape="sine", volume=0.5)
    with wave.open(str(p)) as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getnframes() > 0


def test_midi_freq_a4():
    assert abs(midi_freq(69) - 440.0) < 1e-6

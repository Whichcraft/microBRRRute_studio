"""Headless tests for the data layer (no tkinter / no audio device needed)."""
import wave

from microbrrrute_studio.mbseq import MbseqProject, midi_to_name, name_to_midi, transpose_steps
from microbrrrute_studio.midi_export import export_midi, export_song_midi, import_midi, vlq
from microbrrrute_studio.synth import make_wave, midi_freq, render_steps_wav


def test_parse_roundtrip():
    text = "1:53 53 55 x 60\n2:60 60 x 64\n"
    proj = MbseqProject.parse(text)
    # banks 1..8 always present after parse
    assert set(proj.sequences) == set(range(1, 9))
    # now padded to 64
    assert proj.sequences[1][:5] == [53, 53, 55, None, 60]
    assert len(proj.sequences[1]) == 64
    assert proj.sequences[2][:4] == [60, 60, None, 64]
    assert len(proj.sequences[2]) == 64
    # serialize -> parse is stable
    assert MbseqProject.parse(proj.serialize()).sequences == proj.sequences


def test_empty_has_eight_banks():
    proj = MbseqProject.empty()
    assert set(proj.sequences) == set(range(1, 9))
    assert all(steps == [None] * 64 for steps in proj.sequences.values())


def test_serialize_always_writes_eight_banks():
    proj = MbseqProject.parse("1:60\n")
    lines = proj.serialize().strip().splitlines()
    assert len(lines) == 8
    assert lines[0].startswith("1:60")
    # check it padded bank 1 to 64 steps
    assert len(lines[0].split(":")[1].split()) == 64


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


def test_transpose_clamps_and_keeps_rests():
    assert transpose_steps([60, None, 62], 2) == [62, None, 64]
    assert transpose_steps([0, 127], -5) == [0, 122]      # low clamp
    assert transpose_steps([120, 127], 12) == [127, 127]  # high clamp


def test_midi_roundtrip(tmp_path):
    p = tmp_path / "rt.mid"
    steps = [60, None, 64, 67, None, 72]
    export_midi(p, steps, bpm=120)
    # import recovers notes and internal rests (trailing rest is dropped)
    assert import_midi(p) == [60, None, 64, 67, None, 72]


def test_import_rejects_non_midi(tmp_path):
    p = tmp_path / "bad.mid"
    p.write_bytes(b"not a midi file at all")
    try:
        import_midi(p)
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-MIDI input")


def test_export_song_concatenates(tmp_path):
    p = tmp_path / "song.mid"
    export_song_midi(p, [[60, 62], [64, None, 67]], bpm=120)
    assert import_midi(p) == [60, 62, 64, None, 67]


def test_render_steps_wav(tmp_path):
    p = tmp_path / "bounce.wav"
    render_steps_wav(p, [60, None, 64], bpm=120, wave_shape="saw", volume=0.4)
    with wave.open(str(p)) as w:
        # 3 steps * (eighth note at 120bpm = 0.25s) * 44100 frames
        assert abs(w.getnframes() - int(3 * 0.25 * 44100)) <= 3
        assert w.getnchannels() == 1

from types import SimpleNamespace

from microbrrrute_studio.app import MbseqStudio


def test_piano_roll_position_accounts_for_keyboard_zoom_and_pan():
    studio = SimpleNamespace(
        piano_roll_orientation=SimpleNamespace(get=lambda: "horizontal"),
        _piano_roll_off_x=-120.0,
        _piano_roll_off_y=30.0,
        _piano_roll_metrics=lambda: (700.0, 240.0, 60.0, 640.0, 240.0, 20.0, 10.0),
    )

    assert MbseqStudio._piano_roll_position(studio, 60.0, 230.0) == (6, 15)
    assert MbseqStudio._piano_roll_position(studio, 59.0, 230.0)[0] == 5


def test_vertical_piano_roll_position_swaps_time_and_pitch_axes():
    studio = SimpleNamespace(
        piano_roll_orientation=SimpleNamespace(get=lambda: "vertical"),
        _piano_roll_off_x=-20.0,
        _piano_roll_off_y=-40.0,
        _piano_roll_metrics=lambda: (700.0, 500.0, 50.0, 700.0, 450.0, 15.0, 10.0),
    )

    assert MbseqStudio._piano_roll_position(studio, 30.0, 70.0) == (4, 17)


def test_wheel_direction_supports_linux_and_windows_events():
    assert MbseqStudio._wheel_up(SimpleNamespace(num=4, delta=0))
    assert not MbseqStudio._wheel_up(SimpleNamespace(num=5, delta=0))
    assert MbseqStudio._wheel_up(SimpleNamespace(num=None, delta=120))
    assert not MbseqStudio._wheel_up(SimpleNamespace(num=None, delta=-120))


def test_build_arpeggio_modes_remove_duplicates_and_order_notes():
    notes = [67, 60, 64, 60]

    assert MbseqStudio._build_arpeggio(notes, "Up") == [60, 64, 67]
    assert MbseqStudio._build_arpeggio(notes, "Down") == [67, 64, 60]
    assert MbseqStudio._build_arpeggio(notes, "Up-Down") == [60, 64, 67, 64]


def test_build_arpeggio_up_down_handles_single_note():
    assert MbseqStudio._build_arpeggio([60], "Up-Down") == [60]


def test_parse_step_tokens_accepts_rests_and_midi_range():
    assert MbseqStudio._parse_step_tokens(["60", "x", "127"]) == [60, None, 127]


def test_parse_step_tokens_rejects_bad_or_out_of_range_tokens():
    for tokens in (["bad"], ["128"], ["-1"]):
        try:
            MbseqStudio._parse_step_tokens(tokens)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {tokens!r}")

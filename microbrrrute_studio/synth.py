from __future__ import annotations
import math
import struct
import tempfile
import wave
import threading
import os
import sys
import subprocess
import time
import uuid
from pathlib import Path

from .mbseq import Step

A4 = 440.0
_last_error: str | None = None
_error_lock = threading.Lock()

# Playback engine state -------------------------------------------------------
# The MicroBrute is a monophonic synth, so preview playback is monophonic too:
# starting a new note stops the previous one. Stop must silence audio *now*, so
# we track the in-flight subprocesses (Linux/macOS) and use SND_PURGE (Windows).
_IS_WINDOWS = sys.platform.startswith("win")
_IS_MAC = sys.platform == "darwin"
_lock = threading.Lock()
_active_procs: set[subprocess.Popen] = set()


def get_last_audio_error() -> str | None:
    with _error_lock:
        return _last_error


def midi_freq(note: int) -> float:
    return A4 * (2 ** ((note - 69) / 12))


def make_wave(
    path: Path,
    note: int,
    duration: float = 0.18,
    wave_shape: str = "square",
    volume: float = 0.25,
    sample_rate: int = 44100,
) -> None:
    total = max(1, int(duration * sample_rate))
    freq = midi_freq(note)
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    attack = max(1, min(int(0.008 * sample_rate), total // 2))
    release = max(1, min(int(0.035 * sample_rate), total // 2))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total):
            t = i / sample_rate
            phase = (freq * t) % 1.0
            if wave_shape == "sine":
                val = math.sin(2 * math.pi * phase)
            elif wave_shape == "saw":
                val = 2 * phase - 1
            elif wave_shape == "triangle":
                val = 4 * abs(phase - 0.5) - 1
            else:
                val = 1.0 if phase < 0.5 else -1.0
            env = 1.0
            if i < attack:
                env = i / max(1, attack)
            if i > total - release:
                env = min(env, (total - i) / max(1, release))
            frames += struct.pack("<h", int(val * amp * env))
        w.writeframes(frames)


def _osc_sample(phase: float, wave_shape: str) -> float:
    if wave_shape == "sine":
        return math.sin(2 * math.pi * phase)
    if wave_shape == "saw":
        return 2 * phase - 1
    if wave_shape == "triangle":
        return 4 * abs(phase - 0.5) - 1
    return 1.0 if phase < 0.5 else -1.0


def render_steps_to_data(
    steps: list[Step],
    bpm: int = 120,
    wave_shape: str = "square",
    volume: float = 0.25,
    attack: float = 0.005,
    decay: float = 0.1,
    sustain: float = 0.5,
    release: float = 0.05,
    sample_rate: int = 44100,
    metronome: bool = False,
    steps_per_quarter: int = 2,
) -> bytes:
    """Render a step list to raw PCM data bytes.

    Includes anti-click fades, per-step gate/accent, ADSR envelope, and optional metronome clicks.
    """
    step_secs = 60.0 / max(1, bpm) / max(1, steps_per_quarter)
    step_frames = max(1, int(step_secs * sample_rate))
    click_amp = int(32767 * 0.3)

    # Global ADSR frames
    a_f = max(1, int(attack * sample_rate))
    d_f = max(1, int(decay * sample_rate))
    r_f = max(1, int(release * sample_rate))

    all_frames = bytearray()
    total_samples = 0
    for idx, s in enumerate(steps):
        frames = [0.0] * step_frames

        # Metronome click
        if metronome:
            is_beat = idx % 2 == 0
            f = midi_freq(84 if is_beat else 72)
            click_len = int(0.02 * sample_rate)
            for i in range(min(click_len, step_frames)):
                phase = (f * (i / sample_rate)) % 1.0
                env = 1.0 - (i / click_len)
                frames[i] += math.sin(2 * math.pi * phase) * 0.10 * env

        if s.note is not None:
            freq = midi_freq(s.note)
            gate = max(0.0, min(s.gate, 1.0))
            note_frames = max(1, int(step_frames * gate))
            step_amp = volume * 1.5 if s.accent else volume
            amp_scaled = int(32767 * max(0.0, min(step_amp, 1.0)))

            has_slide = (
                s.slide and (idx + 1 < len(steps)) and (steps[idx + 1].note is not None)
            )
            render_until = step_frames if has_slide else note_frames

            for i in range(render_until):
                phase = (freq * ((total_samples + i) / sample_rate)) % 1.0
                val = _osc_sample(phase, wave_shape)

                # ADSR Logic
                env = 1.0
                if i < a_f:
                    env = i / a_f
                elif i < a_f + d_f:
                    env = 1.0 - (1.0 - sustain) * ((i - a_f) / d_f)
                else:
                    env = sustain

                # Release phase (only if not sliding)
                if not has_slide and i > note_frames - r_f:
                    env = min(env, sustain * (note_frames - i) / r_f)

                frames[i] += val * env

            for f in frames:
                v = max(-1.0, min(1.0, f))
                all_frames += struct.pack("<h", int(v * amp_scaled))
        else:
            for f in frames:
                v = max(-1.0, min(1.0, f))
                all_frames += struct.pack("<h", int(v * click_amp))

        total_samples += step_frames

    return bytes(all_frames)


def render_pre_rendered_wav(path: Path, data: bytes, sample_rate: int = 44100) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(data)


def render_steps_wav(
    path: Path | str,
    steps: list[Step],
    bpm: int = 120,
    wave_shape: str = "square",
    volume: float = 0.25,
    sample_rate: int = 44100,
) -> None:
    """Bounce a step list to a single WAV file (offline render, no playback).

    Each step lasts an eighth note at the given tempo; notes sound for `gate` of
    the step and rests/tails are silence.
    """
    step_secs = 60.0 / max(1, bpm) / 2
    step_frames = max(1, int(step_secs * sample_rate))
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    total_samples = 0
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for step in steps:
            frames = bytearray()
            if step.note is None:
                frames += b"\x00\x00" * step_frames
            else:
                note_frames = max(
                    1,
                    int(step_frames * max(0.0, min(step.gate, 1.0))),
                )
                a_f = min(max(1, int(0.008 * sample_rate)), note_frames // 2)
                r_f = min(max(1, int(0.035 * sample_rate)), note_frames // 2)
                freq = midi_freq(step.note)
                for i in range(step_frames):
                    if i >= note_frames:
                        frames += b"\x00\x00"
                        continue
                    phase = (freq * ((total_samples + i) / sample_rate)) % 1.0
                    env = 1.0
                    if i < a_f:
                        env = i / a_f
                    if i > note_frames - r_f:
                        env = min(env, (note_frames - i) / r_f)
                    frames += struct.pack(
                        "<h", int(_osc_sample(phase, wave_shape) * amp * env)
                    )
            w.writeframes(bytes(frames))
            total_samples += step_frames


def play_pre_rendered_wav(path: Path):
    """Play a pre-rendered WAV file in a background thread."""
    duration: float = 0.0
    with wave.open(str(path), "r") as w:
        duration = float(w.getnframes()) / w.getframerate()

    def worker():
        try:
            if _IS_WINDOWS:
                import winsound

                winsound.PlaySound(
                    str(path), winsound.SND_FILENAME | winsound.SND_ASYNC
                )  # type: ignore
                time.sleep(duration + 0.1)
            else:
                _play_unix(path, duration)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()


def stop_all() -> None:
    """Immediately silence any audio currently playing.

    This is what makes the Stop button actually stop sound: the old version only
    cancelled the *scheduler*, leaving the in-flight note ringing out.
    """
    if _IS_WINDOWS:
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)  # type: ignore
        except Exception:
            pass
        return
    with _lock:
        procs = list(_active_procs)
        _active_procs.clear()
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass


def _play_unix(tmp: Path, duration: float) -> None:
    global _last_error
    players = (
        [["afplay", str(tmp)]]
        if _IS_MAC
        else [["aplay", "-q", str(tmp)], ["paplay", str(tmp)]]
    )
    errors: list[str] = []
    for cmd in players:
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except FileNotFoundError as exc:
            errors.append(str(exc))
            continue
        with _lock:
            _active_procs.add(p)
        try:
            _, err = p.communicate(timeout=max(1.0, duration + 3))
        except subprocess.TimeoutExpired:
            p.kill()
            err = b""
        finally:
            with _lock:
                _active_procs.discard(p)
        if p.returncode == 0:
            with _error_lock:
                _last_error = None
            return
        # A negative return code means we terminated it via stop_all(); not an error.
        if p.returncode is not None and p.returncode < 0:
            return
        errors.append(err.decode(errors="ignore") if err else f"exit {p.returncode}")
    with _error_lock:
        _last_error = "No Linux/macOS audio player worked: " + " | ".join(errors)


def play_note(
    note: int, duration: float = 0.18, wave_shape: str = "square", volume: float = 0.25
) -> None:
    """Play one generated note in a background thread.

    Uses a unique temp filename per note to avoid the Windows playback race where
    one thread deletes the WAV while another is still opening it. Backend errors
    are stored and surfaced via get_last_audio_error().
    """

    def worker():
        global _last_error
        tmp = (
            Path(tempfile.gettempdir())
            / f"mbseq_note_{os.getpid()}_{uuid.uuid4().hex}_{note}.wav"
        )
        try:
            make_wave(tmp, note, duration, wave_shape, volume)
            if _IS_WINDOWS:
                import winsound

                # SND_ASYNC: returns immediately and a new note interrupts the old
                # one (monophonic, matching the hardware). stop_all() purges it.
                winsound.PlaySound(str(tmp), winsound.SND_FILENAME | winsound.SND_ASYNC)
                time.sleep(duration + 0.05)
                with _error_lock:
                    _last_error = None
            else:
                _play_unix(tmp, duration)
        except Exception as exc:
            with _error_lock:
                _last_error = str(exc)
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True).start()

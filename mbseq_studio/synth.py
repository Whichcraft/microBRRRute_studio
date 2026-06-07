from __future__ import annotations
import math, struct, tempfile, wave, threading, os, sys, subprocess, time, uuid
from pathlib import Path

A4 = 440.0
_last_error: str | None = None

# Playback engine state -------------------------------------------------------
# The MicroBrute is a monophonic synth, so preview playback is monophonic too:
# starting a new note stops the previous one. Stop must silence audio *now*, so
# we track the in-flight subprocesses (Linux/macOS) and use SND_PURGE (Windows).
_IS_WINDOWS = sys.platform.startswith('win')
_IS_MAC = sys.platform == 'darwin'
_lock = threading.Lock()
_active_procs: set[subprocess.Popen] = set()


def get_last_audio_error() -> str | None:
    return _last_error


def midi_freq(note: int) -> float:
    return A4 * (2 ** ((note - 69) / 12))


def make_wave(path: Path, note: int, duration: float = 0.18, wave_shape: str = 'square',
              volume: float = 0.25, sample_rate: int = 44100) -> None:
    total = max(1, int(duration * sample_rate))
    freq = midi_freq(note)
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    attack = int(0.008 * sample_rate)
    release = int(0.035 * sample_rate)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total):
            t = i / sample_rate
            phase = (freq * t) % 1.0
            if wave_shape == 'sine':
                val = math.sin(2 * math.pi * phase)
            elif wave_shape == 'saw':
                val = 2 * phase - 1
            elif wave_shape == 'triangle':
                val = 4 * abs(phase - 0.5) - 1
            else:
                val = 1.0 if phase < 0.5 else -1.0
            env = 1.0
            if i < attack:
                env = i / max(1, attack)
            if i > total - release:
                env = min(env, (total - i) / max(1, release))
            frames += struct.pack('<h', int(val * amp * env))
        w.writeframes(frames)


def _osc_sample(phase: float, wave_shape: str) -> float:
    if wave_shape == 'sine':
        return math.sin(2 * math.pi * phase)
    if wave_shape == 'saw':
        return 2 * phase - 1
    if wave_shape == 'triangle':
        return 4 * abs(phase - 0.5) - 1
    return 1.0 if phase < 0.5 else -1.0


def render_steps_wav(path: Path | str, steps: list[int | None], bpm: int = 120,
                     wave_shape: str = 'square', volume: float = 0.25, gate: float = 0.82,
                     sample_rate: int = 44100) -> None:
    """Bounce a step list to a single WAV file (offline render, no playback).

    Each step lasts an eighth note at the given tempo; notes sound for `gate` of
    the step and rests/tails are silence.
    """
    step_secs = 60.0 / max(1, bpm) / 2
    step_frames = max(1, int(step_secs * sample_rate))
    note_frames = max(1, int(step_frames * gate))
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    attack = max(1, int(0.008 * sample_rate))
    release = max(1, int(0.035 * sample_rate))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for note in steps:
            frames = bytearray()
            if note is None:
                frames += b'\x00\x00' * step_frames
            else:
                freq = midi_freq(note)
                for i in range(step_frames):
                    if i >= note_frames:
                        frames += b'\x00\x00'
                        continue
                    phase = (freq * (i / sample_rate)) % 1.0
                    env = 1.0
                    if i < attack:
                        env = i / attack
                    if i > note_frames - release:
                        env = min(env, (note_frames - i) / release)
                    frames += struct.pack('<h', int(_osc_sample(phase, wave_shape) * amp * env))
            w.writeframes(bytes(frames))


def stop_all() -> None:
    """Immediately silence any audio currently playing.

    This is what makes the Stop button actually stop sound: the old version only
    cancelled the *scheduler*, leaving the in-flight note ringing out.
    """
    if _IS_WINDOWS:
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
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
    players = [['afplay', str(tmp)]] if _IS_MAC else [['aplay', '-q', str(tmp)], ['paplay', str(tmp)]]
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
            err = b''
        finally:
            with _lock:
                _active_procs.discard(p)
        if p.returncode == 0:
            _last_error = None
            return
        # A negative return code means we terminated it via stop_all(); not an error.
        if p.returncode is not None and p.returncode < 0:
            return
        errors.append(err.decode(errors='ignore') if err else f'exit {p.returncode}')
    _last_error = 'No Linux/macOS audio player worked: ' + ' | '.join(errors)


def play_note(note: int, duration: float = 0.18, wave_shape: str = 'square', volume: float = 0.25) -> None:
    """Play one generated note in a background thread.

    Uses a unique temp filename per note to avoid the Windows playback race where
    one thread deletes the WAV while another is still opening it. Backend errors
    are stored and surfaced via get_last_audio_error().
    """
    def worker():
        global _last_error
        tmp = Path(tempfile.gettempdir()) / f'mbseq_note_{os.getpid()}_{uuid.uuid4().hex}_{note}.wav'
        try:
            make_wave(tmp, note, duration, wave_shape, volume)
            if _IS_WINDOWS:
                import winsound
                # SND_ASYNC: returns immediately and a new note interrupts the old
                # one (monophonic, matching the hardware). stop_all() purges it.
                winsound.PlaySound(str(tmp), winsound.SND_FILENAME | winsound.SND_ASYNC)
                time.sleep(duration + 0.05)
                _last_error = None
            else:
                _play_unix(tmp, duration)
        except Exception as exc:
            _last_error = str(exc)
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()

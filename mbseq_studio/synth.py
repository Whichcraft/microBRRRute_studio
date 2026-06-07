from __future__ import annotations
import math, struct, tempfile, wave, threading, os, sys, subprocess, uuid
from pathlib import Path

A4 = 440.0
_last_error: str | None = None

def get_last_audio_error() -> str | None:
    return _last_error

def midi_freq(note: int) -> float:
    return A4 * (2 ** ((note - 69) / 12))

def make_wave(path: Path, note: int, duration: float = 0.18, wave_shape: str = 'square', volume: float = 0.25, sample_rate: int = 44100) -> None:
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

def play_note(note: int, duration: float = 0.18, wave_shape: str = 'square', volume: float = 0.25) -> None:
    """Play one generated note in a background thread.

    v3 reused the same temp filename for repeated notes. That can race on Windows
    during sequencer playback: one thread can delete/replace the WAV while another
    is still opening it. v4 uses a unique filename and stores the last backend error.
    """
    def worker():
        global _last_error
        tmp = Path(tempfile.gettempdir()) / f'mbseq_note_{os.getpid()}_{uuid.uuid4().hex}_{note}.wav'
        try:
            make_wave(tmp, note, duration, wave_shape, volume)
            if sys.platform.startswith('win'):
                import winsound
                winsound.PlaySound(str(tmp), winsound.SND_FILENAME)
            elif sys.platform == 'darwin':
                r = subprocess.run(['afplay', str(tmp)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if r.returncode != 0:
                    raise RuntimeError('afplay returned non-zero exit code')
            else:
                played = False
                errors = []
                for cmd in (['aplay', str(tmp)], ['paplay', str(tmp)]):
                    try:
                        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3)
                        if r.returncode == 0:
                            played = True
                            break
                        errors.append(r.stderr.decode(errors='ignore'))
                    except Exception as exc:
                        errors.append(str(exc))
                if not played:
                    raise RuntimeError('No Linux audio player worked: ' + ' | '.join(errors))
            _last_error = None
        except Exception as exc:
            _last_error = str(exc)
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()

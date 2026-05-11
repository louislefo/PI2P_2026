import os
import math
import struct
import wave
import tempfile
import subprocess
import threading
import time

def _generate_beep_wav(freq: int = 880, duration: float = 0.5, volume: float = 0.7) -> str:
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = b""
        for i in range(n_samples):
            sample = int(volume * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            data += struct.pack("<h", sample)
        wf.writeframes(data)
    return tmp.name

def _play_audio(freq: int = 880, duration: float = 0.5):
    wav_path = None
    try:
        wav_path = _generate_beep_wav(freq, duration)
        print(f"🔊 [AUDIO] Bip {freq}Hz × {duration}s...")
        result = subprocess.run(
            ["aplay", "-D", "plughw:0,0", wav_path],
            timeout=duration + 2, capture_output=True
        )
        if result.returncode != 0:
            subprocess.run(["aplay", wav_path], timeout=duration + 2, capture_output=True)
        print(f"✅ [AUDIO] Bip terminé")
    except FileNotFoundError:
        print("❌ [AUDIO] aplay introuvable")
    except Exception as e:
        print(f"❌ [AUDIO] Erreur : {e}")
    finally:
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

def play_pattern(pattern_name: str, freq: int = 880):
    patterns = {
        "single":  [(freq, 0.4)],
        "double":  [(freq, 0.2), (freq, 0.2)],
        "triple":  [(freq, 0.15), (freq, 0.15), (freq, 0.15)],
        "success": [(523, 0.15), (659, 0.15), (784, 0.3)],
        "error":   [(300, 0.3), (200, 0.4)],
    }
    sequence = patterns.get(pattern_name, patterns["single"])
    print(f"🔊 [AUDIO] Pattern '{pattern_name}' → {len(sequence)} bip(s)")
    
    def _play():
        for i, (f, d) in enumerate(sequence):
            _play_audio(f, d)
            if i < len(sequence) - 1:
                time.sleep(0.08)
                
    threading.Thread(target=_play, daemon=True).start()

_loop_proc = None
_loop_active = False

def play_wav_loop(filepath: str):
    global _loop_proc, _loop_active
    if not os.path.exists(filepath):
        print(f"❌ [AUDIO] Fichier introuvable : {filepath}")
        return
        
    stop_wav_loop()
    _loop_active = True
    print(f"🔊 [AUDIO] Lecture en boucle de {filepath}...")
    
    def _loop():
        global _loop_proc
        while _loop_active:
            try:
                _loop_proc = subprocess.Popen(
                    ["aplay", "-D", "plughw:0,0", filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                _loop_proc.wait()
                # Si aplay echoue avec plughw, on essaie sans
                if _loop_proc.returncode != 0 and _loop_active:
                    _loop_proc = subprocess.Popen(
                        ["aplay", filepath],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    _loop_proc.wait()
            except Exception as e:
                print(f"❌ [AUDIO] Erreur boucle: {e}")
                break

    threading.Thread(target=_loop, daemon=True).start()

def stop_wav_loop():
    global _loop_proc, _loop_active
    _loop_active = False
    if _loop_proc and _loop_proc.poll() is None:
        try:
            _loop_proc.terminate()
        except Exception:
            pass
    _loop_proc = None

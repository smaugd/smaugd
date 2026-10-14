"""Teste de fumaça usado no CI: carrega o Whisper de verdade e transcreve um áudio."""

import sys
import wave
from pathlib import Path

import numpy as np

from ditado_livre.audio import resample
from ditado_livre.transcribe.local_whisper import LocalWhisperTranscriber

transcriber = LocalWhisperTranscriber("tiny", "en", "auto")
transcriber.load()
print("dispositivo:", transcriber.active_device)
print("silêncio ->", repr(transcriber.transcribe(np.zeros(16_000, dtype=np.float32))))

path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if path and path.exists():
    with wave.open(str(path)) as wav:
        frames = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768
        if wav.getnchannels() > 1:
            frames = frames.reshape(-1, wav.getnchannels()).mean(axis=1)
        audio = resample(frames, wav.getframerate())
    text = transcriber.transcribe(audio)
    print("voz ->", repr(text))
    assert "hello" in text.lower() or "dictation" in text.lower(), text
else:
    print("sem áudio sintetizado; só o carregamento foi testado")

"""Interface comum dos motores de transcrição."""

from __future__ import annotations

import io
import wave
from typing import Protocol

import numpy as np

SAMPLE_RATE = 16_000


class Transcriber(Protocol):
    name: str

    def transcribe(self, audio: np.ndarray) -> str:
        """Recebe áudio mono float32 a 16 kHz e devolve o texto."""
        ...


class TranscriptionError(Exception):
    pass


def to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()

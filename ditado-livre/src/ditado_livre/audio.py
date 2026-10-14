"""Gravação do microfone."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import numpy as np

from .transcribe.base import SAMPLE_RATE

log = logging.getLogger(__name__)


def resample(audio: np.ndarray, from_rate: int, to_rate: int = SAMPLE_RATE) -> np.ndarray:
    if from_rate == to_rate or audio.size == 0:
        return audio.astype(np.float32, copy=False)
    duration = audio.size / from_rate
    target_size = int(round(duration * to_rate))
    source_times = np.arange(audio.size) / from_rate
    target_times = np.arange(target_size) / to_rate
    return np.interp(target_times, source_times, audio).astype(np.float32)


class Recorder:
    """Grava na taxa nativa do microfone e entrega áudio mono a 16 kHz, como o Whisper espera."""

    def __init__(self, on_level: Callable[[float], None] | None = None) -> None:
        self.on_level = on_level
        self._chunks: list[np.ndarray] = []
        self._stream = None
        self._rate = SAMPLE_RATE
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        import sounddevice as sd

        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self._rate = int(sd.query_devices(kind="input")["default_samplerate"])
            self._stream = sd.InputStream(
                samplerate=self._rate, channels=1, dtype="float32", callback=self._callback
            )
            self._stream.start()

    def _callback(self, indata, _frames, _time, status) -> None:
        if status:
            log.debug("Microfone: %s", status)
        chunk = indata[:, 0].copy()
        self._chunks.append(chunk)
        if self.on_level:
            self.on_level(float(np.sqrt(np.mean(chunk**2))))

    def stop(self) -> np.ndarray:
        with self._lock:
            stream, self._stream = self._stream, None
            if stream is None:
                return np.zeros(0, dtype=np.float32)
            stream.stop()
            stream.close()
            chunks, self._chunks = self._chunks, []
        audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
        return resample(audio, self._rate)

"""Transcrição local com faster-whisper (Whisper otimizado), na placa NVIDIA quando possível."""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

import numpy as np

from .base import TranscriptionError

log = logging.getLogger(__name__)


def add_nvidia_dll_dirs() -> list[str]:
    """No Windows, as DLLs do CUDA instaladas por pip ficam em site-packages/nvidia/*/bin."""
    if sys.platform != "win32":
        return []
    try:
        import nvidia  # pacote "namespace" criado por nvidia-cublas-cu12 / nvidia-cudnn-cu12
    except ImportError:
        return []
    added = []
    for root in getattr(nvidia, "__path__", []):
        for bin_dir in Path(root).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            added.append(str(bin_dir))
    return added


class LocalWhisperTranscriber:
    name = "local"

    def __init__(self, model_name: str, language: str, device: str = "auto") -> None:
        self.model_name = model_name
        self.language = language
        self.device = device
        self.active_device: str | None = None
        self._model = None
        self._lock = threading.Lock()

    def load(self) -> None:
        """Carrega o modelo (baixa da internet só na primeira vez)."""
        with self._lock:
            if self._model is not None:
                return
            add_nvidia_dll_dirs()
            from faster_whisper import WhisperModel

            attempts = {"cuda": [("cuda", "float16")], "cpu": [("cpu", "int8")]}.get(
                self.device, [("cuda", "float16"), ("cpu", "int8")]
            )
            errors = []
            for device, compute_type in attempts:
                try:
                    model = WhisperModel(self.model_name, device=device, compute_type=compute_type)
                    if device == "cuda":
                        # A falta de DLLs do CUDA só aparece na primeira inferência: testa já.
                        list(model.transcribe(np.zeros(16_000, dtype=np.float32), language=self.language)[0])
                    self._model = model
                    self.active_device = device
                    log.info("Whisper %s carregado em %s (%s)", self.model_name, device, compute_type)
                    return
                except Exception as exc:  # noqa: BLE001 - qualquer falha da GPU deve cair para a CPU
                    log.warning("Não deu para usar %s: %s", device, exc)
                    errors.append(f"{device}: {exc}")
            raise TranscriptionError("Não consegui carregar o Whisper. " + " | ".join(errors))

    def transcribe(self, audio: np.ndarray) -> str:
        self.load()
        segments, _info = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

"""Transcrição na nuvem pela Groq (plano gratuito com limite diário)."""

from __future__ import annotations

import httpx
import numpy as np

from ..config import GROQ_BASE_URL
from .base import TranscriptionError, to_wav_bytes


class GroqTranscriber:
    name = "groq"

    def __init__(self, api_key: str, model: str, language: str, client: httpx.Client | None = None) -> None:
        if not api_key:
            raise TranscriptionError("Falta a chave da Groq (groq_api_key) nas configurações")
        self.api_key = api_key
        self.model = model
        self.language = language
        self.client = client or httpx.Client(timeout=30.0)

    def transcribe(self, audio: np.ndarray) -> str:
        try:
            response = self.client.post(
                f"{GROQ_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={"model": self.model, "language": self.language, "response_format": "json", "temperature": "0"},
                files={"file": ("ditado.wav", to_wav_bytes(audio), "audio/wav")},
            )
            response.raise_for_status()
            return str(response.json()["text"]).strip()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise TranscriptionError(f"Groq falhou: {exc}") from exc

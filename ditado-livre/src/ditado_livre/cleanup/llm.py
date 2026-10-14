"""Limpeza 2: envia o texto para uma IA compatível com a API da OpenAI (Ollama local ou Groq)."""

from __future__ import annotations

import re

import httpx

from .prompts import build_messages


class CleanupError(Exception):
    """A IA falhou ou devolveu algo que não parece o texto ditado; o app usa o texto sem essa limpeza."""


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_WRAPPER_TAG = re.compile(r"</?transcricao>", re.IGNORECASE)


class LLMCleaner:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not model:
            raise ValueError("Nenhum modelo de IA configurado")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=timeout)

    def clean(self, transcript: str) -> str:
        if not transcript.strip():
            return transcript
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": self.model,
            "messages": build_messages(transcript),
            "temperature": 0,
            "stream": False,
        }
        try:
            response = self.client.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise CleanupError(f"IA indisponível: {exc}") from exc
        return _sanitize(content, transcript)


def _sanitize(content: str, transcript: str) -> str:
    text = _THINK_BLOCK.sub("", content)
    text = _WRAPPER_TAG.sub("", text).strip()
    if len(text) >= 2 and (text[0], text[-1]) in {('"', '"'), ("'", "'"), ("“", "”")}:
        text = text[1:-1].strip()
    if not text:
        raise CleanupError("IA devolveu texto vazio")
    # Uma resposta muito maior que o ditado indica que a IA "conversou" em vez de revisar.
    if len(text) > 2 * len(transcript) + 80:
        raise CleanupError("IA devolveu um texto muito maior que o ditado")
    return text

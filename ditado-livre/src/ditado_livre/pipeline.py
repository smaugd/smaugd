"""Orquestra o ditado: gravar → transcrever → limpar → colar → guardar no histórico."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from .cleanup.fillers import remove_fillers
from .cleanup.llm import CleanupError, LLMCleaner
from .config import GROQ_BASE_URL
from .hotkey import CANCEL, START, STOP
from .transcribe.base import SAMPLE_RATE, Transcriber, TranscriptionError

log = logging.getLogger(__name__)

IDLE, LOADING, RECORDING, PROCESSING, WARNING, ERROR = (
    "idle", "loading", "recording", "processing", "warning", "error",
)
StatusCallback = Callable[[str, str], None]


@dataclass
class DictationResult:
    raw: str
    text: str
    cleaned_by_ai: bool
    warning: str = ""


def build_transcriber(config: dict[str, Any]) -> Transcriber:
    if config["engine"] == "groq":
        from .transcribe.groq import GroqTranscriber

        return GroqTranscriber(config["groq_api_key"], config["groq_transcribe_model"], config["language"])
    from .transcribe.local_whisper import LocalWhisperTranscriber

    return LocalWhisperTranscriber(config["local_model"], config["language"], config["device"])


def build_cleaner(config: dict[str, Any]) -> LLMCleaner | None:
    if not config["ai_cleanup"]:
        return None
    timeout = float(config["llm_timeout_seconds"])
    if config["llm_provider"] == "groq":
        if not config["groq_api_key"]:
            log.warning("Limpeza com IA via Groq ligada, mas sem groq_api_key")
            return None
        return LLMCleaner(GROQ_BASE_URL, config["groq_llm_model"], config["groq_api_key"], timeout)
    return LLMCleaner(config["ollama_url"], config["ollama_model"], timeout=timeout)


class DictationPipeline:
    """A parte que transforma áudio em texto colado. Não sabe nada de teclado ou microfone."""

    def __init__(
        self,
        config: dict[str, Any],
        transcriber: Transcriber,
        cleaner: LLMCleaner | None,
        paste: Callable[[str], None],
        history=None,
    ) -> None:
        self.config = config
        self.transcriber = transcriber
        self.cleaner = cleaner
        self.paste = paste
        self.history = history

    def process(self, audio: np.ndarray) -> DictationResult | None:
        if audio.size < float(self.config["min_recording_seconds"]) * SAMPLE_RATE:
            return None
        if self.transcriber is None:
            raise TranscriptionError("Motor de transcrição não configurado (veja as configurações)")
        raw = self.transcriber.transcribe(audio).strip()
        text = raw
        if self.config["remove_fillers"]:
            text = remove_fillers(text, self.config["extra_filler_words"])
        cleaned_by_ai = False
        warning = ""
        if self.cleaner is not None and text:
            try:
                text = self.cleaner.clean(text)
                cleaned_by_ai = True
            except CleanupError as exc:
                log.warning("%s — colando sem a limpeza da IA", exc)
                warning = "IA indisponível: texto colado sem a limpeza"
        if not text:
            return None
        output = text + " " if self.config["append_space"] else text
        self.paste(output)
        if self.history is not None:
            self.history.add(raw, text, self.transcriber.name, cleaned_by_ai)
        return DictationResult(raw, text, cleaned_by_ai, warning)


class DictationController:
    """Liga atalho, microfone e pipeline; cada ditado é processado numa thread para não travar nada."""

    def __init__(self, recorder, pipeline: DictationPipeline, on_status: StatusCallback,
                 reset_hotkey: Callable[[], None] | None = None) -> None:
        self.recorder = recorder
        self.pipeline = pipeline
        self.on_status = on_status
        self.reset_hotkey = reset_hotkey
        self._busy = threading.Lock()

    def handle(self, event: str) -> None:
        if event == START:
            if self._busy.locked():
                self.on_status(WARNING, "Aguarde: ainda processando o ditado anterior")
                if self.reset_hotkey:
                    self.reset_hotkey()
                return
            try:
                self.recorder.start()
            except Exception as exc:  # noqa: BLE001
                log.exception("Microfone")
                self.on_status(ERROR, f"Microfone indisponível: {exc}")
                if self.reset_hotkey:
                    self.reset_hotkey()
                return
            self.on_status(RECORDING, "Gravando… solte o atalho para terminar (Esc cancela)")
        elif event == STOP:
            if not self.recorder.recording:
                return
            audio = self.recorder.stop()
            self._busy.acquire()
            threading.Thread(target=self._process, args=(audio,), daemon=True).start()
        elif event == CANCEL:
            self.recorder.stop()
            self.on_status(IDLE, "Ditado cancelado")

    def _process(self, audio: np.ndarray) -> None:
        try:
            self.on_status(PROCESSING, "Transcrevendo…")
            result = self.pipeline.process(audio)
            if result is None:
                self.on_status(IDLE, "Nada foi ouvido")
            elif result.warning:
                self.on_status(WARNING, result.warning)
            else:
                self.on_status(IDLE, "Pronto")
        except TranscriptionError as exc:
            log.error("%s", exc)
            self.on_status(ERROR, str(exc))
        except Exception as exc:  # noqa: BLE001 - erro inesperado não pode derrubar o app
            log.exception("Erro no ditado")
            self.on_status(ERROR, f"Erro: {exc}")
        finally:
            self._busy.release()

"""Configurações do app, guardadas em um arquivo JSON legível e editável."""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    # Atalho: teclas separadas por "+". Nomes: ctrl, alt, shift, win, ou uma tecla (f9, a, space...).
    "hotkey": "ctrl+win",
    # "hold" = segure para falar e solte para terminar; "toggle" = aperte para começar e de novo para terminar.
    "hotkey_mode": "hold",
    "language": "pt",
    # Motor de transcrição: "local" (Whisper no seu PC) ou "groq" (nuvem, plano gratuito com limites).
    "engine": "local",
    "local_model": "large-v3-turbo",
    # "auto" tenta a placa NVIDIA (cuda) e cai para o processador (cpu) se não conseguir.
    "device": "auto",
    "groq_api_key": "",
    "groq_transcribe_model": "whisper-large-v3-turbo",
    # Limpeza 1: regras simples que removem vícios de linguagem.
    "remove_fillers": True,
    "extra_filler_words": [],
    # Limpeza 2: IA que corrige pontuação, números, autocorreções faladas e listas.
    "ai_cleanup": True,
    # "ollama" (IA local, grátis) ou "groq" (nuvem, plano gratuito).
    "llm_provider": "ollama",
    "ollama_url": "http://localhost:11434/v1",
    "ollama_model": "qwen2.5:3b",
    "groq_llm_model": "llama-3.1-8b-instant",
    "llm_timeout_seconds": 10,
    "append_space": True,
    "restore_clipboard": True,
    "min_recording_seconds": 0.3,
    "history_size": 200,
}

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def app_dir() -> Path:
    """Pasta onde ficam configuração, histórico e log."""
    override = os.environ.get("DITADO_LIVRE_HOME")
    if override:
        return Path(override)
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "DitadoLivre"
    return Path.home() / ".config" / "ditado-livre"


def config_path() -> Path:
    return app_dir() / "config.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Lê a configuração; chaves ausentes recebem o valor padrão e o arquivo é (re)criado."""
    path = path or config_path()
    config = copy.deepcopy(DEFAULTS)
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Não consegui ler {path}: {exc}") from exc
        if not isinstance(saved, dict):
            raise ConfigError(f"{path} deveria conter um objeto JSON")
        config.update({k: v for k, v in saved.items() if k in DEFAULTS})
    save_config(config, path)
    return config


def save_config(config: dict[str, Any], path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


class ConfigError(Exception):
    pass

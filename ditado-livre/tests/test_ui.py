"""Partes da interface que dá para testar sem abrir janelas."""

import pytest

pytest.importorskip("tkinter")

from ditado_livre.config import DEFAULTS  # noqa: E402
from ditado_livre.history_window import matches, short_time  # noqa: E402
from ditado_livre.overlay import format_elapsed, level_to_height  # noqa: E402
from ditado_livre.settings_window import (  # noqa: E402
    MODELS, _label, _value, form_to_config, format_hotkey, normalize_hotkey,
)
from ditado_livre.tray import make_icon_image  # noqa: E402


def base_form(**changes):
    form = {
        "hotkey": "Ctrl + Win", "hotkey_mode": "hold", "engine": "local", "local_model": "large-v3-turbo",
        "device": "auto", "language": "pt", "groq_api_key": "", "remove_fillers": True,
        "extra_filler_words": "tipo assim,  sabe ,", "ai_cleanup": True, "llm_provider": "ollama",
        "ollama_model": "", "ollama_url": "", "groq_llm_model": "", "restore_clipboard": True,
        "append_space": False,
    }
    form.update(changes)
    return form


def test_hotkey_display_roundtrip():
    assert format_hotkey("ctrl+win") == "Ctrl + Win"
    assert format_hotkey("ctrl+shift+space") == "Ctrl + Shift + Space"
    assert format_hotkey("f9") == "F9"
    assert normalize_hotkey("Win + Ctrl") == "ctrl+win"
    assert normalize_hotkey("shift + ctrl + d") == "ctrl+shift+d"
    with pytest.raises(ValueError):
        normalize_hotkey("Esc")


def test_form_to_config():
    config = form_to_config(dict(DEFAULTS), base_form(hotkey="Ctrl + Alt"))
    assert config["hotkey"] == "ctrl+alt"
    assert config["extra_filler_words"] == ["tipo assim", "sabe"]
    assert config["ollama_model"] == DEFAULTS["ollama_model"]  # vazio volta ao padrão
    assert config["append_space"] is False


@pytest.mark.parametrize("changes", [
    {"hotkey": ""},
    {"engine": "groq"},
    {"llm_provider": "groq"},
])
def test_form_to_config_errors(changes):
    with pytest.raises(ValueError):
        form_to_config(dict(DEFAULTS), base_form(**changes))


def test_groq_with_key_is_fine():
    config = form_to_config(dict(DEFAULTS), base_form(engine="groq", llm_provider="groq", groq_api_key=" k "))
    assert config["groq_api_key"] == "k"


def test_option_labels():
    assert _value(MODELS, _label(MODELS, "small")) == "small"
    assert _label(MODELS, "desconhecido") == "desconhecido"


def test_overlay_helpers():
    assert level_to_height(0.0) == 0.0
    assert 0 < level_to_height(0.02) < level_to_height(0.05) <= 1.0
    assert level_to_height(5.0) == 1.0
    assert format_elapsed(7.9) == "0:07" and format_elapsed(65) == "1:05"


def test_history_helpers():
    assert short_time("2026-10-14T09:05:33") == "14/10 09:05"
    assert short_time("quebrado") == "quebrado"
    item = {"final": "Amanhã às 3", "bruto": "amanhã às três"}
    assert matches(item, "") and matches(item, "TRÊS") and not matches(item, "reunião")


def test_tray_icon():
    image = make_icon_image(size=32)
    assert image.size == (32, 32) and image.mode == "RGBA"

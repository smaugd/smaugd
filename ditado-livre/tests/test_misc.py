import io
import json
import wave

import httpx
import numpy as np
import pytest

from ditado_livre.audio import resample
from ditado_livre.config import DEFAULTS, ConfigError, load_config
from ditado_livre.output import Paster
from ditado_livre.transcribe.base import TranscriptionError, to_wav_bytes
from ditado_livre.transcribe.groq import GroqTranscriber


def test_config_created_with_defaults_and_merged(tmp_path):
    path = tmp_path / "config.json"
    assert load_config(path) == DEFAULTS
    path.write_text(json.dumps({"engine": "groq", "chave_estranha": 1}), encoding="utf-8")
    config = load_config(path)
    assert config["engine"] == "groq" and "chave_estranha" not in config
    assert json.loads(path.read_text(encoding="utf-8"))["hotkey"] == "ctrl+win"


def test_config_invalid_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{quebrado", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_resample_48k_to_16k():
    audio = np.sin(np.linspace(0, 100, 48_000)).astype(np.float32)
    out = resample(audio, 48_000)
    assert out.dtype == np.float32 and out.size == 16_000


def test_wav_bytes_roundtrip():
    data = to_wav_bytes(np.full(1600, 2.0, dtype=np.float32))
    with wave.open(io.BytesIO(data)) as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getnframes()) == (16_000, 1, 1600)
        assert np.frombuffer(wav.readframes(1), dtype="<i2")[0] == 32767  # valor recortado


def test_paster_restores_previous_text():
    clipboard = ["anterior"]
    events = []
    paster = Paster(
        copy=lambda t: (clipboard.__setitem__(0, t), events.append(("copy", t))),
        read=lambda: clipboard[0],
        send_paste=lambda: events.append(("ctrl+v", clipboard[0])),
        sleep=lambda s: None,
    )
    paster.paste("ditado")
    assert events == [("copy", "ditado"), ("ctrl+v", "ditado"), ("copy", "anterior")]


def test_paster_without_restore_or_with_unreadable_clipboard():
    copies = []

    def broken_read():
        raise RuntimeError("ocupado")

    Paster(copy=copies.append, read=broken_read, send_paste=lambda: None, sleep=lambda s: None).paste("a")
    Paster(restore_clipboard=False, copy=copies.append, read=lambda: "x", send_paste=lambda: None,
           sleep=lambda s: None).paste("b")
    assert copies == ["a", "b"]


def test_groq_transcriber():
    def handler(request):
        assert request.url.path == "/openai/v1/audio/transcriptions"
        assert request.headers["authorization"] == "Bearer k"
        body = request.content
        assert b'name="model"' in body and b"whisper-large-v3-turbo" in body and b"RIFF" in body
        return httpx.Response(200, json={"text": " Olá, mundo. "})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    transcriber = GroqTranscriber("k", "whisper-large-v3-turbo", "pt", client=client)
    assert transcriber.transcribe(np.zeros(16_000, dtype=np.float32)) == "Olá, mundo."


def test_groq_errors():
    with pytest.raises(TranscriptionError):
        GroqTranscriber("", "m", "pt")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429, text="limite")))
    with pytest.raises(TranscriptionError):
        GroqTranscriber("k", "m", "pt", client=client).transcribe(np.zeros(16_000, dtype=np.float32))

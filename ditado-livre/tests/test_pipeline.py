import threading

import numpy as np
import pytest

from conftest import FakeTranscriber
from ditado_livre.cleanup.llm import CleanupError
from ditado_livre.history import History
from ditado_livre.hotkey import CANCEL, START, STOP
from ditado_livre.pipeline import (
    ERROR, IDLE, PROCESSING, RECORDING, WARNING,
    DictationController, DictationPipeline, build_cleaner,
)
from ditado_livre.transcribe.base import TranscriptionError


class FakeCleaner:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.received = result, error, None

    def clean(self, text):
        self.received = text
        if self.error:
            raise self.error
        return self.result


def test_full_flow_with_ai(config, one_second, tmp_path):
    pasted = []
    history = History(tmp_path / "h.sqlite3")
    cleaner = FakeCleaner(result="Amanhã às 3, eu passo aí.")
    pipeline = DictationPipeline(
        config, FakeTranscriber("Hum, amanhã às duas, não, às três eu passo aí"), cleaner, pasted.append, history
    )
    result = pipeline.process(one_second)
    assert cleaner.received == "Amanhã às duas, não, às três eu passo aí"  # vícios já removidos
    assert pasted == ["Amanhã às 3, eu passo aí. "]
    assert result.cleaned_by_ai and not result.warning
    saved = history.recent()
    assert saved[0]["bruto"].startswith("Hum") and saved[0]["final"] == "Amanhã às 3, eu passo aí."


def test_ai_failure_still_pastes(config, one_second):
    pasted = []
    pipeline = DictationPipeline(
        config, FakeTranscriber("ahn, oi tudo bem"), FakeCleaner(error=CleanupError("offline")), pasted.append
    )
    result = pipeline.process(one_second)
    assert pasted == ["Oi tudo bem "] or pasted == ["oi tudo bem "]
    assert not result.cleaned_by_ai and result.warning


def test_options_off(config, one_second):
    config.update(remove_fillers=False, append_space=False)
    pasted = []
    DictationPipeline(config, FakeTranscriber("hum oi"), None, pasted.append).process(one_second)
    assert pasted == ["hum oi"]


def test_too_short_or_silent_does_nothing(config):
    pasted = []
    transcriber = FakeTranscriber("oi")
    pipeline = DictationPipeline(config, transcriber, None, pasted.append)
    assert pipeline.process(np.zeros(1000, dtype=np.float32)) is None
    assert transcriber.calls == 0
    pipeline.transcriber = FakeTranscriber("  ")
    assert pipeline.process(np.zeros(16_000, dtype=np.float32)) is None
    assert pasted == []


def test_missing_transcriber(config, one_second):
    with pytest.raises(TranscriptionError):
        DictationPipeline(config, None, None, print).process(one_second)


def test_build_cleaner(config):
    assert build_cleaner({**config, "ai_cleanup": False}) is None
    assert build_cleaner({**config, "llm_provider": "groq", "groq_api_key": ""}) is None
    ollama = build_cleaner(config)
    assert ollama.url == "http://localhost:11434/v1/chat/completions"
    groq = build_cleaner({**config, "llm_provider": "groq", "groq_api_key": "k"})
    assert groq.url == "https://api.groq.com/openai/v1/chat/completions" and groq.api_key == "k"


class FakeRecorder:
    def __init__(self, fail=False):
        self.recording, self.fail = False, fail

    def start(self):
        if self.fail:
            raise OSError("sem microfone")
        self.recording = True

    def stop(self):
        self.recording = False
        return np.zeros(16_000, dtype=np.float32)


def run_controller(config, transcriber, recorder=None, events=(START, STOP)):
    statuses, pasted, done = [], [], threading.Event()

    def on_status(status, message):
        statuses.append(status)
        if status in (IDLE, WARNING, ERROR) and PROCESSING in statuses:
            done.set()

    pipeline = DictationPipeline(config, transcriber, None, pasted.append)
    controller = DictationController(recorder or FakeRecorder(), pipeline, on_status)
    for event in events:
        controller.handle(event)
    return controller, statuses, pasted, done


def test_controller_records_and_processes(config):
    _, statuses, pasted, done = run_controller(config, FakeTranscriber("Olá."))
    assert done.wait(5)
    assert statuses[:2] == [RECORDING, PROCESSING] and statuses[-1] == IDLE
    assert pasted == ["Olá. "]


def test_controller_cancel(config):
    _, statuses, pasted, _ = run_controller(config, FakeTranscriber("Olá."), events=(START, CANCEL, STOP))
    assert statuses == [RECORDING, IDLE] and pasted == []


def test_controller_reports_errors(config):
    class Broken:
        name = "x"

        def transcribe(self, audio):
            raise TranscriptionError("Groq falhou")

    _, statuses, _, done = run_controller(config, Broken())
    assert done.wait(5) and statuses[-1] == ERROR

    _, statuses, _, _ = run_controller(config, FakeTranscriber("x"), FakeRecorder(fail=True), events=(START,))
    assert statuses == [ERROR]


def test_controller_refuses_while_busy(config):
    release = threading.Event()

    class Slow:
        name = "slow"

        def transcribe(self, audio):
            release.wait(5)
            return "Oi."

    resets = []
    statuses = []
    pipeline = DictationPipeline(config, Slow(), None, lambda t: None)
    controller = DictationController(FakeRecorder(), pipeline, lambda s, m: statuses.append(s),
                                     reset_hotkey=lambda: resets.append(1))
    controller.handle(START)
    controller.handle(STOP)
    controller.handle(START)
    assert WARNING in statuses and resets == [1]
    release.set()

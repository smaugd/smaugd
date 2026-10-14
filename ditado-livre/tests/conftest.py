import numpy as np
import pytest

from ditado_livre.config import DEFAULTS


@pytest.fixture
def config():
    return dict(DEFAULTS)


@pytest.fixture
def one_second():
    return np.zeros(16_000, dtype=np.float32)


class FakeTranscriber:
    name = "fake"

    def __init__(self, text):
        self.text = text
        self.calls = 0

    def transcribe(self, audio):
        self.calls += 1
        return self.text

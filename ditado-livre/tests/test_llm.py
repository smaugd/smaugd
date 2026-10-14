import json

import httpx
import pytest

from ditado_livre.cleanup.llm import CleanupError, LLMCleaner
from ditado_livre.cleanup.prompts import SYSTEM_PROMPT


def make_cleaner(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LLMCleaner("http://localhost:11434/v1/", "qwen2.5:3b", client=client, **kwargs)


def reply(content):
    return lambda request: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_sends_openai_compatible_request():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return reply("Amanhã às 3, eu passo aí.")(request)

    cleaner = make_cleaner(handler, api_key="segredo")
    assert cleaner.clean("amanhã às duas não às três eu passo aí") == "Amanhã às 3, eu passo aí."
    assert seen["url"] == "http://localhost:11434/v1/chat/completions"
    assert seen["auth"] == "Bearer segredo"
    assert seen["body"]["model"] == "qwen2.5:3b"
    assert seen["body"]["temperature"] == 0
    assert seen["body"]["messages"][0]["content"] == SYSTEM_PROMPT
    assert "amanhã às duas" in seen["body"]["messages"][1]["content"]


def test_no_auth_header_without_key():
    def handler(request):
        assert "authorization" not in request.headers
        return reply("Oi.")(request)

    assert make_cleaner(handler).clean("oi") == "Oi."


def test_empty_text_skips_request():
    def handler(request):
        raise AssertionError("não deveria chamar a IA")

    assert make_cleaner(handler).clean("   ") == "   "


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("<think>pensando...</think>\nOlá, tudo bem?", "Olá, tudo bem?"),
        ('"Olá, tudo bem?"', "Olá, tudo bem?"),
        ("“Olá, tudo bem?”", "Olá, tudo bem?"),
        ("<transcricao>\nOlá, tudo bem?\n</transcricao>", "Olá, tudo bem?"),
    ],
)
def test_sanitizes_model_output(content, expected):
    assert make_cleaner(reply(content)).clean("olá tudo bem") == expected


@pytest.mark.parametrize(
    "handler",
    [
        reply(""),
        reply("Claro! Aqui está uma longa explicação sobre reuniões... " * 10),
        lambda request: httpx.Response(500, text="erro"),
        lambda request: httpx.Response(200, json={"inesperado": True}),
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("recusado")),
    ],
)
def test_failures_raise_cleanup_error(handler):
    with pytest.raises(CleanupError):
        make_cleaner(handler).clean("que horas é a reunião")

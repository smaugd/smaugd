"""Limpeza 1: remove vícios de linguagem com regras simples (rápido, sem IA).

Só removemos sons de hesitação que nunca são palavras de verdade. Palavras como
"tipo", "né" e "é" ficam para a IA decidir pelo contexto, porque às vezes têm sentido.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Padrões de hesitação: hum, hmm, ahn, ããã, eh, éé, uh, uhm, aham não (é "sim").
_HESITATIONS = [
    r"h+u+m+",
    r"h+m+",
    r"u+h+m*",
    r"a+h+n+",
    r"ã+h*",
    r"e+h+",
    r"é{2,}",
    r"a{3,}h*",
]


def _build_pattern(extra_words: Iterable[str]) -> re.Pattern[str]:
    alternatives = list(_HESITATIONS) + [re.escape(w.strip()) for w in extra_words if w.strip()]
    words = "|".join(alternatives)
    # Vírgula antes (opcional), a palavra inteira e a pontuação colada nela.
    return re.compile(rf"(?:,\s*)?(?<![\w-])(?:{words})(?![\w-])(?P<punct>[,…!?.]*)", re.IGNORECASE)


def _replacement(match: re.Match[str]) -> str:
    punct = match.group("punct").replace("...", "…")
    before = match.string[: match.start()].rstrip()
    if not before or before.endswith((".", "!", "?", "…")):
        # A hesitação abria a frase: marca para a palavra seguinte virar maiúscula.
        return _SENTENCE_START
    # Um ponto final (ou ! ?) depois da hesitação encerrava a frase: mantém. Reticências e vírgulas eram só pausa.
    for mark in ("?", "!", "."):
        if mark in punct:
            return mark
    return ""


_SENTENCE_START = "\x00"
_DEFAULT_PATTERN = _build_pattern([])


def remove_fillers(text: str, extra_words: Iterable[str] = ()) -> str:
    extra_words = list(extra_words)
    pattern = _build_pattern(extra_words) if extra_words else _DEFAULT_PATTERN
    cleaned = pattern.sub(_replacement, text)
    cleaned = re.sub(r"\x00[\s\x00]*(\w?)", lambda m: " " + m.group(1).upper(), cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)  # espaço antes de pontuação
    cleaned = re.sub(r"([,;:])\1+", r"\1", cleaned)  # vírgulas duplicadas
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"^[,;:.…!?]+\s*", "", cleaned)  # pontuação que sobrou no início
    return cleaned

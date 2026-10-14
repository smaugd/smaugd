import pytest

from ditado_livre.cleanup.fillers import remove_fillers


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hum, eu queria marcar uma reunião.", "Eu queria marcar uma reunião."),
        ("Eu, hum, queria marcar.", "Eu queria marcar."),
        ("Ahn... amanhã eu passo aí", "Amanhã eu passo aí"),
        ("Fui lá, hum.", "Fui lá."),
        ("Fui lá. Hum. Depois voltei.", "Fui lá. Depois voltei."),
        ("éé eu acho que sim", "Eu acho que sim"),
        ("Hmm, será? Uhm, talvez.", "Será? Talvez."),
        # Palavras de verdade ficam: "um", "é", "humano", "ah" sozinho e reticências.
        ("É um humano. Ele disse... depois saiu.", "É um humano. Ele disse... depois saiu."),
        ("hum", ""),
        ("", ""),
    ],
)
def test_remove_fillers(raw, expected):
    assert remove_fillers(raw) == expected


def test_extra_words():
    assert remove_fillers("Tipo assim, eu fui.", ["tipo assim"]) == "Eu fui."

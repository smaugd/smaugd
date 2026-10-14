import pytest

from ditado_livre.hotkey import CANCEL, START, STOP, HotkeyState, normalize_name, parse_hotkey


def test_parse_hotkey_aliases():
    assert parse_hotkey("Ctrl + Win") == frozenset({"ctrl", "win"})
    assert parse_hotkey("ctrl_l+cmd") == frozenset({"ctrl", "win"})
    assert normalize_name("alt_gr") == "alt"


@pytest.mark.parametrize("bad", ["", "esc", "ctrl+esc"])
def test_parse_hotkey_rejects(bad):
    with pytest.raises(ValueError):
        parse_hotkey(bad)


def test_hold_mode_start_and_stop():
    state = HotkeyState(parse_hotkey("ctrl+win"), "hold")
    assert state.press("ctrl") is None
    assert state.press("win") == START
    assert state.press("win") is None  # repetição automática da tecla segurada
    assert state.press("ctrl") is None
    assert state.release("win") == STOP
    assert state.release("ctrl") is None
    assert not state.modifiers_down()


def test_hold_mode_any_order():
    state = HotkeyState(parse_hotkey("ctrl+win"), "hold")
    assert state.press("win") is None
    assert state.press("ctrl") == START
    assert state.release("ctrl") == STOP
    assert state.modifiers_down()  # Win ainda apertado: colar deve esperar


def test_toggle_mode():
    state = HotkeyState(parse_hotkey("f9"), "toggle")
    assert state.press("f9") == START
    assert state.release("f9") is None
    assert state.press("f9") == STOP
    assert state.release("f9") is None
    assert state.press("f9") == START


def test_escape_cancels_only_when_active():
    state = HotkeyState(parse_hotkey("f9"), "toggle")
    assert state.press("esc") is None
    state.release("esc")
    assert state.press("f9") == START
    assert state.press("esc") == CANCEL
    state.release("esc")
    state.release("f9")
    assert state.press("f9") == START


def test_other_keys_do_not_trigger():
    state = HotkeyState(parse_hotkey("ctrl+win"), "hold")
    assert state.press("ctrl") is None
    assert state.press("c") is None
    assert state.release("c") is None
    assert state.release("ctrl") is None


def test_reset_after_refused_start():
    state = HotkeyState(parse_hotkey("f9"), "toggle")
    assert state.press("f9") == START
    state.release("f9")
    state.reset()  # app ocupado recusou o início
    assert state.press("f9") == START

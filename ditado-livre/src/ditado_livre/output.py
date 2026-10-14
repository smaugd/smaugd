"""Coloca o texto no aplicativo ativo: copia, aperta Ctrl+V e devolve o que estava na área de transferência."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

log = logging.getLogger(__name__)


def _send_ctrl_v() -> None:
    from pynput.keyboard import Controller, Key

    keyboard = Controller()
    with keyboard.pressed(Key.ctrl):
        keyboard.tap("v")


class Paster:
    def __init__(
        self,
        restore_clipboard: bool = True,
        copy: Callable[[str], None] | None = None,
        read: Callable[[], str] | None = None,
        send_paste: Callable[[], None] = _send_ctrl_v,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if copy is None or read is None:
            import pyperclip

            copy = copy or pyperclip.copy
            read = read or pyperclip.paste
        self.restore_clipboard = restore_clipboard
        self._copy = copy
        self._read = read
        self._send_paste = send_paste
        self._sleep = sleep

    def paste(self, text: str) -> None:
        previous = None
        if self.restore_clipboard:
            try:
                previous = self._read()
            except Exception as exc:  # noqa: BLE001 - área de transferência ocupada não deve impedir o ditado
                log.debug("Não li a área de transferência: %s", exc)
        self._copy(text)
        self._sleep(0.05)
        self._send_paste()
        self._sleep(0.3)  # dá tempo do app ler antes de restaurar
        # Só texto pode ser restaurado; se antes havia imagem/arquivo (leitura vazia), o ditado fica copiado.
        if previous:
            self._copy(previous)

"""Atalho global: segurar para falar ou apertar para ligar/desligar."""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable

START, STOP, CANCEL = "start", "stop", "cancel"

_ALIASES = {
    "ctrl_l": "ctrl", "ctrl_r": "ctrl", "control": "ctrl",
    "cmd": "win", "cmd_l": "win", "cmd_r": "win", "super": "win", "windows": "win",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "shift_l": "shift", "shift_r": "shift",
    "escape": "esc",
}
MODIFIERS = {"ctrl", "win", "alt", "shift"}


def normalize_name(name: str) -> str:
    name = name.strip().lower()
    return _ALIASES.get(name, name)


def parse_hotkey(text: str) -> frozenset[str]:
    keys = frozenset(normalize_name(part) for part in text.split("+") if part.strip())
    if not keys:
        raise ValueError(f"Atalho inválido: {text!r}")
    if "esc" in keys:
        raise ValueError("Esc é reservado para cancelar o ditado")
    return keys


class HotkeyState:
    """Lógica pura do atalho (sem teclado de verdade), para poder ser testada."""

    def __init__(self, combo: frozenset[str], mode: str = "hold") -> None:
        if mode not in ("hold", "toggle"):
            raise ValueError("hotkey_mode deve ser 'hold' ou 'toggle'")
        self.combo = combo
        self.mode = mode
        self.pressed: set[str] = set()
        self.active = False
        self._combo_down = False

    def press(self, name: str) -> str | None:
        self.pressed.add(name)
        if name == "esc" and self.active:
            self.active = False
            return CANCEL
        if self.combo <= self.pressed and not self._combo_down:
            self._combo_down = True  # ignora a repetição automática de tecla segurada
            if self.mode == "hold":
                self.active = True
                return START
            self.active = not self.active
            return START if self.active else STOP
        return None

    def release(self, name: str) -> str | None:
        self.pressed.discard(name)
        if name in self.combo:
            self._combo_down = False
            if self.mode == "hold" and self.active:
                self.active = False
                return STOP
        return None

    def reset(self) -> None:
        self.active = False

    def modifiers_down(self) -> bool:
        return bool(self.pressed & MODIFIERS)


def _key_name(key) -> str | None:
    """Converte uma tecla do pynput em nome simples ("ctrl", "win", "a", "f9"...)."""
    name = getattr(key, "name", None)
    if name:
        return normalize_name(name)
    vk = getattr(key, "vk", None)
    # Com Ctrl apertado o Windows entrega caracteres de controle; o código virtual é confiável.
    if vk is not None and (48 <= vk <= 57 or 65 <= vk <= 90):
        return chr(vk).lower()
    char = getattr(key, "char", None)
    return char.lower() if char else None


class HotkeyListener:
    def __init__(self, hotkey: str, mode: str, on_event: Callable[[str], None]) -> None:
        self.state = HotkeyState(parse_hotkey(hotkey), mode)
        self.on_event = on_event
        self._listener = None
        self._controller = None
        self._lock = threading.Lock()

    def start(self) -> None:
        from pynput import keyboard

        self._controller = keyboard.Controller()
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()

    def _on_press(self, key) -> None:
        name = _key_name(key)
        if name is None:
            return
        with self._lock:
            event = self.state.press(name)
        if event == START or (event == STOP and self.state.mode == "toggle"):
            self._mask_start_menu()
        if event:
            self.on_event(event)

    def _on_release(self, key) -> None:
        name = _key_name(key)
        if name is None:
            return
        with self._lock:
            event = self.state.release(name)
        if event:
            self.on_event(event)

    def _mask_start_menu(self) -> None:
        """Soltar a tecla Windows sozinha abre o menu Iniciar; uma tecla "vazia" (vk 0xE8) evita isso."""
        if sys.platform != "win32" or "win" not in self.state.combo or self._controller is None:
            return
        from pynput.keyboard import KeyCode

        self._controller.tap(KeyCode.from_vk(0xE8))

    def wait_modifiers_released(self, timeout: float = 2.0) -> None:
        """Espera soltar Ctrl/Win/Alt/Shift antes de colar (senão Win+V abriria outra coisa)."""
        deadline = time.monotonic() + timeout
        while self.state.modifiers_down() and time.monotonic() < deadline:
            time.sleep(0.02)

    def reset(self) -> None:
        with self._lock:
            self.state.reset()

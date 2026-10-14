"""Abrir o Ditado Livre junto com o Windows (registro do usuário, sem precisar de administrador)."""

from __future__ import annotations

import sys
from pathlib import Path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE = "DitadoLivre"


def supported() -> bool:
    return sys.platform == "win32"


def launch_command() -> str:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return f'"{pythonw if pythonw.exists() else exe}" -m ditado_livre'


def is_enabled() -> bool:
    if not supported():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _VALUE)
            return True
    except OSError:
        return False


def set_enabled(enabled: bool) -> None:
    if not supported():
        return
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _VALUE, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, _VALUE)
            except FileNotFoundError:
                pass

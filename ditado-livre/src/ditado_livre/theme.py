"""Aparência: cores, fontes, modo escuro do Windows e nitidez em telas de alta resolução."""

from __future__ import annotations

import sys
import tkinter as tk

ACCENT = "#4f8cff"
RECORDING = "#ff4d5e"
SUCCESS = "#2fbf71"
WARNING = "#ffb020"
ERROR = "#ff5c5c"
MUTED = "#9aa0aa"

# Pílula flutuante (sempre escura, como um "toast" do sistema).
PILL_BG = "#17181c"
PILL_BORDER = "#2c2e35"
PILL_TEXT = "#f2f3f5"
PILL_SUBTEXT = "#a4a9b3"

FONT_FAMILY = "Segoe UI Variable Text" if sys.platform == "win32" else "DejaVu Sans"
FONT_FALLBACK = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def enable_high_dpi() -> None:
    """Sem isso o Windows "estica" a janela e o texto fica borrado em telas com zoom (125%, 150%...)."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def ui_scale(widget: tk.Misc) -> float:
    """Fator de escala da tela (1.0 = 100%, 1.5 = 150%)."""
    return max(1.0, widget.winfo_fpixels("1i") / 96.0)


def font(widget: tk.Misc, size: int, weight: str = "normal") -> tuple[str, int, str]:
    families = set(widget.tk.call("font", "families"))
    family = FONT_FAMILY if FONT_FAMILY in families else FONT_FALLBACK
    return (family, size, weight)


def windows_prefers_dark() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except OSError:
        return False


def apply_theme(root: tk.Tk, dark: bool | None = None) -> bool:
    """Aplica o tema Sun Valley (visual do Windows 11) aos widgets ttk. Devolve se ficou escuro."""
    dark = windows_prefers_dark() if dark is None else dark
    try:
        import sv_ttk

        sv_ttk.set_theme("dark" if dark else "light", root)
        # O tema só pinta o fundo das janelas no evento <<ThemeChanged>>, que não chega a uma janela
        # escondida (a principal do app fica sempre escondida): aplica as cores na hora.
        root.tk.call("configure_colors")
    except Exception:  # noqa: BLE001 - sem o tema, o ttk padrão continua funcionando
        pass
    return dark


def style_titlebar(window: tk.Toplevel, dark: bool) -> None:
    """Barra de título escura no Windows 11 quando o tema é escuro."""
    if sys.platform != "win32" or not dark:
        return
    import ctypes

    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    value = ctypes.c_int(1)
    for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (20 no Windows 11, 19 em builds antigos)
        if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0:
            break

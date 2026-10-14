"""Janelinha flutuante que mostra "Gravando…/Transcrevendo…" sem roubar o foco do app onde você digita."""

from __future__ import annotations

import sys
import tkinter as tk

from .pipeline import ERROR, IDLE, LOADING, PROCESSING, RECORDING, WARNING

_COLORS = {
    RECORDING: "#d93025",
    PROCESSING: "#1a73e8",
    LOADING: "#5f6368",
    WARNING: "#e37400",
    ERROR: "#b3261e",
    IDLE: "#188038",
}
_HIDE_AFTER_MS = {IDLE: 1200, WARNING: 4000, ERROR: 6000}
_ALPHA = 0.93


def _make_click_through_no_focus(window: tk.Toplevel) -> None:
    if sys.platform != "win32":
        return
    import ctypes

    GWL_EXSTYLE = -20
    WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x00080000, 0x00000020
    WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x00000080, 0x08000000
    user32 = ctypes.windll.user32
    hwnd = int(window.wm_frame(), 16) or window.winfo_id()
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    )


class Overlay:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#202124")
        frame = tk.Frame(self.window, bg="#202124", padx=14, pady=8)
        frame.pack()
        self.dot = tk.Canvas(frame, width=14, height=14, bg="#202124", highlightthickness=0)
        self.dot_id = self.dot.create_oval(2, 2, 12, 12, fill=_COLORS[IDLE], outline="")
        self.dot.pack(side="left", padx=(0, 8))
        self.label = tk.Label(frame, text="", fg="white", bg="#202124", font=("Segoe UI", 11))
        self.label.pack(side="left")
        self.meter = tk.Canvas(frame, width=60, height=8, bg="#3c4043", highlightthickness=0)
        self.meter_id = self.meter.create_rectangle(0, 0, 0, 8, fill="#d93025", outline="")
        self.meter.pack(side="left", padx=(10, 0))
        self._hide_job = None
        # Fica sempre "aberta" e só muda a transparência: mostrar/esconder de verdade roubaria o foco.
        self.window.attributes("-alpha", 0.0)
        self.window.update_idletasks()
        _make_click_through_no_focus(self.window)

    def show(self, status: str, message: str) -> None:
        self.label.configure(text=message)
        self.dot.itemconfigure(self.dot_id, fill=_COLORS.get(status, "#5f6368"))
        if status != RECORDING:
            self.meter.coords(self.meter_id, 0, 0, 0, 8)
        self._place()
        self.window.attributes("-alpha", _ALPHA)
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None
        if status in _HIDE_AFTER_MS:
            self._hide_job = self.root.after(_HIDE_AFTER_MS[status], self.hide)

    def level(self, value: float) -> None:
        width = min(60, int(value * 600))
        self.meter.coords(self.meter_id, 0, 0, width, 8)

    def hide(self) -> None:
        self._hide_job = None
        self.window.attributes("-alpha", 0.0)

    def _place(self) -> None:
        self.window.update_idletasks()
        width, height = self.window.winfo_reqwidth(), self.window.winfo_reqheight()
        x = (self.window.winfo_screenwidth() - width) // 2
        y = self.window.winfo_screenheight() - height - 90
        self.window.geometry(f"+{x}+{y}")

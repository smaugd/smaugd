"""Pílula flutuante na parte de baixo da tela: ondas do microfone enquanto grava, andamento e resultado.

Não rouba o foco do aplicativo onde você está digitando e deixa os cliques passarem por ela.
"""

from __future__ import annotations

import math
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from collections import deque

from PIL import Image, ImageDraw, ImageTk

from . import theme
from .pipeline import DONE, ERROR, IDLE, LOADING, PROCESSING, RECORDING, WARNING

BAR_COUNT = 15
_HIDE_AFTER_MS = {DONE: 1400, IDLE: 1600, WARNING: 4500, ERROR: 7000}
_ICON_COLORS = {
    RECORDING: theme.RECORDING, PROCESSING: theme.ACCENT, LOADING: theme.MUTED,
    DONE: theme.SUCCESS, WARNING: theme.WARNING, ERROR: theme.ERROR, IDLE: theme.MUTED,
}
_TRANSPARENT_KEY = "#010203"  # cor que o Windows torna invisível (cantos arredondados de verdade)
_MAX_ALPHA = 0.97
_FRAME_MS = 33


def level_to_height(rms: float) -> float:
    """Converte o volume (RMS 0..1) em altura de barra 0..1, com curva para a fala normal encher bem."""
    if rms <= 0.002:
        return 0.0
    return min(1.0, (rms * 14) ** 0.6)


def format_elapsed(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _work_area(window: tk.Misc) -> tuple[int, int, int, int]:
    """Área útil da tela (sem a barra de tarefas)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):  # SPI_GETWORKAREA
            return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()


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


def _pill_image(width: int, height: int, background: str) -> Image.Image:
    """Desenha a pílula com bordas suaves (desenha 4x maior e reduz)."""
    factor = 4
    big = Image.new("RGB", (width * factor, height * factor), background)
    draw = ImageDraw.Draw(big)
    radius = height * factor // 2
    draw.rounded_rectangle((0, 0, width * factor - 1, height * factor - 1), radius, fill=theme.PILL_BORDER)
    inset = factor  # borda de 1 px
    draw.rounded_rectangle(
        (inset, inset, width * factor - 1 - inset, height * factor - 1 - inset), radius - inset, fill=theme.PILL_BG
    )
    return big.resize((width, height), Image.LANCZOS)


class Overlay:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.s = theme.ui_scale(root)
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        key = _TRANSPARENT_KEY if sys.platform == "win32" else theme.PILL_BG
        self._key = key
        self.window.configure(bg=key)
        if sys.platform == "win32":
            self.window.attributes("-transparentcolor", key)
        self.canvas = tk.Canvas(self.window, bg=key, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.font = tkfont.Font(root=root, font=theme.font(root, 10))
        self.font_small = tkfont.Font(root=root, font=theme.font(root, 9))

        self.status = IDLE
        self.message = ""
        self.levels: deque[float] = deque([0.0] * BAR_COUNT, maxlen=BAR_COUNT)
        self._level = 0.0
        self._started = 0.0
        self._alpha = 0.0
        self._target_alpha = 0.0
        self._hide_job = None
        self._animating = False
        self._pill_photo = None
        self._items: dict[str, object] = {}

        # Fica sempre "aberta" e só muda a transparência: mostrar/esconder de verdade roubaria o foco.
        self.window.attributes("-alpha", 0.0)
        self.window.update_idletasks()
        _make_click_through_no_focus(self.window)

    def px(self, value: float) -> int:
        return int(round(value * self.s))

    # --- API usada pelo app -------------------------------------------------
    def show(self, status: str, message: str) -> None:
        if status == RECORDING and self.status != RECORDING:
            self._started = time.monotonic()
            self.levels.extend([0.0] * BAR_COUNT)
            self._level = 0.0
        self.status, self.message = status, message
        self._layout()
        self._target_alpha = _MAX_ALPHA
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None
        if status in _HIDE_AFTER_MS:
            self._hide_job = self.root.after(_HIDE_AFTER_MS[status], self.hide)
        self._start_animation()

    def level(self, value: float) -> None:
        self._level = max(self._level, level_to_height(value))

    def hide(self) -> None:
        self._hide_job = None
        self._target_alpha = 0.0
        self._start_animation()

    # --- desenho ------------------------------------------------------------
    def _content_width(self) -> int:
        if self.status == RECORDING:
            bars = BAR_COUNT * self.px(3) + (BAR_COUNT - 1) * self.px(3)
            return bars + self.px(11) + self.font_small.measure("0:00")
        return min(self.font.measure(self._display_text()), self.px(460))

    def _display_text(self) -> str:
        text = " ".join(self.message.split())
        limit = 90
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _layout(self) -> None:
        height = self.px(40)
        pad = self.px(14)
        icon = self.px(18)
        width = pad + icon + self.px(10) + self._content_width() + pad + self.px(4)
        self.canvas.delete("all")
        self.canvas.configure(width=width, height=height)
        self._pill_photo = ImageTk.PhotoImage(_pill_image(width, height, self._key))
        self.canvas.create_image(0, 0, image=self._pill_photo, anchor="nw")

        cx, cy = pad + icon // 2, height // 2
        color = _ICON_COLORS.get(self.status, theme.MUTED)
        self._items = {}
        if self.status == RECORDING:
            r = self.px(5)
            self._items["halo"] = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=1)
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
        elif self.status in (PROCESSING, LOADING):
            self._items["dots"] = [
                self.canvas.create_oval(0, 0, 0, 0, fill=color, outline="") for _ in range(3)
            ]
            self._items["center"] = (cx, cy)
        else:
            self._draw_badge(cx, cy, color)

        x = pad + icon + self.px(10)
        if self.status == RECORDING:
            self._items["bars"] = []
            for i in range(BAR_COUNT):
                bx = x + i * self.px(6) + self.px(1)
                self._items["bars"].append(
                    self.canvas.create_line(bx, cy, bx, cy, fill=theme.PILL_TEXT, width=self.px(3), capstyle="round")
                )
            tx = x + BAR_COUNT * self.px(6) + self.px(8)
            self._items["timer"] = self.canvas.create_text(
                tx, cy, text="0:00", fill=theme.PILL_SUBTEXT, font=self.font_small, anchor="w"
            )
        else:
            fill = theme.PILL_TEXT if self.status != IDLE else theme.PILL_SUBTEXT
            self.canvas.create_text(x, cy, text=self._display_text(), fill=fill, font=self.font, anchor="w",
                                    width=self.px(460))
        self._place(width, height)
        self._animate_frame()

    def _draw_badge(self, cx: int, cy: int, color: str) -> None:
        r = self.px(8)
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
        w = max(2, self.px(2))
        if self.status == DONE:
            pts = (cx - self.px(3.5), cy, cx - self.px(1), cy + self.px(3), cx + self.px(4), cy - self.px(3))
            self.canvas.create_line(*pts, fill=theme.PILL_BG, width=w, capstyle="round", joinstyle="round")
        elif self.status in (WARNING, ERROR):
            self.canvas.create_line(cx, cy - self.px(4), cx, cy + self.px(1), fill=theme.PILL_BG, width=w,
                                    capstyle="round")
            d = self.px(1.3)
            self.canvas.create_oval(cx - d, cy + self.px(3) - d, cx + d, cy + self.px(3) + d, fill=theme.PILL_BG,
                                    outline="")
        else:
            self.canvas.create_oval(cx - self.px(2), cy - self.px(2), cx + self.px(2), cy + self.px(2),
                                    fill=theme.PILL_BG, outline="")

    def _place(self, width: int, height: int) -> None:
        left, _top, right, bottom = _work_area(self.window)
        x = left + (right - left - width) // 2
        y = bottom - height - self.px(28)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    # --- animação -----------------------------------------------------------
    def _start_animation(self) -> None:
        if not self._animating:
            self._animating = True
            self.root.after(_FRAME_MS, self._tick)

    def _tick(self) -> None:
        self._alpha += (self._target_alpha - self._alpha) * 0.35
        if abs(self._target_alpha - self._alpha) < 0.02:
            self._alpha = self._target_alpha
        self.window.attributes("-alpha", self._alpha)
        self._animate_frame()
        moving = self.status in (RECORDING, PROCESSING, LOADING) or self._alpha != self._target_alpha
        if moving and not (self._alpha == 0.0 and self._target_alpha == 0.0):
            self.root.after(_FRAME_MS, self._tick)
        else:
            self._animating = False

    def _animate_frame(self) -> None:
        now = time.monotonic()
        height = int(self.canvas.cget("height"))
        cy = height // 2
        if self.status == RECORDING and "bars" in self._items:
            self.levels.append(self._level)
            self._level *= 0.55  # decai até o próximo pedaço de áudio chegar
            max_half = self.px(11)
            for item, value in zip(self._items["bars"], self.levels, strict=False):
                half = max(self.px(1.5), value * max_half)
                x = self.canvas.coords(item)[0]
                self.canvas.coords(item, x, cy - half, x, cy + half)
            self.canvas.itemconfigure(self._items["timer"], text=format_elapsed(now - self._started))
            pulse = (math.sin(now * 5) + 1) / 2
            halo = self._items["halo"]
            cx = self.px(14) + self.px(18) // 2
            r = self.px(5) + pulse * self.px(4)
            self.canvas.coords(halo, cx - r, cy - r, cx + r, cy + r)
        elif "dots" in self._items:
            cx, cy = self._items["center"]
            for i, dot in enumerate(self._items["dots"]):
                phase = now * 6 - i * 0.9
                offset = -abs(math.sin(phase)) * self.px(4)
                dx = (i - 1) * self.px(7)
                r = self.px(2.8)
                self.canvas.coords(dot, cx + dx - r, cy + offset - r, cx + dx + r, cy + offset + r)

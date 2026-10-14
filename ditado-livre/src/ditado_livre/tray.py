"""Ícone na bandeja do Windows (perto do relógio) com o menu do app."""

from __future__ import annotations

from collections.abc import Callable

from PIL import Image, ImageDraw

from . import theme


def make_icon_image(color: str = theme.ACCENT, size: int = 64) -> Image.Image:
    """Microfone branco num quadrado arredondado colorido, desenhado grande e reduzido para ficar nítido."""
    big = 256
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, big - 8, big - 8), radius=64, fill=color)
    white = (255, 255, 255, 255)
    draw.rounded_rectangle((100, 44, 156, 152), radius=28, fill=white)  # cápsula
    draw.arc((72, 84, 184, 184), start=0, end=180, fill=white, width=16)  # suporte
    draw.line((128, 184, 128, 212), fill=white, width=16)
    draw.rounded_rectangle((92, 204, 164, 220), radius=8, fill=white)  # base
    return image.resize((size, size), Image.LANCZOS)


class Tray:
    def __init__(self, app) -> None:
        import pystray

        self.app = app
        item = pystray.MenuItem
        menu = pystray.Menu(
            item(lambda _i: app.status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Configurações…", lambda: app.open_settings(), default=True),
            item("Histórico…", lambda: app.open_history()),
            pystray.Menu.SEPARATOR,
            item("Transcrição", pystray.Menu(
                item("No meu PC (Whisper)", self._set("engine", "local"),
                     checked=lambda _i: app.config["engine"] == "local", radio=True),
                item("Na nuvem (Groq)", self._set("engine", "groq"),
                     checked=lambda _i: app.config["engine"] == "groq", radio=True),
            )),
            item("Limpeza com IA", self._toggle("ai_cleanup"), checked=lambda _i: app.config["ai_cleanup"]),
            item("Remover vícios (hum, ahn…)", self._toggle("remove_fillers"),
                 checked=lambda _i: app.config["remove_fillers"]),
            pystray.Menu.SEPARATOR,
            item("Sair", lambda: app.quit()),
        )
        self.icon = pystray.Icon("ditado-livre", make_icon_image(), "Ditado Livre", menu)

    def _set(self, key: str, value) -> Callable[[], None]:
        return lambda: self.app.update_setting(key, value)

    def _toggle(self, key: str) -> Callable[[], None]:
        return lambda: self.app.update_setting(key, not self.app.config[key])

    def run_detached(self) -> None:
        self.icon.run_detached()

    def refresh(self, color: str | None = None, tooltip: str | None = None) -> None:
        if color:
            self.icon.icon = make_icon_image(color)
        if tooltip:
            self.icon.title = f"Ditado Livre — {tooltip}"[:127]
        self.icon.update_menu()

    def notify(self, message: str) -> None:
        try:
            self.icon.notify(message, "Ditado Livre")
        except Exception:  # noqa: BLE001 - notificação é opcional
            pass

    def stop(self) -> None:
        self.icon.stop()

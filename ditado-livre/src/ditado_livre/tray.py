"""Ícone na bandeja do Windows (perto do relógio) com o menu do app."""

from __future__ import annotations

from collections.abc import Callable

from PIL import Image, ImageDraw


def make_icon_image(color: str = "#1a73e8") -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, 62, 62), fill=color)
    draw.rounded_rectangle((24, 12, 40, 38), radius=8, fill="white")  # microfone
    draw.arc((16, 22, 48, 46), start=0, end=180, fill="white", width=4)
    draw.line((32, 46, 32, 53), fill="white", width=4)
    draw.line((24, 53, 40, 53), fill="white", width=4)
    return image


class Tray:
    def __init__(self, app) -> None:
        import pystray

        self.app = app
        item = pystray.MenuItem
        menu = pystray.Menu(
            item(lambda _i: f"Ditado Livre — {app.status_text}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Transcrever no meu PC (Whisper)", self._set("engine", "local"),
                 checked=lambda _i: app.config["engine"] == "local", radio=True),
            item("Transcrever na nuvem (Groq)", self._set("engine", "groq"),
                 checked=lambda _i: app.config["engine"] == "groq", radio=True),
            item("Limpeza com IA", self._toggle("ai_cleanup"), checked=lambda _i: app.config["ai_cleanup"]),
            item("Remover vícios (hum, ahn…)", self._toggle("remove_fillers"),
                 checked=lambda _i: app.config["remove_fillers"]),
            pystray.Menu.SEPARATOR,
            item("Ver últimos ditados", lambda: app.open_history()),
            item("Abrir configurações", lambda: app.open_config()),
            item("Recarregar configurações", lambda: app.reload_config()),
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

    def refresh(self, color: str | None = None) -> None:
        if color:
            self.icon.icon = make_icon_image(color)
        self.icon.update_menu()

    def notify(self, message: str) -> None:
        try:
            self.icon.notify(message, "Ditado Livre")
        except Exception:  # noqa: BLE001 - notificação é opcional
            pass

    def stop(self) -> None:
        self.icon.stop()

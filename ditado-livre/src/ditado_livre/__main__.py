"""Ponto de entrada: `python -m ditado_livre` (ou iniciar.bat no Windows)."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk

from . import APP_NAME, __version__
from .audio import Recorder
from .config import ConfigError, app_dir, config_path, load_config, save_config
from .history import History
from .hotkey import HotkeyListener
from .output import Paster
from .pipeline import (
    ERROR, IDLE, LOADING, PROCESSING, RECORDING,
    DictationController, DictationPipeline, build_cleaner, build_transcriber,
)
from .transcribe.base import TranscriptionError

log = logging.getLogger("ditado_livre")

_TRAY_COLORS = {RECORDING: "#d93025", PROCESSING: "#1a73e8", LOADING: "#5f6368", ERROR: "#b3261e"}


def _open_file(path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606 - abre com o programa padrão (Bloco de Notas)
    else:
        subprocess.Popen(["xdg-open", str(path)])  # noqa: S603, S607


def _already_running() -> bool:
    """Evita dois Ditados Livres abertos (cada um colaria o texto)."""
    if sys.platform != "win32":
        return False
    import ctypes

    ctypes.windll.kernel32.CreateMutexW(None, False, "DitadoLivre-instancia-unica")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


class App:
    def __init__(self) -> None:
        self.config = load_config()
        self.status_text = "iniciando"
        self.events: queue.Queue = queue.Queue()
        self.root = tk.Tk()
        self.root.withdraw()
        from .overlay import Overlay
        from .tray import Tray

        self.overlay = Overlay(self.root)
        self.tray = Tray(self)
        self.history = History(app_dir() / "historico.sqlite3", self.config["history_size"])
        self.recorder = Recorder(on_level=lambda v: self.events.put(("level", v)))
        self.listener: HotkeyListener | None = None
        self.pipeline = DictationPipeline(self.config, None, None, self._paste, self.history)
        self.controller = DictationController(
            self.recorder, self.pipeline, self.set_status, reset_hotkey=lambda: self.listener and self.listener.reset()
        )
        self._apply_config()

    # --- configuração -------------------------------------------------------
    def _apply_config(self) -> None:
        if self.listener:
            self.listener.stop()
        self.listener = HotkeyListener(self.config["hotkey"], self.config["hotkey_mode"], self.controller.handle)
        self.listener.start()
        self.paster = Paster(restore_clipboard=self.config["restore_clipboard"])
        self.pipeline.config = self.config
        self.pipeline.cleaner = build_cleaner(self.config)
        self.pipeline.transcriber = None
        self.history.max_items = self.config["history_size"]
        try:
            self.pipeline.transcriber = build_transcriber(self.config)
        except TranscriptionError as exc:
            self.set_status(ERROR, str(exc))
            return
        threading.Thread(target=self._preload, daemon=True).start()

    def _preload(self) -> None:
        transcriber = self.pipeline.transcriber
        load = getattr(transcriber, "load", None)
        if load is None:
            self.set_status(IDLE, f"Pronto — segure {self.config['hotkey']} e fale")
            return
        self.set_status(LOADING, "Carregando o Whisper (na 1ª vez ele é baixado, pode demorar)…")
        try:
            load()
        except TranscriptionError as exc:
            self.set_status(ERROR, str(exc))
            return
        where = "placa de vídeo" if transcriber.active_device == "cuda" else "processador (mais lento)"
        self.set_status(IDLE, f"Pronto ({where}) — segure {self.config['hotkey']} e fale")

    def update_setting(self, key: str, value) -> None:
        self.config[key] = value
        save_config(self.config)
        self.events.put(("apply", None))

    def reload_config(self) -> None:
        try:
            self.config = load_config()
        except ConfigError as exc:
            self.set_status(ERROR, str(exc))
            return
        self.events.put(("apply", None))

    def open_config(self) -> None:
        _open_file(config_path())
        self.tray.notify("Depois de salvar o arquivo, use 'Recarregar configurações'.")

    def open_history(self) -> None:
        path = app_dir() / "ultimos-ditados.txt"
        lines = []
        for item in self.history.recent(30):
            ia = "com IA" if item["limpo_por_ia"] else "sem IA"
            lines.append(f"[{item['criado_em']} · {item['motor']} · {ia}]\n{item['final']}\n")
        path.write_text("\n".join(lines) or "Nenhum ditado ainda.", encoding="utf-8")
        _open_file(path)

    # --- status e colagem ---------------------------------------------------
    def set_status(self, status: str, message: str) -> None:
        log.info("[%s] %s", status, message)
        self.events.put(("status", (status, message)))

    def _paste(self, text: str) -> None:
        if self.listener:
            self.listener.wait_modifiers_released()
        self.paster.paste(text)

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    status, message = payload
                    self.status_text = message
                    self.overlay.show(status, message)
                    self.tray.refresh(_TRAY_COLORS.get(status, "#1a73e8"))
                elif kind == "level":
                    self.overlay.level(payload)
                elif kind == "apply":
                    self._apply_config()
                    self.tray.refresh()
                elif kind == "quit":
                    self._shutdown()
                    return
        except queue.Empty:
            pass
        self.root.after(30, self._poll_events)

    def quit(self) -> None:
        self.events.put(("quit", None))

    def _shutdown(self) -> None:
        if self.listener:
            self.listener.stop()
        self.recorder.stop()
        self.tray.stop()
        self.history.close()
        self.root.destroy()

    def run(self) -> None:
        self.tray.run_detached()
        self.root.after(30, self._poll_events)
        self.root.mainloop()


def main() -> None:
    app_dir().mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(app_dir() / "ditado-livre.log", encoding="utf-8"), logging.StreamHandler()],
    )
    log.info("%s %s", APP_NAME, __version__)
    if _already_running():
        log.info("Já existe um Ditado Livre aberto; saindo.")
        return
    App().run()


if __name__ == "__main__":
    main()

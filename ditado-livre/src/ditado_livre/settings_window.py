"""Janela de Configurações (no lugar de editar o config.json à mão)."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from . import APP_NAME, __version__, autostart, theme
from .hotkey import parse_hotkey

HOTKEY_PRESETS = ["Ctrl + Win", "Ctrl + Alt", "Ctrl + Shift + Space", "F9", "F8"]
MODELS = [
    ("large-v3-turbo", "Turbo — melhor precisão (recomendado)"),
    ("medium", "Médio — mais leve"),
    ("small", "Pequeno — rápido, menos preciso"),
    ("base", "Básico — para PCs fracos"),
]
DEVICES = [("auto", "Automático"), ("cuda", "Placa de vídeo NVIDIA"), ("cpu", "Processador")]
LANGUAGES = [("pt", "Português"), ("en", "English"), ("es", "Español")]
GROQ_KEYS_URL = "https://console.groq.com/keys"


def format_hotkey(value: str) -> str:
    names = {"ctrl": "Ctrl", "win": "Win", "alt": "Alt", "shift": "Shift", "space": "Space"}
    return " + ".join(names.get(part, part.upper() if len(part) <= 3 else part.title())
                      for part in value.split("+") if part)


def normalize_hotkey(display: str) -> str:
    keys = parse_hotkey(display)  # valida; lança ValueError se inválido
    order = ["ctrl", "win", "alt", "shift"]
    return "+".join(sorted(keys, key=lambda k: (order.index(k) if k in order else len(order), k)))


def form_to_config(base: dict[str, Any], form: dict[str, Any]) -> dict[str, Any]:
    """Converte os valores da tela em configuração. Lança ValueError com mensagem amigável."""
    config = dict(base)
    try:
        config["hotkey"] = normalize_hotkey(form["hotkey"])
    except ValueError as exc:
        raise ValueError(f"Atalho inválido: {exc}") from exc
    config["hotkey_mode"] = form["hotkey_mode"]
    config["engine"] = form["engine"]
    config["local_model"] = form["local_model"]
    config["device"] = form["device"]
    config["language"] = form["language"]
    config["groq_api_key"] = form["groq_api_key"].strip()
    config["remove_fillers"] = bool(form["remove_fillers"])
    config["extra_filler_words"] = [w.strip() for w in form["extra_filler_words"].split(",") if w.strip()]
    config["ai_cleanup"] = bool(form["ai_cleanup"])
    config["llm_provider"] = form["llm_provider"]
    config["ollama_model"] = form["ollama_model"].strip() or base["ollama_model"]
    config["ollama_url"] = form["ollama_url"].strip() or base["ollama_url"]
    config["groq_llm_model"] = form["groq_llm_model"].strip() or base["groq_llm_model"]
    config["restore_clipboard"] = bool(form["restore_clipboard"])
    config["append_space"] = bool(form["append_space"])
    if config["engine"] == "groq" and not config["groq_api_key"]:
        raise ValueError("Para transcrever na nuvem, cole a sua chave da Groq na aba Transcrição.")
    if config["ai_cleanup"] and config["llm_provider"] == "groq" and not config["groq_api_key"]:
        raise ValueError("Para revisar com a IA da Groq, cole a sua chave da Groq na aba Transcrição.")
    return config


class SettingsWindow:
    def __init__(
        self,
        root: tk.Tk,
        config: dict[str, Any],
        dark: bool,
        on_save: Callable[[dict[str, Any], bool], None],
        test_cleanup: Callable[[dict[str, Any]], str],
        open_data_folder: Callable[[], None],
    ) -> None:
        self.config = config
        self.on_save = on_save
        self.test_cleanup = test_cleanup
        self.open_data_folder = open_data_folder
        self.win = tk.Toplevel(root)
        self.win.title(f"{APP_NAME} — Configurações")
        self.win.resizable(False, False)
        self.font_title = theme.font(root, 15, "bold")
        self.font_hint = theme.font(root, 9)

        self.v = {
            "hotkey": tk.StringVar(value=format_hotkey(config["hotkey"])),
            "hotkey_mode": tk.StringVar(value=config["hotkey_mode"]),
            "engine": tk.StringVar(value=config["engine"]),
            "local_model": tk.StringVar(value=_label(MODELS, config["local_model"])),
            "device": tk.StringVar(value=_label(DEVICES, config["device"])),
            "language": tk.StringVar(value=_label(LANGUAGES, config["language"])),
            "groq_api_key": tk.StringVar(value=config["groq_api_key"]),
            "remove_fillers": tk.BooleanVar(value=config["remove_fillers"]),
            "extra_filler_words": tk.StringVar(value=", ".join(config["extra_filler_words"])),
            "ai_cleanup": tk.BooleanVar(value=config["ai_cleanup"]),
            "llm_provider": tk.StringVar(value=config["llm_provider"]),
            "ollama_model": tk.StringVar(value=config["ollama_model"]),
            "ollama_url": tk.StringVar(value=config["ollama_url"]),
            "groq_llm_model": tk.StringVar(value=config["groq_llm_model"]),
            "restore_clipboard": tk.BooleanVar(value=config["restore_clipboard"]),
            "append_space": tk.BooleanVar(value=config["append_space"]),
        }
        self.autostart = tk.BooleanVar(value=autostart.is_enabled())
        self.show_key = tk.BooleanVar(value=False)
        self.error = tk.StringVar()
        self.test_result = tk.StringVar()

        outer = ttk.Frame(self.win, padding=(24, 20, 24, 20))
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="Configurações", font=self.font_title).pack(anchor="w")
        ttk.Label(header, text="As mudanças valem assim que você clicar em Salvar.",
                  font=self.font_hint, foreground=theme.MUTED).pack(anchor="w", pady=(2, 0))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        notebook.add(self._tab_general(notebook), text="  Geral  ")
        notebook.add(self._tab_transcription(notebook), text="  Transcrição  ")
        notebook.add(self._tab_cleanup(notebook), text="  Limpeza  ")
        notebook.add(self._tab_about(notebook), text="  Sobre  ")

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(16, 0))
        ttk.Label(footer, textvariable=self.error, foreground=theme.ERROR, font=self.font_hint,
                  wraplength=330, justify="left").pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Salvar", style="Accent.TButton", command=self._save, width=12).pack(side="right")
        ttk.Button(footer, text="Cancelar", command=self.win.destroy, width=12).pack(side="right", padx=(0, 8))

        self.v["engine"].trace_add("write", lambda *_: self._sync_states())
        self.v["ai_cleanup"].trace_add("write", lambda *_: self._sync_states())
        self.v["llm_provider"].trace_add("write", lambda *_: self._sync_states())
        self._sync_states()

        self.win.bind("<Escape>", lambda _e: self.win.destroy())
        self.win.update_idletasks()
        self._center()
        theme.style_titlebar(self.win, dark)
        self.win.lift()
        self.win.focus_force()

    # --- abas ---------------------------------------------------------------
    def _page(self, parent) -> ttk.Frame:
        page = ttk.Frame(parent, padding=(18, 16, 18, 16))
        page.columnconfigure(1, weight=1)
        return page

    def _section(self, page, row: int, title: str) -> int:
        ttk.Label(page, text=title, font=theme.font(page, 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0 if row == 0 else 14, 6))
        return row + 1

    def _hint(self, page, row: int, text: str, column: int = 0) -> int:
        ttk.Label(page, text=text, font=self.font_hint, foreground=theme.MUTED, wraplength=420,
                  justify="left").grid(row=row, column=column, columnspan=3 - column, sticky="w", pady=(0, 4))
        return row + 1

    def _tab_general(self, parent) -> ttk.Frame:
        page = self._page(parent)
        row = self._section(page, 0, "Atalho para ditar")
        ttk.Label(page, text="Teclas").grid(row=row, column=0, sticky="w", padx=(0, 12))
        ttk.Combobox(page, textvariable=self.v["hotkey"], values=HOTKEY_PRESETS, width=24).grid(
            row=row, column=1, sticky="w")
        row += 1
        row = self._hint(page, row, "Escolha uma opção ou digite outra combinação (ex.: Ctrl + Shift + D). "
                                    "Esc cancela o ditado em andamento.")
        ttk.Radiobutton(page, text="Segurar enquanto fala", value="hold",
                        variable=self.v["hotkey_mode"]).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1
        ttk.Radiobutton(page, text="Apertar para começar e de novo para terminar", value="toggle",
                        variable=self.v["hotkey_mode"]).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1

        row = self._section(page, row, "Ao colar o texto")
        ttk.Checkbutton(page, text="Devolver o que estava copiado antes", variable=self.v["restore_clipboard"]
                        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1
        ttk.Checkbutton(page, text="Adicionar um espaço no final", variable=self.v["append_space"]
                        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1

        row = self._section(page, row, "Inicialização")
        check = ttk.Checkbutton(page, text="Abrir junto com o Windows", variable=self.autostart)
        check.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        if not autostart.supported():
            check.state(["disabled"])
        return page

    def _tab_transcription(self, parent) -> ttk.Frame:
        page = self._page(parent)
        row = self._section(page, 0, "Onde transcrever")
        ttk.Radiobutton(page, text="No meu computador — privado e grátis", value="local",
                        variable=self.v["engine"]).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1
        ttk.Radiobutton(page, text="Na nuvem (Groq) — rápido em qualquer PC, precisa de internet", value="groq",
                        variable=self.v["engine"]).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1

        row = self._section(page, row, "Whisper no computador")
        self.local_widgets = []
        for label, key, options in (("Modelo", "local_model", MODELS), ("Usar", "device", DEVICES)):
            ttk.Label(page, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
            combo = ttk.Combobox(page, textvariable=self.v[key], values=[o[1] for o in options],
                                 state="readonly", width=36)
            combo.grid(row=row, column=1, sticky="w", pady=3)
            self.local_widgets.append(combo)
            row += 1
        ttk.Label(page, text="Idioma").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        ttk.Combobox(page, textvariable=self.v["language"], values=[o[1] for o in LANGUAGES], state="readonly",
                     width=36).grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        row = self._section(page, row, "Chave da Groq")
        key_row = ttk.Frame(page)
        key_row.grid(row=row, column=0, columnspan=3, sticky="we")
        key_row.columnconfigure(0, weight=1)
        self.key_entry = ttk.Entry(key_row, textvariable=self.v["groq_api_key"], show="•")
        self.key_entry.grid(row=0, column=0, sticky="we")
        ttk.Checkbutton(key_row, text="Mostrar", variable=self.show_key,
                        command=lambda: self.key_entry.configure(show="" if self.show_key.get() else "•")
                        ).grid(row=0, column=1, padx=(8, 0))
        row += 1
        link = ttk.Label(page, text="Criar uma chave grátis ↗", foreground=theme.ACCENT, cursor="hand2",
                         font=self.font_hint)
        link.grid(row=row, column=0, columnspan=3, sticky="w", pady=(6, 0))
        link.bind("<Button-1>", lambda _e: webbrowser.open(GROQ_KEYS_URL))
        row += 1
        self._hint(page, row, "Só é usada se você escolher a nuvem para transcrever ou para a IA. "
                              "Com a Groq, o áudio e o texto saem do seu computador.")
        return page

    def _tab_cleanup(self, parent) -> ttk.Frame:
        page = self._page(parent)
        row = self._section(page, 0, "Hesitações")
        ttk.Checkbutton(page, text="Remover “hum”, “ahn”, “éé”…", variable=self.v["remove_fillers"]
                        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1
        ttk.Label(page, text="Remover também").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        ttk.Entry(page, textvariable=self.v["extra_filler_words"]).grid(row=row, column=1, sticky="we", pady=3)
        row += 1
        row = self._hint(page, row, "Separe por vírgulas. Ex.: tipo assim, sabe")

        row = self._section(page, row, "Revisão com IA")
        ttk.Checkbutton(page, text="Revisar o texto com IA", variable=self.v["ai_cleanup"]
                        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1
        row = self._hint(page, row, "Corrige pontuação, escreve números com dígitos, aplica correções faladas "
                                    "(“às duas, não, às três”) e monta listas. Se a IA falhar, o texto é colado "
                                    "mesmo assim.")
        self.ai_widgets = []
        for text, value in (("Ollama — no meu computador", "ollama"), ("Groq — na nuvem", "groq")):
            radio = ttk.Radiobutton(page, text=text, value=value, variable=self.v["llm_provider"])
            radio.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
            self.ai_widgets.append(radio)
            row += 1
        self.provider_rows = {}
        for provider, label, key in (("ollama", "Modelo do Ollama", "ollama_model"),
                                     ("ollama", "Endereço", "ollama_url"),
                                     ("groq", "Modelo da Groq", "groq_llm_model")):
            lbl = ttk.Label(page, text=label)
            lbl.grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
            entry = ttk.Entry(page, textvariable=self.v[key])
            entry.grid(row=row, column=1, sticky="we", pady=3)
            self.provider_rows.setdefault(provider, []).append(entry)
            row += 1
        test_row = ttk.Frame(page)
        test_row.grid(row=row, column=0, columnspan=3, sticky="we", pady=(8, 0))
        self.test_button = ttk.Button(test_row, text="Testar IA", command=self._run_test)
        self.test_button.pack(side="left")
        ttk.Label(test_row, textvariable=self.test_result, font=self.font_hint, wraplength=330,
                  justify="left").pack(side="left", padx=(10, 0))
        self.ai_widgets.append(self.test_button)
        return page

    def _tab_about(self, parent) -> ttk.Frame:
        page = self._page(parent)
        ttk.Label(page, text=APP_NAME, font=theme.font(page, 13, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(page, text=f"Versão {__version__}", foreground=theme.MUTED).grid(row=1, column=0, sticky="w")
        self._hint(page, 2, "Ditado por voz gratuito e de código aberto. Segure o atalho, fale e solte: "
                            "o texto aparece onde o cursor estiver.")
        ttk.Button(page, text="Abrir pasta de dados", command=self.open_data_folder).grid(
            row=3, column=0, sticky="w", pady=(12, 0))
        self._hint(page, 4, "Lá ficam o config.json (opções avançadas), o histórico e o log de erros.")
        return page

    # --- comportamento ------------------------------------------------------
    def _sync_states(self) -> None:
        local = self.v["engine"].get() == "local"
        for widget in self.local_widgets:
            widget.state(["!disabled", "readonly"] if local else ["disabled"])
        ai_on = self.v["ai_cleanup"].get()
        for widget in self.ai_widgets:
            widget.state(["!disabled"] if ai_on else ["disabled"])
        provider = self.v["llm_provider"].get()
        for name, widgets in self.provider_rows.items():
            for widget in widgets:
                widget.state(["!disabled"] if ai_on and name == provider else ["disabled"])

    def _form(self) -> dict[str, Any]:
        form = {key: var.get() for key, var in self.v.items()}
        form["local_model"] = _value(MODELS, form["local_model"])
        form["device"] = _value(DEVICES, form["device"])
        form["language"] = _value(LANGUAGES, form["language"])
        return form

    def _save(self) -> None:
        try:
            config = form_to_config(self.config, self._form())
        except ValueError as exc:
            self.error.set(str(exc))
            return
        self.on_save(config, self.autostart.get())
        self.win.destroy()

    def _run_test(self) -> None:
        try:
            config = form_to_config(self.config, {**self._form(), "ai_cleanup": True})
        except ValueError as exc:
            self.test_result.set(str(exc))
            return
        self.test_button.state(["disabled"])
        self.test_result.set("Testando…")

        def work() -> None:
            try:
                message = "✓ Funcionando: " + self.test_cleanup(config)
            except Exception as exc:  # noqa: BLE001 - mostra qualquer falha na tela
                message = f"✗ {exc}"
            self.win.after(0, lambda: self._finish_test(message))

        threading.Thread(target=work, daemon=True).start()

    def _finish_test(self, message: str) -> None:
        if not self.win.winfo_exists():
            return
        self.test_result.set(message)
        self.test_button.state(["!disabled"])

    def _center(self) -> None:
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x = (self.win.winfo_screenwidth() - w) // 2
        y = (self.win.winfo_screenheight() - h) // 3
        self.win.geometry(f"+{x}+{y}")


def _label(options: list[tuple[str, str]], value: str) -> str:
    return next((label for v, label in options if v == value), value)


def _value(options: list[tuple[str, str]], label: str) -> str:
    return next((v for v, lbl in options if lbl == label), label)

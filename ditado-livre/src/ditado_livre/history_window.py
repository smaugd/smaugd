"""Janela de Histórico: os últimos ditados, com busca e botão de copiar."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import APP_NAME, theme


def short_time(iso: str) -> str:
    """'2026-10-14T09:05:33' → '14/10 09:05'."""
    try:
        date, clock = iso.split("T")
        _year, month, day = date.split("-")
        return f"{day}/{month} {clock[:5]}"
    except ValueError:
        return iso


def matches(item: dict, query: str) -> bool:
    query = query.strip().lower()
    return not query or query in item["final"].lower() or query in item["bruto"].lower()


class HistoryWindow:
    def __init__(self, root: tk.Tk, items: list[dict], dark: bool) -> None:
        self.items = items
        self.win = tk.Toplevel(root)
        self.win.title(f"{APP_NAME} — Histórico")
        self.win.geometry("680x520")
        self.win.minsize(520, 400)
        self.query = tk.StringVar()
        self.feedback = tk.StringVar()
        self.meta = tk.StringVar()

        outer = ttk.Frame(self.win, padding=(20, 18, 20, 18))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=3)
        outer.rowconfigure(4, weight=2)

        top = ttk.Frame(outer)
        top.grid(row=0, column=0, sticky="we")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text="Histórico", font=theme.font(root, 15, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Buscar", foreground=theme.MUTED).grid(row=0, column=1, sticky="e", padx=(0, 8))
        search = ttk.Entry(top, textvariable=self.query, width=26)
        search.grid(row=0, column=2, sticky="e")
        ttk.Label(outer, text="Clique duas vezes num ditado para copiar.", foreground=theme.MUTED,
                  font=theme.font(root, 9)).grid(row=1, column=0, sticky="w", pady=(2, 10))

        table = ttk.Frame(outer)
        table.grid(row=2, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=("hora", "texto"), show="headings", selectmode="browse")
        self.tree.heading("hora", text="Quando", anchor="w")
        self.tree.heading("texto", text="Texto", anchor="w")
        self.tree.column("hora", width=110, stretch=False)
        self.tree.column("texto", width=480)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        label_row = ttk.Frame(outer)
        label_row.grid(row=3, column=0, sticky="we", pady=(14, 6))
        ttk.Label(label_row, text="Texto completo", font=theme.font(root, 10, "bold")).pack(side="left")
        ttk.Label(label_row, textvariable=self.meta, foreground=theme.MUTED, font=theme.font(root, 9)).pack(
            side="left", padx=(10, 0))
        self.preview = tk.Text(outer, height=5, wrap="word", relief="flat", borderwidth=0, padx=10, pady=8,
                               font=theme.font(root, 10),
                               background="#202227" if dark else "#f4f5f7",
                               foreground="#f2f3f5" if dark else "#1f2328",
                               highlightthickness=0, insertwidth=0)
        self.preview.grid(row=4, column=0, sticky="nsew")
        self.preview.configure(state="disabled")

        bottom = ttk.Frame(outer)
        bottom.grid(row=5, column=0, sticky="we", pady=(12, 0))
        ttk.Label(bottom, textvariable=self.feedback, foreground=theme.SUCCESS).pack(side="left")
        ttk.Button(bottom, text="Copiar", style="Accent.TButton", width=12,
                   command=lambda: self._copy("final")).pack(side="right")
        ttk.Button(bottom, text="Copiar original", width=14,
                   command=lambda: self._copy("bruto")).pack(side="right", padx=(0, 8))

        self.query.trace_add("write", lambda *_: self._fill())
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._show_selected())
        self.tree.bind("<Double-1>", lambda _e: self._copy("final"))
        self.win.bind("<Escape>", lambda _e: self.win.destroy())
        self._fill()
        self.win.update_idletasks()
        x = (self.win.winfo_screenwidth() - self.win.winfo_width()) // 2
        y = (self.win.winfo_screenheight() - self.win.winfo_height()) // 3
        self.win.geometry(f"+{max(0, x)}+{max(0, y)}")
        theme.style_titlebar(self.win, dark)
        self.win.lift()
        self.win.focus_force()
        search.focus_set()

    def _fill(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.visible = [item for item in self.items if matches(item, self.query.get())]
        for index, item in enumerate(self.visible):
            text = " ".join(item["final"].split())
            self.tree.insert("", "end", iid=str(index), values=(short_time(item["criado_em"]), text))
        if self.visible:
            self.tree.selection_set("0")
        else:
            self.meta.set("")
            self._set_preview("Nenhum ditado ainda." if not self.items else "Nada encontrado.")

    def _selected(self) -> dict | None:
        selection = self.tree.selection()
        return self.visible[int(selection[0])] if selection else None

    def _show_selected(self) -> None:
        item = self._selected()
        if item:
            ai = "revisado com IA" if item["limpo_por_ia"] else "sem revisão da IA"
            motor = "no computador" if item["motor"] == "local" else item["motor"]
            self._set_preview(item["final"])
            self.feedback.set("")
            self.meta.set(f"transcrito {motor} · {ai}")

    def _set_preview(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _copy(self, field: str) -> None:
        item = self._selected()
        if not item:
            return
        self.win.clipboard_clear()
        self.win.clipboard_append(item[field])
        self.feedback.set("✓ Copiado" if field == "final" else "✓ Original copiado")

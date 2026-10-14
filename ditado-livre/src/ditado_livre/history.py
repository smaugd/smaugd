"""Histórico das últimas falas, para recuperar um texto que não colou."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path


class History:
    def __init__(self, path: Path, max_items: int = 200) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.max_items = max_items
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS ditados ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, criado_em TEXT NOT NULL, "
            "bruto TEXT NOT NULL, final TEXT NOT NULL, motor TEXT NOT NULL, limpo_por_ia INTEGER NOT NULL)"
        )
        self._db.commit()

    def add(self, raw: str, final: str, engine: str, cleaned_by_ai: bool) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO ditados (criado_em, bruto, final, motor, limpo_por_ia) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), raw, final, engine, int(cleaned_by_ai)),
            )
            self._db.execute(
                "DELETE FROM ditados WHERE id NOT IN (SELECT id FROM ditados ORDER BY id DESC LIMIT ?)",
                (self.max_items,),
            )
            self._db.commit()

    def recent(self, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT criado_em, bruto, final, motor, limpo_por_ia FROM ditados ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"criado_em": r[0], "bruto": r[1], "final": r[2], "motor": r[3], "limpo_por_ia": bool(r[4])}
            for r in rows
        ]

    def close(self) -> None:
        self._db.close()

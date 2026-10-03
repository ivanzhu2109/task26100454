"""SQLite 流水存储：追加与按序读取。"""
from __future__ import annotations

import sqlite3

from .models import Event, EventType

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq  INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    qty  INTEGER NOT NULL CHECK (qty > 0),
    dst  TEXT NOT NULL,
    src  TEXT NOT NULL DEFAULT ''
)
"""


class EventStore:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append(self, type_: EventType, qty: int, dst: str, src: str = "") -> int:
        """追加一条流水，返回分配的严格递增序号。"""
        if qty <= 0:
            raise ValueError("qty 必须为正整数")
        cur = self._conn.execute(
            "INSERT INTO events (type, qty, dst, src) VALUES (?, ?, ?, ?)",
            (type_.value, qty, dst, src),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def load_upto(self, cutoff: int) -> list[Event]:
        """按序号升序返回 seq <= cutoff 的全部流水。"""
        rows = self._conn.execute(
            "SELECT seq, type, qty, dst, src FROM events WHERE seq <= ? ORDER BY seq",
            (cutoff,),
        ).fetchall()
        return [
            Event(seq=r[0], type=EventType(r[1]), qty=r[2], dst=r[3], src=r[4])
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()

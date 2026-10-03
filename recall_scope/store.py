"""SQLite 流水存储：追加与按截止序号读取。"""
from __future__ import annotations

import sqlite3

from .types import Event, EventType

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
    seq       INTEGER PRIMARY KEY,
    type      TEXT NOT NULL,
    qty       INTEGER NOT NULL CHECK (qty > 0),
    container TEXT NOT NULL DEFAULT '',
    src       TEXT NOT NULL DEFAULT '',
    dst       TEXT NOT NULL DEFAULT ''
)
"""


class LedgerStore:
    """调用方指定 SQLite 文件路径；历史流水只追加、不修改。"""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def _append(self, type_: EventType, qty: int,
                container: str = "", src: str = "", dst: str = "") -> Event:
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("qty 必须为正整数")
        cur = self._conn.execute(
            "INSERT INTO ledger (seq, type, qty, container, src, dst) "
            "VALUES (COALESCE((SELECT MAX(seq) FROM ledger), 0) + 1, ?, ?, ?, ?, ?)",
            (type_.value, qty, container, src, dst),
        )
        self._conn.commit()
        return Event(seq=cur.lastrowid, type=type_, qty=qty,
                     container=container, src=src, dst=dst)

    def append_inbound(self, container: str, qty: int) -> Event:
        return self._append(EventType.INBOUND, qty, container=container)

    def append_transfer(self, src: str, dst: str, qty: int) -> Event:
        if src == dst:
            raise ValueError("源容器与目标容器不能相同")
        return self._append(EventType.TRANSFER, qty, src=src, dst=dst)

    def append_issue(self, container: str, qty: int) -> Event:
        return self._append(EventType.ISSUE, qty, container=container)

    def load_upto(self, cutoff: int) -> list[Event]:
        """按序号升序返回 seq <= cutoff 的全部流水。"""
        rows = self._conn.execute(
            "SELECT seq, type, qty, container, src, dst FROM ledger "
            "WHERE seq <= ? ORDER BY seq",
            (cutoff,),
        ).fetchall()
        return [
            Event(seq=r[0], type=EventType(r[1]), qty=r[2],
                  container=r[3], src=r[4], dst=r[5])
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "LedgerStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

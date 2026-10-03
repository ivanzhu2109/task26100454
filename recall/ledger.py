"""对外 API：追加流水 + 生成召回清单。由上层质量系统直接调用。"""
from __future__ import annotations

from typing import Iterable

from .engine import compute_recall
from .models import EventType, RecallResult
from .store import EventStore


class RecallLedger:
    """单一物料的流水账本与召回范围计算。

    流水持久化在调用方指定的 SQLite 文件中；关闭后重新打开，
    同样的查询输入得到一致的结果。
    """

    def __init__(self, db_path: str) -> None:
        self._store = EventStore(db_path)

    def append_inbound(self, container: str, qty: int) -> int:
        """外部入库：增加目标容器库存，返回流水序号。"""
        return self._store.append(EventType.INBOUND, qty, dst=container)

    def append_transfer(self, src: str, dst: str, qty: int) -> int:
        """容器间转移：源扣减并等量加入目标，返回流水序号。"""
        if src == dst:
            raise ValueError("源容器与目标容器不能相同")
        return self._store.append(EventType.TRANSFER, qty, dst=dst, src=src)

    def append_consume(self, container: str, qty: int) -> int:
        """最终领用：扣减库存并永久离开流转链，返回流水序号。"""
        return self._store.append(EventType.CONSUME, qty, dst=container)

    def recall(self, suspicious_seqs: Iterable[int], cutoff_seq: int) -> RecallResult:
        """生成召回清单：只依据 cutoff_seq 及之前的流水。

        suspicious_seqs 为可疑入库流水序号集合；多条传播路径按并集计算，
        同一领用与同一容器不重复计量。
        """
        events = self._store.load_upto(cutoff_seq)
        return compute_recall(events, set(suspicious_seqs))

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> "RecallLedger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

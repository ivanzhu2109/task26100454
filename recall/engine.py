"""召回传播引擎：对截止点之前的流水做纯内存重放。

传播规则（保守并集）：
- 可疑入库进入容器时，该容器当时全部库存成为疑似。
- 疑似容器未清空前，后续加入的正常物料也全部视为疑似。
- 从疑似容器转出的整笔均为疑似，并使目标容器全部库存成为疑似。
- 容器数量恰好归零时，疑似状态消失，后续正常入库不继承旧状态。
- 从疑似容器领用的整笔必须召回；污染不倒推此前已离开的物料。
"""
from __future__ import annotations

from .models import Event, EventType, RecallResult


class _Container:
    __slots__ = ("qty", "suspect")

    def __init__(self) -> None:
        self.qty = 0
        self.suspect = False


def compute_recall(events: list[Event], suspicious: set[int]) -> RecallResult:
    containers: dict[str, _Container] = {}

    def get(name: str) -> _Container:
        c = containers.get(name)
        if c is None:
            c = containers[name] = _Container()
        return c

    result = RecallResult()
    for ev in events:
        if ev.type is EventType.INBOUND:
            c = get(ev.dst)
            c.qty += ev.qty
            if ev.seq in suspicious:
                c.suspect = True
        elif ev.type is EventType.TRANSFER:
            src, dst = get(ev.src), get(ev.dst)
            src.qty -= ev.qty
            dst.qty += ev.qty
            if src.suspect:
                dst.suspect = True
            if src.qty == 0:
                src.suspect = False
        elif ev.type is EventType.CONSUME:
            c = get(ev.dst)
            c.qty -= ev.qty
            if c.suspect:
                result.recalled_consumes.append((ev.seq, ev.qty))
            if c.qty == 0:
                c.suspect = False
        else:  # pragma: no cover
            raise ValueError(f"未知流水类型: {ev.type}")

    result.suspect_stock = {
        name: c.qty for name, c in sorted(containers.items()) if c.suspect and c.qty > 0
    }
    return result

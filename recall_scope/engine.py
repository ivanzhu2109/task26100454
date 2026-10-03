"""召回范围计算：对截止点之前的流水做确定性重放。"""
from __future__ import annotations

from .types import Event, EventType, RecallReport, RecalledIssue


def compute_recall(events: list[Event], suspicious_inbounds: set[int]) -> RecallReport:
    """重放 events（已按 seq 升序、且不晚于截止点），输出召回清单。

    容器状态：现存数量 + 是否疑似。可疑入库到达时容器全部库存转疑似；
    疑似容器未清空时后续入库同样疑似；从疑似容器转出的整笔使目标全疑；
    数量归零时疑似状态消失；从疑似容器领用的整笔计入召回。
    """
    stock: dict[str, int] = {}
    suspect: set[str] = set()
    report = RecallReport()

    def add(container: str, qty: int) -> None:
        stock[container] = stock.get(container, 0) + qty

    def take(container: str, qty: int) -> None:
        left = stock.get(container, 0) - qty
        if left < 0:
            raise ValueError(f"容器 {container} 库存不足")
        stock[container] = left
        if left == 0:
            suspect.discard(container)

    for ev in events:
        if ev.type is EventType.INBOUND:
            add(ev.container, ev.qty)
            if ev.seq in suspicious_inbounds:
                suspect.add(ev.container)
        elif ev.type is EventType.TRANSFER:
            was_suspect = ev.src in suspect
            take(ev.src, ev.qty)
            add(ev.dst, ev.qty)
            if was_suspect:
                suspect.add(ev.dst)
        elif ev.type is EventType.ISSUE:
            if ev.container in suspect:
                report.recalled_issues.append(
                    RecalledIssue(seq=ev.seq, container=ev.container, qty=ev.qty))
            take(ev.container, ev.qty)
        else:  # pragma: no cover
            raise ValueError(f"未知流水类型: {ev.type}")

    report.suspect_stock = {c: stock[c] for c in suspect if stock.get(c, 0) > 0}
    return report

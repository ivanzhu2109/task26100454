"""类型定义：流水事件与召回清单。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    INBOUND = "inbound"    # 外部入库：增加目标容器库存
    TRANSFER = "transfer"  # 容器间转移：源扣减、目标等量加入
    ISSUE = "issue"        # 最终领用：扣减并永久离开流转链


@dataclass(frozen=True)
class Event:
    """一条流水。seq 由库在追加时分配，严格递增。"""
    seq: int
    type: EventType
    qty: int
    container: str = ""        # INBOUND / ISSUE 的目标容器
    src: str = ""              # TRANSFER 的源容器
    dst: str = ""              # TRANSFER 的目标容器


@dataclass(frozen=True)
class RecalledIssue:
    """需要召回的领用流水。"""
    seq: int
    container: str
    qty: int


@dataclass
class RecallReport:
    """召回清单：需召回的领用 + 仍疑似容器的全部现存数量。"""
    recalled_issues: list[RecalledIssue] = field(default_factory=list)
    suspect_stock: dict[str, int] = field(default_factory=dict)

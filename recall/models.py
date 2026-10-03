"""类型定义：流水事件与召回结果。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    INBOUND = "inbound"    # 外部入库：增加目标容器库存
    TRANSFER = "transfer"  # 容器间转移：源扣减、目标等量加入
    CONSUME = "consume"    # 最终领用：扣减并永久离开流转链


@dataclass(frozen=True)
class Event:
    seq: int
    type: EventType
    qty: int
    dst: str        # INBOUND/TRANSFER 的目标容器；CONSUME 时为领用容器
    src: str = ""   # 仅 TRANSFER 使用


@dataclass
class RecallResult:
    # 截止点时需要召回的领用流水：(seq, qty)，按 seq 升序
    recalled_consumes: list[tuple[int, int]] = field(default_factory=list)
    # 仍处于疑似状态的容器及其全部现存数量
    suspect_stock: dict[str, int] = field(default_factory=dict)

# recall — 召回范围计算库

单一物料的流水账本与召回清单生成，由上层质量系统直接调用，
流水持久化在调用方指定的 SQLite 文件中。

## 用法

```python
from recall import RecallLedger

with RecallLedger("/path/to/ledger.db") as lg:
    s1 = lg.append_inbound("A", 10)      # 外部入库
    lg.append_transfer("A", "B", 4)      # 容器间转移
    lg.append_consume("B", 2)            # 最终领用

    result = lg.recall(suspicious_seqs=[s1], cutoff_seq=10**9)
    result.recalled_consumes  # [(领用流水序号, 数量), ...]
    result.suspect_stock      # {容器: 疑似现存数量}
```

## 规则要点

- 可疑入库进入容器时，该容器当时全部库存成为疑似；未清空前后续加入的
  正常物料也视为疑似；数量恰好归零时疑似状态消失，不继承给后续补货。
- 从疑似容器转出的整笔均为疑似并使目标全部库存疑似；从疑似容器领用的
  整笔必须召回；污染不倒推此前已离开的物料。
- 查询只依据截止序号及之前的流水；多笔可疑入库与多条传播路径按并集
  计算，同一领用与同一容器不重复计量。
- 关闭后重新打开同一数据文件，查询结果一致。

## 测试

```sh
python3 -m unittest discover -s tests -v
```

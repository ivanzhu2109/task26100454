# recall-scope

单物料召回范围计算库，由上层质量系统直接调用；流水持久化在调用方指定的 SQLite 文件中。

## 能力

- `LedgerStore(db_path)`：打开/创建流水文件，提供 `append_inbound` / `append_transfer` / `append_issue` 追加流水（序号自动严格递增，历史不可改）。
- `compute_recall(events, suspicious_inbounds)`：传入 `store.load_upto(cutoff)` 与可疑入库序号集合，返回 `RecallReport`：
  - `recalled_issues`：截止点内需召回的领用流水及数量；
  - `suspect_stock`：仍处于疑似状态的容器及其全部现存数量。

## 规则摘要

可疑入库到达时容器全部库存转疑似；疑似容器未清空时后续入库同样疑似；从疑似容器转出的整笔使目标容器全疑；源容器数量归零时疑似状态消失，之后补货不继承；从疑似容器领用的整笔计入召回。多笔可疑入库按并集计算，同一领用/容器不重复计量，合计允许大于原可疑数量（保守口径）。

## 测试

```bash
python3 -m pytest tests/ -q
```

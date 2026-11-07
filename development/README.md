# 开发入口

依次阅读 [长期规范](plan.md)、[当前计划](current.md)、[当前交接](handoff.md)。三份台账位于 `ledgers/`；共同功能和批次位于 `tracking/`；生成汇总位于 `generated/`。

```powershell
.\.venv\Scripts\python.exe -B scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json
.\.venv\Scripts\python.exe -B -m pytest tests/unit -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests/native --run-zemax -q -p no:cacheprovider
```

原生测试串行执行。证据摘要在 `evidence/`；原始数据在 `.local/evidence`，大复现输入在 `.local/fixtures`；历史ZIP在 `.local/archives`。迁移清单为 `tracking/workspace-migration.json`。

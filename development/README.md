# 开发入口

项目已于 2026-11-09 停止新增功能开发并进入 1.0.0 维护阶段。D00x 分组、逐项台账与验收证据保留为历史状态及未来重新立项依据；发行结果见[1.0.0发行记录](evidence/BASE-04/release100.md)。

发行记录列出全量普通测试、wheel 构建、独立安装、stdio 和本机原生冒烟的实际结果；未通过或未运行的检查按记录中的状态说明。

依次阅读 [长期规范](plan.md)、[当前计划](current.md)、[当前交接](handoff.md)。三份台账位于 `ledgers/`；共同功能、D00x分组和集中检查周期位于 `tracking/`；生成汇总位于 `generated/`。

历史开发范围：OpticStudio内建功能、官方STAR和HPC，原计划96组；发行前记录为7组完整验收、89组未完成。逐项状态见[scope.json](tracking/scope.json)、[原生功能表](remaining-origin-classification.md)及归档。

历史D001—D013顺序、逐项状态和证据保留在[current.md](current.md)、[remaining-ranked.md](remaining-ranked.md)、三份台账及[tracking](tracking/)中。当前维护工作限于已发行范围内的问题修复和兼容性维护。

历史协作材料：[并行任务与审查安排](parallel-development.md)及派工模板。

```powershell
.\.venv\Scripts\python.exe -B scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json --ranked development/remaining-ranked.md
.\.venv\Scripts\python.exe -B -m pytest tests/unit -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests/native --run-zemax -q -p no:cacheprovider
```

普通测试命令用于维护性改动。原生测试需要本机 OpticStudio、适用许可和受控模型；证据摘要在 `evidence/`，原始数据在 `.local/evidence`，大复现输入在 `.local/fixtures`。

历史开发过程和验收材料按原记录保留，不构成 1.0.0 功能完成声明。

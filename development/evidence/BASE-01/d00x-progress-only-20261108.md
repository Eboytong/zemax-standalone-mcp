# 当前计划统一采用D00x

2026-11-08。源码/发行基线0.1.62；当前剩余106条源记录、98个不同编号、96组共同功能。此次计划维护增加0个功能完成项。

开发安排及进度统一由`tracking/development-groups.json`的D001—D013成员和三份台账生成。原B007快照中的0/10表示旧发行周期尚无首次完成条目，现归入`archive/b00x-20261108/`。已发行版本的原始批次证据保留历史归属。

集中检查仍按每十个首次完成的共同功能执行。`tracking/verification-cycle.json`保存检查间隔、上次已检查条目集合及下一发行目标；统计工具按所有同功能台账记录均为done计算新增完成项，不再读取旧批次候选顺序或显示旧批次编号。

改动入口：`scripts/development/status.py`、当前计划、长期规范、交接、开发/产品导航及分派登记。生成结果为`generated/status.json`、`generated/remaining.md`、`generated/queue.json`、`remaining-ranked.md`。原96项归属和执行顺序保持。

定向命令：

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_development_status_report.py -q -p no:cacheprovider --junitxml=.local/evidence/development/BASE-04/parallel-01/review-d00x-progress.xml
```

最终定向结果：17通过，0.22秒。覆盖D00x顺序、别名、条目完成、范围、历史记录和跨开发组集中检查计数。生成快照中的发行记录将旧`next_action`标为`historical_next_action`，发行原件保留原字段；当前动作由D00x和台账提供。生成四份状态输出的命令成功。本次未启动原生实例。

# 开发入口

当前计划为[工程搜索与设计改进](plan.md)，生效日期2026-11-11。本期D017—D022六项，当前6/6；六项已完成，统一发行1.3.0。当前源码107工具、146种分析请求。主仓C:/Users/tonge/Desktop/mcp。

## 阅读顺序

1. [当前阶段](current.md)：六项交付与发行状态。
2. [计划](plan.md)：选题理由、任务书、检查及第7节证据要求。
3. [台账](ledgers/roadmap.csv)：状态、实际依赖、下一动作和证据。
4. [选题核对](evidence/PLAN-20261111/README.md)：源码、正式接口和外部参考依据。
5. [交接](handoff.md)：最近交付、运行状态及下一命令。
6. [源码参考](github-references.md)：固定commit、具体文件及借鉴边界。

已交付D001—D012、D014—D016共15项，见[1.1.0发行记录](evidence/release110.md)。其[旧计划与终态](archive/native-engineering-20261110/README.md)用于检索既有成果。本期完成数只计算D017—D022。

## 常用命令

从仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -B scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json --ranked development/remaining-ranked.md
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-roadmap
```

逐项运行相关定向检查。首次完成10项或阶段发行时集中检查；原生执行串行。开发安排在本目录维护，当前产品调用说明见[用户文档](../docs/README.md)。

## 文件职责

| 位置 | 用途 |
| --- | --- |
| plan.md/current.md/handoff.md | 任务书、顺序及当前交接 |
| ledgers/roadmap.csv | 本期实际状态与下一动作 |
| tracking/roadmap.json | 范围、依赖顺序、阶段和检查门槛 |
| generated/、remaining-ranked.md | 台账生成视图 |
| evidence/ | 实际验收及选题依据 |
| .local/evidence/ | 原始输出和工作副本 |
| archive/ | 已完成计划及历史资料 |

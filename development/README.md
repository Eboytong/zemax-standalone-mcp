# 开发入口

当前正式版**1.4.0，107个直接工具、146种分析请求**，compact11入口。本期[自主调用与渐进式披露](plan.md)编号D023—D027，完成5/5，集中检查及GitHub发行已完成。主仓`C:/Users/tonge/Desktop/mcp`。安装包与发布收据见[发行记录](evidence/release140.md)。

## 阅读顺序

1. [调研与判断](tool-disclosure-research.md)：工程工具取舍、实际schema大小、宿主能力及子Agent比较。
2. [当前阶段](current.md)：本轮交付、实施范围及下一项。
3. [开发计划](plan.md)：任务书、依赖、验收和第7节证据。
4. [台账](ledgers/roadmap.csv)及[生成工作表](remaining-ranked.md)：单项实际状态。
5. [交接](handoff.md)：下一命令、源码与运行状态。
6. [测量证据](evidence/PLAN-20261111-DISCLOSURE/README.md)：真实stdio、字节指标及复跑程序。

D017—D022已完成6/6，已发行1.3.0；[计划终态](archive/engineering-search-20261111/README.md)与[发行证据](evidence/release130.md)保留。此前1.1.0已交付范围见[归档](archive/native-engineering-20261110/README.md)。历史完成数与本期工作包分列。

## 常用命令

从主仓根目录执行：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 development/evidence/PLAN-20261111-DISCLOSURE/measure.py
.\.venv\Scripts\python.exe -B scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json --ranked development/remaining-ranked.md
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-roadmap-disclosure
```

逐项做定向检查，D027统一集中检查与发行；原生执行串行。用户使用说明见[产品文档](../docs/README.md)，本期研究与计划在development维护。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| plan.md/current.md/handoff.md | 任务书、状态及接手 |
| tool-disclosure-research.md | 本次技术研究与方法选择 |
| ledgers/roadmap.csv | 本期状态、动作及证据 |
| tracking/roadmap.json | 顺序、依赖及发行门槛 |
| generated/、remaining-ranked.md | 台账生成视图 |
| evidence/ | 摘要、可重跑命令和参考 |
| .local/evidence/ | 原始工具列表、运行输出和模型 |
| archive/ | 已发行计划和历史索引 |

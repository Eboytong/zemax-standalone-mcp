# 开发入口

当前依据[交付与维护规范](plan.md)，生效日期2026-11-10，专题编号为D001—D012、D014—D016。产品基线1.0.0，本地发行1.1.0。主仓为`C:/Users/tonge/Desktop/mcp`。

## 阅读顺序

1. [当前阶段](current.md)：本阶段顺序与下一项。
2. [开发计划](plan.md)：15项任务书、依赖、检查节奏及第7节证据要求。
3. [专题台账](ledgers/roadmap.csv)：状态、排期、具体动作和证据。
4. [GitHub源码参考](github-references.md)：固定commit、文件、适配差异和许可。
5. [交接](handoff.md)：最近结果、运行状态及下一命令。

[剩余工作表](remaining-ranked.md)、[状态JSON](generated/status.json)、[队列JSON](generated/queue.json)从台账生成。15/15项已完成，当前待开发队列为空；本地1.1.0交付102工具/144分析请求。

## 常用命令

从仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -B scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json --ranked development/remaining-ranked.md
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-roadmap
```

逐项运行对应定向测试。累计完成10项或阶段收尾时进行集中回归、构建、独立安装和真实stdio。原生执行串行，使用自有工作副本；模型、许可、实际设置和关闭结果按第7节记录。

## 文件职责

| 位置 | 用途 |
| --- | --- |
| plan.md/current.md/handoff.md | 任务书、当前排程、当前交接 |
| ledgers/roadmap.csv | 专题状态与下一动作的维护入口 |
| tracking/roadmap.json | 计划范围、顺序和集中检查规则 |
| tracking/github-references.json | 固定版本源码参考清单 |
| generated/和remaining-ranked.md | 自动生成视图 |
| evidence/ | 可读验收摘要和已发行能力记录 |
| .local/evidence/ | 原始结果、工作副本和探查输出 |
| archive/ | 技术历史与原始资料检索索引 |

产品调用说明见[用户文档](../docs/README.md)，当前发行事实见[1.1.0记录](evidence/release110.md)。协作归属见[协作安排](parallel-development.md)。

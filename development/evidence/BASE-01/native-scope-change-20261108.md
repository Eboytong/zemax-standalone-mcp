# 原生开发范围调整

日期2026-11-08；用户要求仅保留Ansys原生功能开发。源码/发行0.1.62，OpticStudio基线24.2.0 build240529，B007为0/10。

## 范围与状态

保留内建61组、官方STAR30组、HPC5组，共96组；待处理106条源记录、98个不同编号。19组移出项的原始行、2个工作包及原计划快照见[归档](../../archive/scope-native-only-20261108/README.md)。执行状态、原始失败和历史验收保留，本次维护的功能完成数为0。

三项衍射效率和散射/solve聚合按当前原生范围调整声明及依赖，保持implemented，后续依据原数值容差和适用原生证据判断完成。用户代码宿主、宏/DLL和Speos接收端的产品实现及历史测试继续保留。

## 本次检查

仅运行开发统计相关普通测试并重新生成status、remaining及queue。命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_development_status_report.py -q -p no:cacheprovider --junitxml=.local/evidence/development/BASE-01/native-scope-tests-20261108.xml`。实际结果：11项通过，0失败，耗时0.17秒；XML保留。

本次未运行原生实例、全量回归或wheel构建。最近CLR加载失败与0.1.62此前发行通过分别记录于当前交接和release062.json。下一步先恢复CLR，再按当前清单逐项推进。

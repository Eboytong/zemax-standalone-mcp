# STAR许可要求及D011/D012解除条件

2026-11-09；源码0.1.62工作区，主仓`C:/Users/tonge/Desktop/mcp`。本项核对许可正式依据，补充能力与错误详情，沿用已有原生模块检查。

## 计划与正式依据

本机2024 R2手册The STAR Tab、印刷页1708明确要求Ansys Zemax OpticStudio Enterprise级许可。资料为`C:/Program Files/ANSYS Inc/v242/Zemax OpticStudio/OpticStudio_UserManual_en.pdf`，可检索文本`.local/evidence/development/EXT-EXPORT/manual042.txt`，章节中的Enterprise License Required段。原文定位摘录另存`.local/evidence/development/EXT-STAR/license-requirement-20261109/manual-excerpt.txt`。

已有实际执行为24.2.0/build240529、PremiumEdition，IsSTARModuleEnabled=false，get_star_data返回FEATURE_UNAVAILABLE。原始记录在`.local/evidence/development/BASE-04/scope-conditions-20261109-r2/`；模型/修订保持、未提交节点作业、native.closed=true、forced=false，完整过程见[条件记录](../BASE-04/native-scope-conditions-20261109.md)。本轮没有重复原生启动；该记录证明所测实例当前未启用模块，手册提供适用许可的解除方向。

## 实现与定向检查

`star.py`为模块未启用错误增加required_license、requirement_source及next_action。错误码FEATURE_UNAVAILABLE、现有feature/enabled字段保留；Sequential前置及逐次实时模块检查沿用。失败发生在STARData访问和模型修改之前。

`get_capabilities.star_operations`返回相同许可依据，更新STAR文档位置与验收条件；各操作的实际许可判定仍读取IsSTARModuleEnabled。请求字段及schema未改变。

命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_star.py tests/unit/test_star_controls.py tests/unit/test_star_materials.py tests/unit/test_star_analyses.py tests/unit/test_contracts.py -q -p no:cacheprovider --basetemp=.local/tmp/star-license-20261109 --junitxml=.local/evidence/development/EXT-STAR/license-requirement-20261109/unit.xml
```

153 passed in1.50s。状态汇总工具另20 passed in0.30s，XML为同目录status-unit.xml；生成台账汇总仍为92组、99条源记录、94个编号。检查模块false时不访问STARData、错误信息含正式条件、修订和修改事件保持，并覆盖受影响STAR读写、控制、材料和专题消费者。

## 影响范围与解除顺序

对应分组定义D011的16组与D012的14组，共30组。24条操作台账和6条分析台账补入同一正式依据，保留各自资源、接口、数值与生命周期缺口及原状态。

1. 检查本机是否有可用Enterprise级许可，并按实际许可配置创建新原生实例。
2. 读取IsSTARModuleEnabled；true后以单个受控FEA执行导入、拟合、采样及卸载最小检查。
3. 按D011数据依赖推进D012组件与专题，逐项验设置、数值、重载、取消/恢复和关闭。

许可条件满足后，仍需逐项完成受控数据和正式结果验收。HPC返回null的原因另行探查，本记录不变更其许可判定。当前完整验收仍4/10、剩余92组；本项未新增完整功能。

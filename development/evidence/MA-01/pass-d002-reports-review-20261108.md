# D002 材料四专题审查（2026-11-08）

本轮对 GlassMap、AthermalGlassMap、DispersionDiagram、DispersionvsWavelength 的当前系统报告、独立目录参考和正式选择缺口重新审查。使用已保存的原生输出，未重新创建 OpticStudio 实例。

| 条目 | 本轮实际结论 | 剩余工作 |
| --- | --- | --- |
| MA-01.GlassMap | SCHOTT 报告 346 行全部按大小写归一匹配目录；原先七项为目录拼写差异。OHARA 原记录 410 行参考继续保留 | 专题目录/材料/波长等正式选择和采用回读；用更新的目录匹配重新执行原生身份用例 |
| MA-01.AthermalGlassMap | 独立正式热光公式覆盖 359/364 行，最大绝对误差 4.9452123175592664e-9，门槛 5e-9。B270 使用公式1后通过 | F2HTI 的 CD 首系数占位、P-SK57Q1/REALVIEW_2.0/LF5G15/SF66 缺 TD；正式专题选择；环境温变原生对照 |
| MA-01.DispersionDiagram | 已有指数曲线独立参考最大误差 4.96616834322339e-8，门槛 5.1e-8；99 个中心差分节点最大误差约 3.49e-5，门槛 5e-5 | 原生 dn/dλ 数值定义未确认，解析导数 4 点超限，最大 5.919e-8 对 5.1e-8；材料/环境正式选择 |
| MA-01.DispersionvsWavelength | 同一正式色散模型和已保存报告的逐点复算，采用原有参考及门槛 | 正式输入选择、dn/dλ 定义和受控原生重验 |

## 交付与检查

已集成 `tests/support/athermal_reference.py`、`tests/unit/test_athermal_reference.py`，补充 Schott/Sellmeier、空气折射率温导数、绝对/相对折射率转换、D1/D2/E1 项、目录占位及有限性检查。任意温度路径有独立公式实现，当前已验证条件为目录参考温度；温变路径保留显式条件及后续用例。

主区相关检查 77 项通过，见 `.local/coordination/integration-athermal-reference.md` 与 `.local/evidence/development/MA-01/athermal-reference-20261108/review-athermal-reference-main.xml`。实际命令、原目录行、逐点输出和来源手册存放于该目录的 `final-report.md`、`athermal-reference.py`、`athermal-reference.out.json`、`athermal-gaps.json`。

已有原生报告的任务、模型保持、分页/PNG、正常关闭和 stdio 断开保留在各专题历史证据。当前本轮复算的 Python 文件已关闭；新原生生命周期没有执行。四项完整功能继续保留原范围，新增完成数 0。正式设置选择与缺失目录数据的解除条件按上表逐项处理。

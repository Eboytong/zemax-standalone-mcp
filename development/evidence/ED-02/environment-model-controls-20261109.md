# MaterialModel环境条件修正与八组复测

## 正式定义与计划

2026-11-09查阅本机2024 R2 CHM解包主题Environment.html、Using_Model_Glasses.html、Environmental_Effects_on_Index_for_Gradient_Index_MIL.html。解包路径沿用[定义记录](parallel-02-material-definition-20261108.md)。

Environment明确规定：Adjust Index Data To Environment关闭时，温度固定20°C、压力固定1 atm。此前控制矩阵基线正好关闭该选项，导致温压请求拒绝，不能据此认定温压功能不可写。现计划显式启用选项、设置20°C/1 atm基线后重跑C1/C2/C3。

Using Model Glasses给出精确d/F/C、Abbe定义、dPgF名称及可见光折射率近似精度约0.0001；该页没有给出完整色散重建公式或系数。原“完整公式待转录”的后续动作改为取得正式算法/系数依据或厂商对原数值差异的说明。dPgF相对Normal Line定义仍需数值参考。

## 实现与普通检查

系统设置新增最终条件的写前检查：环境修正关闭且请求非20°C/1 atm时，返回SETTING_INACTIVE、required_setting和正式条件来源。与请求一起启用修正时可写温压；省略字段保持原值。检查位于_mutate之前。

`tests/unit/test_environment_conditions.py`9项覆盖最终条件与局部修改；联合modeling/material reference/probe request共75项通过。修正后的矩阵及几何参考联合27项通过。请求字段保持不变。

## 原生环境检查

命令：`python -B -m pytest tests/native/test_environment_conditions_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/env-native-20261109 --junitxml=.local/evidence/development/ED-02/environment-conditions-20261109.xml`。

1 passed in11.08s，原始`.local/runs/runs/environment_conditions_4c0a65d905/`。关闭修正时压力0请求在写前拒绝，partial_changes_possible=false，系统设置及model_revision保持；一起启用后压力0/温度10实际采用，最后恢复原设置并断开。

## MaterialModel最终矩阵

命令：`python -B -X utf8 scripts/probes/D002-MODEL_GLASS/model_glass_control018.py .local/evidence/development/ED-02/mm-20261109-r3`。

基线开启环境修正。8 cases/11 writes；C1关闭修正、C2压力0、C3温度10均执行成功；diagnostics_passed=true，solve_readback_passed=true，save_reload_passed=true。vary_abbe=True覆盖，五组模型保存重载通过。

B0精确谱线Vd60.02418808120307；C1相同；C2为60.022015709596765；C3仍60.02418808120307。Nd/Vd主门槛保持原值，acceptance_passed=false。请求、直接折射率、双入射角Snell、环境实际值与恢复、逐点误差完整保存anchors.json。

closed=true，native.closed=true、forced=false、无cleanup_error、无活动任务。r2的环境拒绝记录作为已纠正的基线条件问题保留，r3作为本轮最终有效环境控制。

MaterialModel保持implemented；剩余为精确谱线数值差异、dPgF和环境独立算法参考及完整失败恢复模型比较。新增完整验收0。

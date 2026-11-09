# Agent 1任务书：D001偏振、透射与光纤耦合

范围为`PO-01.PhaseAberration`、`PO-01.PolarizationRayTrace`、`PO-01.Transmission`、`WP-01.FiberCouplingSettings`四组共同功能。按此顺序逐项推进；每项开始先发布实施计划。协作、原生排期和交付方式见[并行安排](../../parallel-development.md)。

## 当前证据与缺口

读取`development/evidence/PO-01/`下的`phase-aberration-probe20261108.md`、`polarization-ray-trace-probe20261108.md`、`transmission-probe20261108.md`，以及`development/evidence/WP-01/fiber-coupling-acceptance20261108.md`。

相位报告含0.55µm、中心视场、Jx/Jy及201点双方向数据，但缺正式选择回读及明确相位单位。偏振光线报告包含电场/膜层量，射线选择未确认。透射报告包含32×32瞳积分及逐场/波长量，专用选择未确认。光纤专题需核对专用设置，现有POP重叠参考已有适用证据。

## 可立即并行开展

1. 阅读现有专题文本、`scripts/probes/PO-01/phase_aberration_reference.py`、`polarization.py`/`polarization_models.py`、`transmission_fan.py`和POP接收器/耦合入口。建立四项“输入—实际设置—输出—参考”表。
2. 从正式定义确定Jones基底、振幅/功率、相位零点、传播相位及主光线参考。相位单位未确定前，分别列出可区分假设和实验预期；确认定义后固定验收单位及容差。
3. 建立空气—玻璃平面、无膜层/已知膜层、中心/离轴光线参考；光纤使用受控高斯复场重叠。新参考放任务独立模块，复用现有解析公式。
4. 确认正式接口后补有类型请求、设置写入/回读、报告解析和结果身份。保留原始文本、无效/零振幅状态、单位、坐标和计算来源；共用注册改动单列为集成补丁。

## 原生作业申请

先申请最小设置/输入探查，再申请数值矩阵。依次覆盖S/P及混合偏振、中心/离轴、不同波长、适用的相位跨周和零振幅；透射区分单光线与瞳积分；光纤区分专题输出与POP替代范围。

采用适用的已有门槛：偏振瞳电场幅度/功率参考`atol=1e-8, rtol=1e-7`，已有相对相位比较`atol=1e-6 degrees`，POP重叠绝对差`5e-4`。这些门槛只用于已匹配的量和定义；新相位像差验收先写出参考及容差依据。

完成相关分页、图像/报告、成功/失败/取消、同会话复用、临时条件恢复、保存重载及关闭。每项作业提交给Agent 0串行执行。

## 文件归属与检查

归属建议：新增偏振专题请求/适配/参考模块及独立的相位、偏振光线、透射、光纤测试。现有`polarization.py`相关修改归本任务；POP共享模块变化提供最小补丁。

`analysis_models.py`、`analyses.py`、`models.py`、`backend.py`和总schema的接入修改单列。`tests/support/numeric_reference.py`沿用，新增专用参考另建文件。

先运行`tests/unit/test_polarization.py`、`tests/unit/test_transmission_fan.py`及新增普通测试；原生消费者从`test_polarization_live.py`、`test_transmission_fan_live.py`、`test_pupil_coupling_live.py`中选择受影响用例。四项专题的新增原生用例另列精确命令。

## 审查交付

四项分别提交合同、调用例子、设置采用、数值比较、分页/输出和生命周期证据；逐项给出`implemented/blocked/done`建议及剩余条件。若正式专题选择仍缺失，说明已支持输出和缺口，避免把既有瞳图或POP结果自动计作专题整项完成。

向D010任务提供可复用的S/P方向、电场基底与功率归一化说明，供联合审查。

# YNI显式波长与完整条目验收

日期2026-11-08。源码0.1.61工作区，OpticStudio24.2.0 build240529 PremiumEdition，Python3.14。范围为当前顺序系统各光学曲面的YNI贡献，保留默认专题报告并新增明确波长选择。

## 实施计划及接口

先用本机正式YNIP(Surf,Wave)查询核对原生专题定义及波长参数，再接入typed request。省略wavelength保留原生YNIContributions专题及文本附件；显式正整数使用GetOperandValue逐面查询，记录native_operand、native_arguments、波长微米、镜头单位、实际配置和任务修订。任务资源归属活动系统，不创建额外分析窗口或SystemTool。通过复合任务逐面yield提供取消边界及rows/series分页。

正式依据为本机MeritOperandType.YNIP=333及2024 R2手册YNI Contributions对该操作数的说明。原生探查程序`scripts/probes/CV-01/yni_operand_probe.py`；完整三波长×六面查询和断连证据`.local/evidence/development/CV-01/yni-operand-9af2235f0d/summary.json`。

## 请求和数值参考

`{"request":{"kind":"yni_contributions","wavelength":2}}`。默认请求`{"request":{"kind":"yni_contributions"}}`继续有效。波长0、类型错误由请求拒绝；系统越界在创建任务前拒绝。

Cooke主波长2=0.55µm的六项操作数对五位小数原报告：预设atol5e-6、rtol0；最大差2.5049198917326265e-6。波长1=0.48µm检查身份及第二面变化。独立球面模型为空气入射、准直边缘光线高度5mm，曲率半径±20mm、玻璃N-BK7：近轴I=Y/R，预设YNI=Y²/R=±1.25mm，门槛atol1e-10+rtol1e-10，两符号通过。

## 检查与生命周期

普通命令`.venv/Scripts/python.exe -B -m pytest tests/unit/test_yni_contributions.py tests/unit/test_contracts.py tests/unit/test_basic_analyses.py -q -p no:cacheprovider`：58通过，涵盖精确参数、非有限/空结果、系统越界、请求边界及原生查询前取消。共用分析可选波长检查补充None判断，默认专题路径已在原生对照执行。

原生命令`.venv/Scripts/python.exe -B -m pytest tests/native/test_yni_contributions_live.py::test_yni_explicit_wave_operand_report_and_spherical_reference --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/CV-01/yni-explicit-wave-repeat-20261108.xml`：1通过，10.41秒。原始调用和逐项参考`.local/runs/runs/yni_explicit_wave_76e9dc2cfc/`。报告与操作数任务均完成；操作数路径不创建原生工具；rows分页返回面3/4，Cooke设置保持，最后disconnect成功。默认报告分页/关闭沿用本日yni-recovery-audit原生通过证据。

首次集成发现默认None在共用波长范围检查触发TypeError，已修复并在最终默认报告加显式请求组合验收通过；首次失败XML保留。FRU初始化警告仍在，不影响本次数值通过，根因继续归BASE-04。

## 结论

CV-01.YNIContributions声明范围完成，标记done，B006从5/10增加至6/10。本轮保持0.1.61工作区基线，达到十项后集中发行。文档、schema、示例和台账同步；下一项源光谱输入身份审计。

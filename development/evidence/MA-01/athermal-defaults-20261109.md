# 消热差材料缺省数据、波长换算与材料名回读

日期：2026-11-09。D002，MA-01.AthermalGlassMap。源码0.1.62工作树，Python3.14，OpticStudio24.2.0 build240529 PremiumEdition。完整条目状态保持implemented/blocked的既有逐来源记录。

## 开工范围与正式依据

本轮处理原359/364独立参考中的五种缺口：F2HTI首CD系数占位，P-SK57Q1、REALVIEW_2.0、LF5G15、SF66缺TD。计划比较固定相对折射率与固定绝对折射率两种假设，使用19.99/20/20.01°C、0.55µm、1atm，环境修正显式开启；以BK7G18及B270作有数据/零系数控制。

本机手册第118—119页规定先将系统空气波长换算到材料参考空气再计算折射率；缺热光数据时六系数默认零，绝对热光变化为零。第1352—1353页规定消热差图的热功率在材料参考温度计算、压力1atm，使用系统最小/中心/最大波长。摘录在r2/manual。三个系统温度15/20/25°C的图表比较用于检验此参考温度定义。

## 实现与失败修复

新增scripts/probes/MA-01/athermal_missing_data.py：保存原AGF、正式目录属性和有效系数、系统设置、GetIndex、原生图表、任务终态、恢复及关闭。支持--evaluate离线独立公式复算。

首轮发现F2HTi写入后原生回读F2HTI被误判未采用，返回PARTIAL_UPDATE。原始拒绝及失败曲面状态完整留存，最终基线恢复和断开成功。backend._write_cell仅在材料名写入时允许大小写等价；其他字符串继续精确比较，替换为其他材料仍拒绝。r2和r3中的F2HTi写入成功，实际曲面值为F2HTI。

独立参考新增system_relative_index，遵循手册的参考空气波长换算、色散、绝对热光变化、系统空气归一化步骤。原温度参考函数及其验收范围保留；新函数不将缺系数自动填零。缺省输入先经正式IMaterialsCatalog回读确认，再由探针显式构造。

## 实际执行与数值

COMPLUS_LoadFromRemoteSources=1；串行执行：

- `.venv/Scripts/python.exe -B -X utf8 scripts/probes/MA-01/athermal_missing_data.py .local/evidence/development/MA-01/athermal-missing-data-20261109`：完成对照，F2HTi有上述设置误判；原记录保留。
- 同命令改目录为athermal-missing-data-20261109-r2：修复后七种材料均执行完成。
- 同命令改目录为athermal-missing-data-20261109-r3：增加正式目录属性/系数与参考温度回读，七种材料均完成。
- `.venv/Scripts/python.exe -B -X utf8 scripts/probes/MA-01/athermal_missing_data.py --evaluate .local/evidence/development/MA-01/athermal-missing-data-20261109-r3/probe.json`：离线对照全部保存值，写independent-reference.json，不创建应用。

四种缺TD材料均正式回读D0/D1/D2/E0/E1/Ltk为零、Temp=20；按手册零缺省建立独立热功率参考。F2HTi的正式K1为0，其他五个实际系数与非占位AGF系数一致；独立公式使用正式有效系数，并保留原始占位及输入来源。此参考验证实际材料定义，不替代厂商原目录中的缺失系数。

| 材料 | 热功率绝对误差，1/°C |
| --- | ---: |
| BK7G18 | 3.931165794775197e-9 |
| B270 | 1.358497498924648e-9 |
| F2HTI | 3.023700666649e-9 |
| P-SK57Q1 | 5.424829767517887e-10 |
| REALVIEW_2.0 | 8.554167978909712e-10 |
| LF5G15 | 3.511642908318888e-9 |
| SF66 | 4.75491657390027e-9 |

七种材料在15/20/25°C图表中的热功率不变，21/21比较通过原5e-9门槛；符合材料参考温度定义。原359行历史参考保留，本轮补齐其五种缺口的实际输入参考，没有重新宣称本轮全364行已运行。

七种材料在19.99/20/20.01°C的GetIndex与独立环境折射率21/21通过预定1e-12门槛，最大2.1094237467877974e-13。仅用空气温导数的初始假设未包含波长换算，保留初始差异；按正式手册补齐换算后对应通过。

普通最终218项通过，1.13秒，XML：.local/evidence/development/MA-01/athermal-material-identity-final-20261109.xml。覆盖材料名实际采用/拒绝、模型写入、配置精度、变量、温度请求、AGF占位位置、独立热光参考、光纤解析、材料报告与状态工具。

## 生命周期与剩余动作

r3所有三个图表任务成功，报告保留分页及原生数据；所有目录查询经owned_catalog关闭。probe.json中error为空，各材料error为空，settings_restored=true、surfaces_restored=true、cleanup_failures=[]；disconnect.connected=false。未新增取消/失败恢复的完整条目声明。原生FRU警告保留于执行输出。

五种材料的当前缺省输入参考已解释。完整验收仍需色/热功率边界、替代模板、ReferenceGlass正式可脚本化选择及采用回读，随后补相应失败/取消与保存重载。原生AS_Default未提供这些成员，等待正式接口或受支持CFG键。下一可执行动作：沿D002处理材料专题选择及导数正式定义，随后MaterialModel/Gradium有新依据的控制实验。集中检查4/10、剩余92组保持。


后续参考修正：更大温压范围对照发现空气公式须统一使用系统输入波长。按手册第119页修正system_relative_index后，对本记录r3重算21个环境折射率最大差为2.220446049250313e-16，热功率结论保持。旧独立参考已保留；细节见ED-02/model-environment-refresh-20261109.md。

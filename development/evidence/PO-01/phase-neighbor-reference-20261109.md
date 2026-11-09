# 相位像差：相邻光线参考与原生复现

2026-11-09；主仓`C:/Users/tonge/Desktop/mcp`。条目`PO-01.PhaseAberration`，D001；源码0.1.62工作区，101工具/132分析；安装包0.1.62未重建。原生OpticStudio24.2.0/build240529、PremiumEdition，项目`.venv`，进程级`COMPLUS_LoadFromRemoteSources=1`。

## 声明范围与本项计划

完整条目要求正式视场/波长/Jones输入、相位定义、有效曲线与生命周期。本轮处理轴上Cooke数值残差：先检查保留文本精度及采样归属，再按手册的相邻光线插值构造独立参考，并进行一次新的串行原生复现。原门槛为`1e-6 degrees / 360 = 2.7777777777777776e-9 waves`。

## 正式依据与计算

本机`C:/Program Files/ANSYS Inc/v242/Zemax OpticStudio/OpticStudio_UserManual_en.pdf`，Phase Aberration讨论，印刷页904（条目起于903）。手册描述参考主光线相位，并在零强度分量导致相位不确定时，用主光线两侧的光线平均插值；未规定其实际间距及内部复数平均细节。本轮对本机401点表验证相邻`pupil=-0.005,+0.005`候选。

原生表相位为9位小数，单个数值的舍入半宽为`5e-10 waves`。此前约`2.5e-7 waves`残差在全部非中心点近似恒定，中心点为零，超出文本舍入解释范围。

独立几何光程仍采用逐面位置、GetGlobalMatrix及前一介质GetIndex，适用于本控制的轴上平行入射、无反射Cooke系统。令`q = arg(E/E_chief)/(2π) + (OPL-OPL_chief)/lambda`；参考为两侧q的圆周平均。保留此前固定的`q + native`符号候选，不利用native表值拟合参考偏移。比较`remainder(q-reference+native,1)`。中心原生零值单独记录为参考标记；零振幅X分量保留indeterminate。

脚本`phase_reference_diagnostics.py`并列保留原中心参考误差和相邻参考误差。合成测试覆盖跨周期、错误几何、零振幅、独立参考不随native改变及真实残差不被隐藏。该结果确认当前轴上控制与上述符号/参考组合对应；任意模型的绝对相位约定仍按条目剩余范围验收。

## 输入、执行及原始结果

输入为官方Cooke 40 degree field.zos，轴上0度，波长编号2、0.55µm，Jones=(0,1)、两初相位0度。实际表头、系统设置、曲面、矩阵、折射率、任务请求及分页回执均在probe.json。

离线保留数据命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/PO-01/phase_reference_diagnostics.py .local/evidence/development/PO-01/phase-path-20261109/probe.json .local/evidence/development/PO-01/phase-neighbor-20261109/retained-comparison.json
```

新原生命令：

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/PO-01/phase_propagation_reference.py .local/evidence/development/PO-01/phase-neighbor-native-20261109
```

新数据：`.local/evidence/development/PO-01/phase-neighbor-native-20261109/probe.json`。离线与新原生数值结果一致：

| 方向/分量 | 非中心比较数 | 旧中心参考最大误差/waves | 相邻参考/waves | 新最大误差/waves | 原门槛判定 |
| --- | ---: | ---: | ---: | ---: | --- |
| sagittal Y | 400 | 2.499509153593843e-7 | 2.4950844296497363e-7 | 5.82678922472768e-10 | 通过 |
| tangential Y | 400 | 2.5001445071084344e-7 | 2.495083636811109e-7 | 5.668621128052109e-10 | 通过 |
| sagittal X | 0 | — | — | — | 401点零振幅，indeterminate |
| tangential X | 0 | — | — | — | 401点零振幅，indeterminate |

两个中心标记均为0；没有纳入800个非中心点误差统计。

## 设置、终态与关闭

新进程的9个任务（一项PhaseAberration、一次偏振批量追迹、七个曲面几何追迹）均succeeded；保留分页回执。系统设置与曲面前后相同。shutdown检查点成功，native.closed=true、forced=false、native.error=null，进程exit_code=0。原生标准输出仍含`FRU__delta_init(): Attempt to start when running!`；关闭回执及退出单独记录。此次未新增取消/失败/保存重载实验；相关范围沿用已有证据或继续保留验收动作。

## 普通检查与实现

命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_phase_reference_diagnostics.py tests/unit/test_phase_propagation_reference.py tests/unit/test_phase_aberration.py tests/unit/test_native_controls.py -q -p no:cacheprovider --basetemp=.local/tmp/phase-neighbor-final-20261109 --junitxml=.local/evidence/development/PO-01/phase-neighbor-20261109/unit-final.xml
```

最终83 passed in1.68s，XML见unit-final.xml；初轮另83项通过，集合重叠。产品结果的phase_reference补充手册插值说明，原生数据保持原值；phase_unit_verified及sign声明继续保留原有核验范围，请求schema未改变。

## 状态与下一步

轴上Cooke原数值残差已由有手册依据的相邻参考候选解释，并在新原生会话复现。完整条目保持in_progress：正式视场/波长选择、非轴上及更多Jones的绝对相位与插值规则、完整生命周期仍待验收。下一步先取得正式选择入口或正式等价路径及同条件输入身份；已有相同AS_Default缺口证据沿用，条件不足时继续D001偏振光线及光纤条目。完整验收累计4/10、剩余92组保持。

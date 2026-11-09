# PO-01.PhaseAberration 受控参考与阻塞

日期：2026-11-09；源码0.1.62；OpticStudio24.2.0 build240529 PremiumEdition。执行主仓和COMPLUS开关沿用D001。

## 实施计划与执行

本项先运行kind-only原生PhaseAberration，再用同一Cooke模型、同一0.55µm波长、同一401点弧矢/子午瞳坐标执行J_y批量偏振追迹。零振幅X分量保留为indeterminate；Y分量按主光线复场相位差比较，原门槛1e-6度（2.7777777778e-9 waves）。原生任务、批量任务、分页、结果文件和断开均完成。

## 结果

原生报告打印Y相位约−0.0118至−0.0092 waves。批量复场相位差最大约0.501152588 waves（弧矢）和0.501020378 waves（子午），均超原门槛。X分量因Jx=0，401点全部标记零振幅不可判定。真实报告及802行批量结果保存在`.local/evidence/development/PO-01/phase-reference-20261109/`；原生UTF-16文本、CSV、JSON和工作副本均保留。

## 定位结论

误差不是普通报告精度问题：批量复场包含从入口瞳到像面的传播相位，而PhaseAberration按原生定义以主光线为参考并去除几何/光程项。当前批量接口的偏振模式不允许同时取得OPD（`BatchRays`在偏振时拒绝`opd=true`），因此直接取 `arg(E/E_chief)`不能作为相同物理量。现有逐段PolarizationRayTrace可取得传播相位，但尚未建立与PhaseAberration表逐点一致的几何光程减除组合。

## 状态与解除条件

本轮不放宽1e-6度门槛，条目保持in_progress。解除条件为取得正式PhaseAberration选择设置或建立逐点传播相位/几何光程参考，使批量结果与原生“chief-ray-referenced polarization phase aberration”具有相同定义；随后再验中心/离轴、S/P和混合Jones、保存重载及取消恢复。D001下一项可先推进PolarizationRayTrace或光纤耦合，不重复同一未区分实验。

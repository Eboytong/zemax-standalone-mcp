# D020 评价函数构建验收

日期2026-11-11；源码a099540加当前修改，实际导入主仓src。OpticStudio24.2.0/build240529 Premium Standalone，Python3.14。

正式探查程序`scripts/probes/D020/native_merit_probe.py`确认OPDC/OPDM/OPDX有效列3—7依次为Wave、Hx、Hy、Px、Py；原生向导生成连续OPDX组。原始反射与行回读位于`.local/evidence/development/D020/native-columns.json`。原生对象为系统所有的MFE；预览使用CopySystem并Close(False)。

`run_merit_program`交付原生向导、完整圆瞳/环瞳节点、三种OPD参考、配置/波长选择、目标/尺度/权重、几何约束、预览/应用/回读/求值及逐目标贡献。默认独立副本，应用保留检查点。修正取消请求派发前推进计算的问题；取消请求优先设置标志，再由任务边界关闭副本。

普通检查35通过，命令及XML为`ordinary.xml`。数学参考覆盖常数、X/Y倾斜、离焦和非对称多项式的完整瞳积分以及环形遮拦，积分误差门槛1e-13。额外共享任务回归待发行尾检。

真实stdio原生用例1通过，77.10秒。受控N-BK7双球面单片，5mm入瞳，0.55µm，双视场；使用非轴上Hx=.3、Hy=.7。6环32臂与12环64臂的OPDC/OPDM/OPDX RMS分别为0.5736451281143352/0.31120950778296025/0.3033089374069091waves，最大采样差9.05e-13waves；预定门槛1e-5waves+1%。厚度约束实际值3mm，目标5mm，正确报告2mm超限。预览保持MFE；应用、越界失败、实际cancelled、原MFE保持及副本关闭通过，stdio正常断开。

原始调用和检查：`.local/runs/runs/d020_merit_program_6df14929ec/`。命令：`pytest tests/native/test_merit_program_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d020-native3 --junitxml=development/evidence/D020/native.xml`。

补充有焦GridPhase受控模型验收通过：0.55µm、5mm入瞳、N-BK7曲率±50mm/厚3mm，MCE控制后空气48/50mm。相位含径向二次、X/Y倾斜和非对称三次项，公式、DAT和导数由tests/native/test_merit_program_phase_configuration_live.py保存。两配置×轴上/离轴×三种OPD参考共12组，4环16臂；独立批量OPD加权均值和最小二乘去倾斜参考，预定门槛1e-5 waves + 1%×最大参考值。最大绝对差9.630008140604218e-5 waves，OPDC/OPDM约1.6e-12，全部通过。原生向导选择配置1、视场2并生成MFE，回读、实际求值、保存重载和MCE恢复通过。native-phase-focused.xml记录1通过、65.09秒，原始目录.local/runs/runs/d020_phase_mce_wizard_074e9ee7c8/。

向导设置改为写入完整组合后回读，解决UseAllConfigurations关闭后、尚未指定ConfigurationNumber时原生开关延迟生效造成的误拒绝；单测覆盖该依赖，ordinary-targeted.xml记录71通过。

历史控制实验中，无光焦度平板的离轴OPDX与Python去倾斜参考差44.38 waves；该结果保留为参考定义诊断。有焦任务采用上述聚焦透镜完成全部轴上/离轴验收。取消、失败和预览保持证据沿用本页前述用例。D020功能验收完成。G3采样假设经审查后采用完整2π节点，固定源码与许可见开发参考记录。

统一发行回归首次在加密OPD构建时触发状态查询60秒超时。已将OPD写入/回读和结果行读取改为每16项交还任务控制，并在边界检查取消；原生求值定义、权重和组行保持相同。49项构建/联合玻璃/去敏感化普通检查通过，见ordinary-cooperative.xml。修复后原生复测见统一发行记录。

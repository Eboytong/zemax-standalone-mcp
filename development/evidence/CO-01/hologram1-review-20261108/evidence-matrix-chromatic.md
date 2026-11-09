# CO-01.DiffEfficiencyChromatic：原生 Hologram1 证据矩阵（阶段一）

- 声明范围：原生 Hologram1 体全息（Par13=1）波长扫描，S/P 双偏振，0.45–0.65 µm，效率无量纲；视场取 Bragg 角 26.56505117707799°。依据 `scope.json` 原生声明与 D010 item 2。
- 证据运行：`…\.local\runs\runs\diff_efficiency_offaxis059_native_bdfaeee137`（会话 `d5946d8262334d3cb2ff2ca6358a2622`）。
- 参考/容差：`tests/support/kogelnik.py::unslanted_transmission`（构造 λc=0.55 µm、θc=atan0.5、n=1.5、dn=0.02、d=10 µm、Fresnel 关闭、两侧空气）；`atol=1e-6, rtol=1e-5`。

| 维度 | 既有证据（文件 / 定位） | 结论 | 缺口 / 复测条件 |
| --- | --- | --- | --- |
| 当前声明 | `scope.json`、`development-groups.json` D010 item 2 | 仅原生 Hologram1 计入 | 无 |
| 输入身份 | calls.json：同一 Hologram1 模型（Par1-8、Par13-21），field_type=Angle 场 (0, 26.56505117707799)，wavelength 1 = 0.55 µm（扫描轴独立于系统波长） | 扫描以视场/系统波长为固定条件 | 用例未断言「扫描轴≠系统波长」这一语义 |
| 设置写入 | `configure_diff_efficiency` → `SampleSize='S_65'`、`MinWavelength=0.45`、`MaxWavelength=0.65` | 只写请求字段（无 MinAngle/MaxAngle，被类型校验拒绝） | — |
| 设置回读 | `task.settings.native`：`SampleSize='S_65'`、`MinWavelength=0.45`、`MaxWavelength=0.65`，其余同角度项（`HologramObject…InsideOfObject` 为 −1 默认，`IsValid=true`，`Field/Wavelength/Surface=1`）；`evaluation_conditions.surface_type='Hologram1'` | 回读完整 | 未断言 Min/MaxWavelength/SampleSize 与请求相等 |
| 结果（曲线） | 任务 `3c8de77dd88c4ba8b71c636623ad15a1`（S）、`16915c77f99d452880bd4049fcb20ebd`（P）：series 0，64 点，x=0.45…0.6468750000000001（步长 0.003125，S_65 不含上界），单值列，`labels_source='native'` | 曲线有效 | 未断言步长/上界不含 |
| 数值 / 参考 | checks.json：`S/P diff_efficiency_chromatic angle=26.56505117707799 wave=<λ>` 各 64 条，共 128 条全部 passed；全套最大绝对差 5.385047963102352e-11 | 与独立 Kogelnik 参考一致 | 覆盖 64 点/偏振 |
| 单位 | series `x_unit='micrometers'`、`y_unit='dimensionless'`、`value_quantity='diffraction efficiency'` | 波长 µm、效率无量纲 | 未断言 `x_unit='micrometers'` |
| 分页 | `get_task_result(series=0,start=1,count=3)` 调用成功 | 分页可用 | 未与全量比对 |
| 图像 | `S/P_diff_efficiency_chromatic.png` | 两偏振各一张 | 未校验文件 |
| 恢复 / 重载 | 同角度项：`offaxis_saved.zos` 重开，曲面与 configuration/fields/wavelengths/polarization 相等 | 重载保持 | — |
| 任务失败 | ObjectHeight 失败用例使用角度 kind，未单独覆盖波长 kind | 失败机制在同类原生设置上成立 | 若审查要求逐 kind 失败证据，可在最小原生命中追加一次（非必需） |
| 取消 | 同会话 2048×2048 `diff_efficiency_2d` 取消 | 取消机制成立 | 波长扫描本身未单独取消（三项共用证据） |
| 关闭 | 每任务 `close_attempted=true`；close_receipt `native.closed=true, forced=false`；`disconnect` 正常 | 关闭齐备 | — |

## 缺口（断言层面）

1. `MinWavelength/MaxWavelength/SampleSize` 回读断言；2. `x_unit='micrometers'` 与 `labels_source='native'`；3. 64 点、步长 0.003125、末尾 0.646875 < `max_wavelength`；4. 扫描轴与系统波长（0.55 µm）分离的显式断言；5. 分页子块等值；6. 复用 Hologram1 模型参数回读断言（与角度项共用）。

## 判定

数值（128 点 S/P）、单位、重载、关闭证据齐备且与当前源码输出结构一致 → **implemented；补断言后转 done**。DLL 波长证据（576 检查中 192 项 P 物理参考失败）仅作历史，不进入当前结论。

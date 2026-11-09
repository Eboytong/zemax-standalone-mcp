# CO-01.DiffEfficiencyAngular：原生 Hologram1 证据矩阵（阶段一）

- 声明范围：原生 Hologram1 体全息（Par13=1）角度扫描，S/P 双偏振，Bragg±6.4°（20.16505117707799–32.96505117707799°），效率为无量纲比例。依据 `development/tracking/scope.json`（排除 `CO-01.KogelnikDLL.PProjection`）与 `development-groups.json` D010。
- 证据运行：`C:\Users\tonge\Desktop\Zemax_MCP\.local\runs\runs\diff_efficiency_offaxis059_native_bdfaeee137`（会话 `d5946d8262334d3cb2ff2ca6358a2622`；OpticStudio 24.2.0 build 240529 PremiumEdition；sequential；lens units mm）。
- 独立参考：`tests/support/kogelnik.py::unslanted_transmission`；容差 `atol=1e-6, rtol=1e-5`（沿用原条目，未改）。

| 维度 | 既有证据（文件 / 定位） | 结论 | 缺口 / 复测条件 |
| --- | --- | --- | --- |
| 当前声明 | `scope.json` 原生声明；`development-groups.json` D010 item 1 | 当前仅以原生 Hologram1 评定；DLL 记录转历史 | 无 |
| 输入身份 | calls.json：`open_lens` 样例 `…\Samples\Sequential\Diffractive components\Transmission hologram.zos`；`update_system_settings` field_type=Angle, fields[(0, 26.56505117707799)]；wavelengths[(1, 0.55 µm)]；`update_surfaces` surface=1 surface_type=Hologram1 厚度 100 mm、Par1-8 与 Par13-21 | 记录/重建几何、级次、乳胶参数齐全 | 用例未把 Par1-8/13-21 回读与写入值断言比对（回读见任务 json 的 cells） |
| 设置写入 | `configure_diff_efficiency` → `SampleSize`、`MinAngle`、`MaxAngle`（其余 None 字段不写） | 只写请求字段，未覆盖原生默认 | — |
| 设置回读 | 任务 json `task.settings.native`：`SampleSize='S_65'`、`MinAngle=20.16505117707799`、`MaxAngle=32.96505117707799`、`HologramObject/AmbientObject/DetectorObject=-1`、`srcPositionX/Y/Z=-1.0`、`srcUnpolarized=false`、`srcXTitled=true`、`srcPolJx/Jy=-1.0`、`srcPrePropagation=-1.0`、`InsideOfObject=-1`、`IsValid=true`、`IsActiveWindow=true`、`Field=1`、`Wavelength=1`、`Surface=1`；`evaluation_conditions={surface_type:'Hologram1', material:''}` | 回读完整，含实际曲面类型 | 测试断言只校验 `surface_type`，未断言 MinAngle/MaxAngle/SampleSize 与请求相等 |
| 结果（曲线） | 任务 `c984787ec273403597bc4e84e1133cff`（S）、`5fc28006ec8043a1896a7cde92629462`（P）：series 0，64 点，x 20.16505117707799…32.76505117707799 递增（S_65 不含上界），单值列，`labels_source='native'`（原生标签「衍射效率」） | 曲线有效、点数与采样一致 | 未断言上界不含、未断言 labels 来源 |
| 数值 / 参考 | checks.json：`S/P diff_efficiency_angular angle=<x> wave=0.55` 各 64 条，共 128 条全部 passed；全套 384 条最大绝对差 5.385047963102352e-11 | 与独立 Kogelnik 参考一致（远优于容差） | 无非 Hologram1 混入；覆盖为 64 点/偏振 |
| 单位 | series `x_unit='degrees'`、`y_unit='dimensionless'`、`value_quantity='diffraction efficiency'`（analyses.py 标注） | 结果轴与量纲明确 | 用例只断言 `y_unit`，未断言 `x_unit='degrees'` |
| 分页 | `get_task_result(series=0,start=1,count=3)` 调用成功（calls.json） | 分页可用 | 未与全量结果子块比对数值 |
| 图像 | `S_diff_efficiency_angular.png`、`P_diff_efficiency_angular.png`（`export_analysis_image`） | 两偏振各一张 | 未校验文件存在性/尺寸 |
| 恢复 / 重载 | `save_lens_as offaxis_saved.zos` → `open_lens`；`get_surfaces` 与 `get_system_settings`（configuration/fields/wavelengths/polarization）前后相等 | 重载后模型与设置保持 | — |
| 任务失败 | ObjectHeight 视场下 `diff_efficiency_angular` → `failed`，`close_attempted=true`，`error.code ∈ {NO_RESULT_DATA, ANALYSIS_FAILED}`；恢复 Angle 后同会话再次成功 | 失败路径与复用成立 | 该失败用例的原始请求为角度 kind，可直接引用 |
| 取消 | 同一原生会话中 2048×2048 `diff_efficiency_2d` 运行中取消 → `cancelled`、`close_attempted=true`（`cancellation.json`） | 取消机制成立 | 角度扫描本身未单独取消；取消证据为三项共用，须如实标注 |
| 关闭 | 每任务 `close_attempted=true`；`state/close_receipt.json`：`native.attempted=true, closed=true, forced=false`；`disconnect` 正常 | 任务/实例/session 关闭齐备 | — |
| 证据汇总 | `reference_status.json`：`{surface_model:'native', physical_reference_passed:true, physical_reference_failures:0, maximum_physical_error:0}` | 原生 S/P 参考通过 | — |

## 缺口（仅断言层面，不改数值口径）

1. 断言 `SampleSize/MinAngle/MaxAngle` 回读等于请求；2. 断言 `x_unit='degrees'`、`value_quantity` 与 `labels_source='native'`；3. 断言 64 点、递增、末尾 < `max_angle`；4. 断言 Hologram1 Par1-8/13-21（厚度 0.01 mm、n1=n2=1、n=1.5、dn=0.02、收缩/漂移 0、Fresnel 0、级次 m=1、λc=0.55）与写入一致；5. 分页子块与全量对应项比对；6. 记录原生前导把角度标签写成「最大角度=20.17，最小角度=32.97」的表述差异，判定以 settings 回读与递增轴为准。

## 判定

数值、单位、生命周期、关闭均已具备，且证据字段与当前源码（0.1.62，HEAD `34e1a18`）的 `analyses.py` 输出结构一致 → **判定 implemented，可在补入上述 6 项断言后转为 done**；既有 384 项数值证据可复用，不重跑 DLL 路径。

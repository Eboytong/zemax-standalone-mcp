# D003 / D004 最终离线审计报告（12 项）

日期：2026-11-08。性质：**离线审计（源码 + 正式接口 + 历史证据 + 普通检查）**。原生启动统一延后（`application_create` 三次 180 s 超时），本轮不执行原生、不关闭条目、不改台账。D011 Unload 已完成实际实现（另见 `pass-d011-report.md`）。

> **CV-01.FftSurfaceMtf 的留存数据单因素实验已交由 `zemax-p01-hologram` 并行执行**；本报告只记录该条目的离线审计与索引，不重复其实验，最终引用其报告。

## 1. 实际运行的检查

1. `python -B -m pytest tests/unit/test_power_maps.py tests/unit/test_power_probe_contracts.py tests/unit/test_pickup_probe_contracts.py tests/unit/test_modeling.py tests/unit/test_extended_solves.py tests/unit/test_solve_support.py tests/unit/test_seidel_diagram.py tests/unit/test_full_field_spot.py tests/unit/test_configuration_matrix_spot.py tests/unit/test_fft_surface_mtf.py tests/unit/test_conversion.py -q`
   → **235 passed in 1.69s**。
2. pickup + power 探针合同测试（上一回合真实回执）：`test_pickup_probe_contracts.py + test_power_probe_contracts.py` → **26 passed**。
3. `ED-02.SolveExtensions018` 聚合范围表：`python -B .local/coordination/solve_extensions018_scope.py` → 输出 `.local/coordination/solve-extensions018-scope.json`（27 个 solve；15 有单元测试引用；6 未在 solve-extensions.md 显式出现）。
4. typed 请求 + dispatch 存在性：`analysis_models.py`/`analyses.py` 中 `seidel_diagram/full_field_spot/matrix_spot/configuration_matrix_spot/fft_surface_mtf` 均命中；`power_field_map/power_pupil_map` 在 `analyses.py` 命中。
5. `d003-interface-check.py` 反射成员核对：5/5 命中，exit 0（上回合）。

## 2. 逐项审计（D003 5 项）

| 条目 | 正式接口 / 适配器 | 实际检查 | 状态 / 阻塞 |
| --- | --- | --- | --- |
| `ED-02.SurfacePickup.ChipZone` | `ILDERow.ChipZoneCell`→CreateSolveType/SetSolveData；`ISolveSurfacePickup`；`backend._surface_data` | pickup 探针 5 测试（含于 26 passed）；`d003-interface-check` 5/5 | blocked：原生 setter Success 但回退 `Automatic`。解除：四时刻三路回读=SurfacePickup + 参数 + 联动 + 保存重载 + 关闭 |
| `ED-02.SurfacePickup.MechanicalSemiDiameter` | `ILDERow.MechanicalSemiDiameterCell` | 同上；失败写入把目标值 5.2→5.0（成因未定，记录） | blocked：原生不采用且失败路径改写数值。解除：同 ChipZone + 无残留改写 |
| `ED-02.SolveExtensions018` | `SOLVES/SOLVE_FIELDS/SOLVE_ALIASES`（modeling.py:14-29） | **聚合表已生成**：27 solve / 15 有单测引用 / 6 未在文档显式列出；12 无直接单测引用 | 聚合项：依赖 MaterialModel + 两 SurfacePickup。解除：前置收口且表与台账口径一致 |
| `NS-01.Conversion` | `conversion.py`/`conversion_models.py` | `test_conversion.py` 通过（含于 235 passed） | implemented：纯 NSC 已验收；混合组 dummy/关闭光阑 `TASK_START_FAILED`。解除：混合组原生设置/光线/保存重载/取消通过 |
| `ED-04.RayAimingWizard` | design tool `RayAimingWizard`（models/backend） | 无专门离线单测（原生依赖）；证据 `ED-04/ray-aiming276/probe.json`：RunAndWaitWithTimeout(10) TimedOut、Cancel 后仍 IsRunning、Close=false | blocked：工具不可完成/不可取消。解除：可靠完成/取消/关闭路径或修复版本，再验预览/Apply/保存重载/模型保持 |

## 3. 逐项审计（D004 7 项）

| 条目 | 正式接口 / 适配器 | 实际检查 | 状态 / 阻塞 |
| --- | --- | --- | --- |
| `CV-02.PowerFieldMapSettings` | `run_analysis power_field_map`（POWF）；`_page_task_result` 分页 | `test_power_maps.py` + `test_power_probe_contracts.py`（含于 235/26） | implemented：raw zero/offset/分页/模型保持通过；零 EFL 语义与环状态未定义。解除：E2/E3 原生可区分证据 |
| `CV-02.PowerPupilMapSettings` | `run_analysis power_pupil_map`（POWP） | 同上（共用验收） | implemented：同 Field Map |
| `CV-01.SeidelDiagram` | `run_analysis seidel_diagram`；`IAS_SeidelDiagram` | `test_seidel_diagram.py` 通过；typed+dispatch 存在 | blocked：`EXPORT_FAILED`，无图形/数值结果出口；独立 `SeidelCoefficients` S1 参考 1e-6 通过但不含图。解除：正式结果出口或经验证等价实现 |
| `CV-01.FullFieldSpot` | `run_analysis full_field_spot`；`AS_Spot` | `test_full_field_spot.py` 通过 | implemented：设置采用；三配置 `RESULT_UNAVAILABLE`、`SpotData` 空。解除：有效结果出口或验证参考点/放大/布局映射 |
| `CV-01.MatrixSpot` | `run_analysis matrix_spot` | `test_configuration_matrix_spot.py` 覆盖 matrix/configuration；typed+dispatch 存在 | implemented：计算完成但 `SpotData` 空、`EXPORT_FAILED`。解除：正式出口或等价计算 |
| `CV-01.ConfigurationMatrixSpot` | `run_analysis configuration_matrix_spot`；11 可写设置 | `test_configuration_matrix_spot.py` 通过 | implemented：双配置原生 1 项通过；无 `SpotData`/文本。解除：同 MatrixSpot |
| `CV-01.FftSurfaceMtf` | `run_analysis fft_surface_mtf`；6 可写设置 | `test_fft_surface_mtf.py` 通过；**留存数据单因素实验由 hologram worker 执行** | implemented：复瞳自相关 field1 6.66e-16、field3 0.0049502（<0.005）；离轴映射超限。阈值固定 0.005。解除：离轴映射入门槛或记录为限制 |

## 4. 审计发现

- **D003-1**：`ED-02.SolveExtensions018` 聚合范围为 27 个 solve（15 有单测引用、12 无直接单测引用、6 未在 `solve-extensions.md` 显式出现）。表见 `solve-extensions018-scope.json`。此为台账“已实现待验收”的量化补齐，不改产品。
- **D003-2**：机械半口径失败写入残留数值改写（5.2→5.0）仍无成因，仅事实记录。
- **D004-1**：CV-01 五项的“结果出口缺失/EXPORT_FAILED”均来自既有原生证据，本轮仅复核 typed/dispatch 与单测；未新增原生。
- **D004-2**：`power-maps-review3-report.md`、`d003-pickup-implementation-report.md` 已记录零 EFL/环状态与 SurfacePickup 反射限制。

## 5. 外部阻塞与解除条件（汇总）

1. **SurfacePickup（ChipZone/MechanicalSemiDiameter）**：原生返回 Success 但模式回退；解除=正式可采用且可持久化路径。
2. **RayAimingWizard**：原生向导不完成/不取消；解除=可靠完成/取消/关闭路径或修复版本。
3. **SeidelDiagram**：无图形/数值结果出口；解除=正式出口或经验证等价实现。
4. **FullField/Matrix/ConfigurationMatrix Spot**：结果出口缺失/`EXPORT_FAILED`；解除=有效原生出口或经验证替代路径。
5. **FftSurfaceMtf**：离轴坐标/幅度/瞳支持映射超门槛（0.005 保持）；由 hologram worker 留存数据单因素实验判定。
6. **NS-01.Conversion**：混合组原生转换失败；解除=混合组完整原生验收。

## 6. 结论与界限

- 12 项完成离线审计与普通检查（235 passed）；**无一项本轮可关闭**；`SolveExtensions018` 由“待离线”升级为“已审计（附聚合表）”。
- 未启动原生、未改 `src/`（本任务仅 D011 unload 在工作区改动）、未改台账/批次/tracking、未提交 Git。
- 交付：本报告 + `pass-d003-d004-plan.md` + `pass-d003-d004-items.json` + `solve-extensions018-scope.json`。

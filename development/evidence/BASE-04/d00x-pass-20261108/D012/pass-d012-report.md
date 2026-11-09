# D012 实施与审计报告：STAR 组件、坐标与性能分析（14 项）

- 组：D012；权威清单 `development/tracking/d00x-pass-20261108.json`（`development_group=="D012"`，14 项）
- 本轮：实际审计 + 可执行开发 + 审查后修正；原生新启动延后；未改公共台账；未提交 Git
- 只读资料：`verification/development/BASE-01/probe/api-interfaces.json`、`development/evidence/CV-01/star-analysis-readiness-20261108.md`、`development/evidence/EXT-STAR/{components,coordinate-transform,control-evidence-reconciliation}-20261108.md`、`verification/development/EXT-STAR/readiness193.json`

## 1. 六个 STAR 专题的准确结论

| 事实 | 值 |
| --- | --- |
| `AnalysisIDM.STARAlignCheck` / `STARSysViewer` / `STAR2DDefPlot` | 155 / 156 / 157 |
| `AnalysisIDM.STARPerfChange` / `STARIndexVsTemp` / `STARInspectFEA` | 158 / 159 / 160 |
| 对应 `IAS_` 设置接口 | 转储中**没有** |

枚举给出通用 `CreateNewAnalysis` 的候选标识；实际创建及设置/结果面需原生执行确认。转储缺少 `IAS_` 只说明设置接口未文档化，既不证明也不否定正式设置出口。本轮据此实现：创建走通用工厂，设置面**运行时探测并原样记录**，结果出口**运行时探查**。

## 2. 模块可用性：历史 vs 实时

- `IsSTARModuleEnabled=false` 是 **2026-11-06** 的采集结果（readiness193），属历史状态。
- 代码**每次执行实时读取** `IZOSAPI_Application.IsSTARModuleEnabled`，结果与错误详情都带 `availability={enabled, source}`。
- 未启用时在**任何原生写入之前**返回 `FEATURE_UNAVAILABLE`，并显式说明这是模块许可前置而非缺工厂。

## 3. 审查修正（本轮重做）

| 审查意见 | 修正 |
| --- | --- |
| `star_payload` 用 `bool(artifacts)` 判结构数据 | 删除。`structured_data_available` 只由 **series / grids / scatter（散点集合）** 决定；BOM-only、仅标题、错误报告永不计为有效结果 |
| 走 `_collect_general_analysis` 会先 `EXPORT_FAILED`，丢掉已有网格/曲线 | 改为 **STAR 独立收集器** `collect_star_results`：文本导出结果单独记录（`text_export={attempted,exported,path,error,line_count,non_blank_lines}`），与 series/grids/scatter/native_messages 并行采集；不触碰通用消费者 |
| `unavailable_fields` 未拒绝 | 现在显式拒绝并**先关闭原生**（`SETTING_UNAVAILABLE` + `unavailable_fields`），关闭失败补 `cleanup_warnings` |
| `GetSettings` 调用两次 | 只取一次，设置面探测与回读共用同一对象（测试断言调用次数为 1） |
| `kind=star_analysis`+`analysis` 会让能力发现漏报 | **改为六个具体 kind** 分别注册到 `ANALYSES` 原生枚举并纳入请求联合体：`star_align_check`→`STARAlignCheck`、`star_sys_viewer`→`STARSysViewer`、`star_2d_def_plot`→`STAR2DDefPlot`、`star_perf_change`→`STARPerfChange`、`star_index_vs_temp`→`STARIndexVsTemp`、`star_inspect_fea`→`STARInspectFEA` |
| 旧的行上限硬截断 | 删除截断；`grid_values` 用 `Values`（`Double[,]`）或 `ValueData`（`Rows/Cols/GetValueAt`）读完整 `Ny×Nx`，取不全 → `INVALID_RESULT_DATA` |
| 散点读取需核对集合和数量 | 优先 `Points`（`IAR_ScatterPoint[]`），回退 `GetPoint(Int32)`；数量与 `NumPoints` 不符 → `INVALID_RESULT_DATA` |
| 消息严重性缺少枚举来源 | 按 `ErrorType` 14 值分类，仅 `Success` 非失败，其余 13 个为具体失败码 |
| 致命消息附带部分数据仍可能返回成功 | 有致命消息即 `ANALYSIS_FAILED`，数据放入 `details.partial_result` |
| 空 X/零列曲线、`NumPoints=0` 散点块被计为有效 | 不计入结构数据，记入 `empty_collections`；仅剩空集合时返回 `NO_RESULT_DATA` |
| 散点输出结构不与共享 `scatter`/`rows` 合同一致 | 统一为 `scatter`（仅有限点）+ `rows`（含非法行）；不再有独立散点键，避免同一大数组重复到另一个键 |
| 目录匹配未采用原生精确名 | `catalog_diagnostics` 返回 `matched_name`；`set_scattering` 用其替换 `file_name` 后再 `SetFile`，避免回读大小写冲突 |

## 4. 代码改动

| 文件 | 改动 | 性质 |
| --- | --- | --- |
| `src/zemax_mcp/star_analyses.py`（新，重写） | 六个 kind-only 请求模型；`STAR_REQUESTS`；`star_module_enabled`（实时）；`settings_surface`；`native_messages`/`fatal_messages`/`native_header`；`text_export`；`native_series`/`native_grids`（完整 Values/ValueData）/`native_scatter`（rows + 有限点 scatter）；`collect_star_results`；`run_star_analysis` | 新增 |
| `src/zemax_mcp/plotting.py` | `export_image` 的散点图项按 `points` 非空过滤（空散点块不生成图，返回 `NO_PLOTTABLE_DATA`） | 共享补丁 |
| `src/zemax_mcp/analyses.py` | 六个 kind 注册到 `ANALYSES`（能力发现可见）+ 分派分支 | 共享补丁 |
| `src/zemax_mcp/analysis_models.py` | 六个类导入并纳入 `AnalysisRequest` 联合体 | 共享补丁 |
| `tests/support/analysis_scenarios.py` | 六个 STAR kind 归入 SPECIALIZED（需启用模块与受控 FEA） | 修正 |
| `tests/unit/test_star_analyses.py`（重写，43 项） | 注册/契约、实时可用性、通用创建、关闭路径、独立收集、完整网格、rows/scatter 合同、错误分层、真实 Backend 分页与 export_image | 新增 |
| `tests/native/test_star_analysis_live.py` | 六 kind 原生作业（仅准备） | 新增 |

### 收集器语义（与既有约定一致）

**原生成员来源表（全部取自 `verification/development/BASE-01/probe/api-interfaces.json`，非臆造）**

| 用途 | 原生成员 | 转储类型 |
| --- | --- | --- |
| 网格完整数值 | `IAR_DataGrid.Values` | `System.Double[,]` |
| 网格回退读取 | `IAR_DataGrid.ValueData`（`Rows`/`Cols`/`Data`/`GetValueAt`/`ReadData`） | `ZOSAPI.Common.IMatrixData` |
| 网格轴 | `Nx`/`Ny`/`Dx`/`Dy`/`MinX`/`MinY`/`Description`/`XLabel`/`YLabel`/`ValueLabel` | `UInt32`/`Double`/`String` |
| 曲线 | `IAR_DataSeries.XData.YData`/`SeriesLabels`/`NumSeries`/`Description`/`XLabel` | `IMatrixData`/`String[]` |
| 散点集合 | `IAR_DataScatterPoints.NumPoints`/`Points`/`GetPoint(Int32)` | `UInt32`/`IAR_ScatterPoint[]`/方法 |
| 散点元素 | `IAR_ScatterPoint.X`/`Y`/`Value` | `Double` |
| 消息 | `IMessage.ErrorCode`/`Text` | `ZOSAPI.Analysis.ErrorType`/`String` |
| 文本导出 | `GetTextFile(String)`；`HeaderData.Lines` | 方法；`String[]` |

- **文本导出**：`GetTextFile` 返回 false 不再是致命错误，记录 `text_export.error='GetTextFile returned false'`；成功时记录 UTF-16 行数与非空行数，但文本是否存在不影响结构数据判定。
- **曲线**：`XData/YData` 缺失 → `NO_RESULT_DATA`；长度不一致、横轴含非有限值 → `INVALID_RESULT_DATA`；非有限列值置 `None` 并计 `invalid_count`；`SeriesLabels` 为空时生成列索引并标注来源。**空 X 或零列曲线不计有效结构结果**（记入 `empty_collections`）。
- **网格**：**读取完整 `Ny×Nx`，绝不截断**。优先 `Values`（`Double[,]`），否则用 `ValueData` 的 `Rows`/`Cols`/`GetValueAt` 逐行取全区；尺寸与 `Nx`/`Ny` 不符或两者皆缺 → `INVALID_RESULT_DATA`。分辨率差异（`Dx≠Dy`）与非方形网格由 `_page_task_result` 的区域分页支持（`x_start/y_start/width/height`）。
- **散点**：按 `imaging.collect_scatter` 既有格式——`rows` 扁平化保存每个点的 `block/point/x/y/value/valid`（非法坐标留 `None` 与 `valid=False`，计入 `invalid_count`）；`scatter=[{scatter,native_scatter,description,x_label,y_label,value_label,count,points,invalid_count,points_source}]`，其中 `points` **只含有限有效点**供绘图。不再设置独立散点键，避免同一大数组重复到另一个键；默认分页走 `rows` 现有链路，`_page_task_result` 会把 `scatter[*].points` 剥离为 `point_count` 并置 `scatter_data_in_artifacts=True`。`NumPoints=0` 的散点块不计有效结构结果。
- **消息严重性**：`ErrorType` 共 14 个值，仅 `Success` 为非失败；其余 13 个（`InvalidParameter`/`InvalidSettings`/`Failed`/`AnalysisUnavailableForProgramMode`/`NotYetImplemented`/`NoSolverLicenseAvailable`/`ToolAlreadyOpen`/`SequentialOnly`/`NonSequentialOnly`/`SingleNSCRayTraceSupported`/`HPCNotAvailable`/`FeatureNotSupported`/`NotAvailableInLegacy`）均归为致命失败码。
- **致命消息优先**：即使附带了部分结构数据，只要有致命消息就 **`ANALYSIS_FAILED`**，并把已收集数据放入 `details.partial_result`，绝不返回成功。
- **无结构数据时**：无致命消息 → `NO_RESULT_DATA`（导出但为空/仅标题、空曲线、空散点块都不算结果）。

### 共享合同测试（真实 Backend 与 plotting，非 fake collector）

`tests/unit/test_star_analyses.py` 用真实 `Backend._page_task_result` 与真实 `plotting.export_image` 驱动采集器产物：

- `test_backend_pages_scatter_rows_and_hides_points`：散点 `points` 被剥离（`point_count`、`scatter_data_in_artifacts=True`），`rows` 分页（`start/count` → `total/next_start`）。
- `test_backend_reads_a_non_square_grid_region`：`ny=3,nx=5` 网格按 `x_start/y_start/width/height` 取非方形区域，返回 `values` 与 `next_x/next_y`。
- `test_export_image_draws_scatter_with_only_finite_points`：散点 PNG 只取有限点；全非法点块 → `NO_PLOTTABLE_DATA`（`plotting.export_image` 现按 `points` 非空过滤散点图项）。

### STAR 本轮专项确认（对应审查清单）

| 确认项 | 结论 | 测试 |
| --- | --- | --- |
| native_scatter 解包 | 优先 `Points`(`IAR_ScatterPoint[]`)，回退 `GetPoint(Int32)`；数量≠`NumPoints` → `INVALID_RESULT_DATA` | `test_scatter_uses_the_official_collection`、`test_scatter_falls_back_to_get_point_and_rejects_count_mismatch` |
| rows 分页 | `_page_task_result` 按 `rows` 分页，`scatter[*].points` 剥离为 `point_count` | `test_backend_pages_scatter_rows_and_hides_points` |
| 非方形 grid 区域 | `ny=3,nx=5` 区域读取 + `next_x/next_y` | `test_backend_reads_a_non_square_grid_region` |
| scatter PNG | 仅有限点入库绘图 | `test_export_image_draws_scatter_with_only_finite_points` |
| 全无效点状态 | 采集保留非法行（`valid=False`、`invalid_count`），图像阶段无可用点 → `NO_PLOTTABLE_DATA` | `test_scatter_non_finite_values_stay_in_rows_but_not_in_points` + 上述 PNG 用例 |
| 完整 Ny×Nx | 5×4 全量、无截断键；`ValueData` 回退；缺值/尺寸不符 → `INVALID_RESULT_DATA` | `test_grids_keep_the_complete_ny_by_nx_values`、`test_grid_values_fall_back_to_the_value_data_matrix`、`test_grid_without_any_values_is_invalid`、`test_grid_value_data_size_mismatch_is_invalid`、`test_grid_shape_mismatch_is_invalid` |

### `plotting.export_image` 通用过滤：消费者需求与受影响定向测试

- 改动：构造绘图项时散点仅纳入 `points` 非空的项（`[("scatter",s) ... if s.get("points")]`）。
- 实际消费者需求：`export_image` 由 `src/zemax_mcp/exports.py`（导出图片工具）与 `src/zemax_mcp/image_worker.py`（后台绘图 worker）调用；`src/zemax_mcp/reports.py` 用同一 `scatter[*].points` 形状生成散点 PNG。STAR/成像的散点块可能出现“有块但无有限点”（全部坐标非法）；若不过滤，会画出空坐标轴并返回成功，掩盖“无可绘点”。过滤后空散点块不进入候选，最终返回 `NO_PLOTTABLE_DATA`，与“图像仅取适用有限点”一致。
- 受影响定向测试（均离线通过）：`tests/unit/test_plotting_units.py`（series/grid 绘图与等轴）、`tests/unit/test_imaging.py`（成像 grid 导出）、`tests/unit/test_scatter_report.py`（散点报告 PNG）、`tests/unit/test_star_analyses.py`（STAR 散点 PNG 与全无效点）。

## 5. 逐项状态（14 项）

### A 类：控制项（7 项）— blocked（许可 + 资源）

接口齐备（`ISTAR_ComponentRBMs`、`ISTAR_CoordinateTransform`、`ISTAR_RBMs`、`ISTAR_RBM_ReferencePoint`/`Centroid`）；适配与检查已在 `star_controls.py`（成员清单、重叠、首面规则、重复操作、恢复、拓扑变化）。本轮回归确认 `test_star_controls.py`/`test_star.py`/`test_star_materials.py` 全通过。

| 项 | 已有实现 | 剩余 | 解除条件 |
| --- | --- | --- | --- |
| `EXT-STAR.Components.define` | `StarDefineComponent`+像面/重叠检查+成员回读 | 原生采用、保存/重载 | STAR 启用 + 受控模型 |
| `.configure` | `component_rbm(configure)`+`AdjustIndexDataWithComponentRBM` 回读 | 同上 | 同上 |
| `.coordinate_breaks` | `AddComponentRBMsAsCoordinateBreaks`+拓扑确认 | 同上 | 同上 |
| `EXT-STAR.CoordinateTransform` | `StarCoordinateTransform`+`coordinate_state` | 角度顺序语义、原生回读 | 同上 + 角度顺序确认 |
| `EXT-STAR.RigidBody` | `StarRigidBody`+`rigid_body_state`+未导入前置 | 原生采用 | 同上 |
| `.remove_rbms` | `remove_from_fea`+已移除拒绝 | 幂等性与原生状态 | 同上 |
| `.remove` | `StarRemoveComponent`+首面规则+清单为空 | 原生采用 | 同上 |

### B 类：专题分析（6 项）— blocked（许可 + 资源）

六个 kind 均已：注册到能力发现、可用性实时门、通用工厂创建、设置面探测、独立结果采集（曲线/网格/散点/文本导出分别记录）。**剩余**：启用后现场确认设置面与结果出口（`STARSysViewer` 另需图像出口）。

### C 类：组项 `EXT-STAR.Components`

A 类四项聚合，`_composite('star_operation')` 与清单不变量已在 `star_controls.py`，本轮未改。

## 6. 实际执行的命令与回执（本轮定向，无全量、无原生）

```
... -m pytest tests/unit/test_star_analyses.py tests/unit/test_analysis_scenarios.py \
    tests/unit/test_scatter_capabilities.py tests/unit/test_plotting_units.py \
    tests/unit/test_imaging.py tests/unit/test_scatter_report.py \
    tests/unit/test_property_pages_adoption.py -q -p no:cacheprovider
→ 225 passed in 1.91s
```

准确回执文件：`.local/coordination/pass-d012-star-targeted.xml`（JUnit，`tests=225 failures=0 errors=0 skipped=0`，含重命名后的 `test_scatter_uses_the_official_collection`）。定向文件名为实查确认存在：`test_plotting_units.py`、`test_imaging.py`、`test_scatter_report.py`。

针对本轮审查三点的专项断言（均在 `test_star_analyses.py`）：

1. 全部失败码：`test_every_non_success_error_type_is_fatal` — 转储 `ErrorType` 的 13 个非 `Success` 值逐一为致命，`Success` 非致命。
2. 致命+部分数据：`test_fatal_message_with_structured_data_is_not_success` — 有网格+`HPCNotAvailable` 时返回 `ANALYSIS_FAILED` 且 `details.partial_result` 保留网格。
3. 空集合：`test_empty_series_is_not_a_structured_result`、`test_zero_column_series_is_not_a_structured_result`、`test_zero_point_scatter_block_is_not_a_structured_result`、`test_empty_collection_does_not_mask_a_valid_one`。
4. 官方成员：`test_collection_members_match_the_dump`、`test_message_severity_uses_the_official_enum`。
5. 网格完整：`test_grids_keep_the_complete_ny_by_nx_values`（5×4 全量、无 `truncated`/`row_limit` 键）、`test_grid_values_fall_back_to_the_value_data_matrix`、`test_grid_without_any_values_is_invalid`、`test_grid_value_data_size_mismatch_is_invalid`、`test_grid_shape_mismatch_is_invalid`。
6. 散点：`test_scatter_uses_the_official_collection`、`test_scatter_falls_back_to_get_point_and_rejects_count_mismatch`、`test_scatter_non_finite_values_stay_in_rows_but_not_in_points`。
7. 共享合同（真实 Backend/plotting）：`test_backend_pages_scatter_rows_and_hides_points`、`test_backend_reads_a_non_square_grid_region`、`test_export_image_draws_scatter_with_only_finite_points`。
8. 不依赖通用收集器：`test_collection_does_not_depend_on_the_generic_collector`（通用收集器被调用即失败）。

取消/关闭：`test_settings_readback_failure_closes_without_losing_the_original_error` 覆盖关闭失败时仍保留原始错误与 `cleanup_warnings`；任务级取消沿用既有 `_start_task(analysis=True)` 生命周期（`native.Terminate()`），未新增代码路径。

## 7. 剩余范围与解除条件

| 项 | 剩余 | 类型 | 解除条件 |
| --- | --- | --- | --- |
| A 类 7 项 | 原生采用/数值/保存重载/恢复 | 许可 + 资源 | STAR 模块启用 + 受控 FEA/顺序模型 |
| B 类 6 项 | 设置面与结果出口现场验证 | 许可 + 资源 | 同上并确认出口 |
| CoordinateTransform | 旋转角顺序语义 | 接口语义 | 启用后实测 `RotationAngles` vs `RotationValues` |

## 8. 风险

- 全部 STAR 原生证据仍为 **2026-11-06 历史**；本轮未新增原生执行。
- `settings_surface` 只是当前对象公开成员快照，不等同于"官方支持的设置项"。
- 转储缺失 `IAS_` 可能是反射不完整；只记录"未文档化"，不下"不存在"结论。
- 网格一律读取完整 `Ny×Nx`（`Values` 或 `ValueData`），不再有行上限截断；超大网格由 `_page_task_result` 的区域分页按 `x_start/y_start/width/height` 取用，无需在采集阶段裁剪。
- 六个新 kind 进入公共请求联合体与 `ANALYSES`，属共享补丁，需集成负责人审核后再合并。

协调者最终审查：本机IAR_DataGrid.Z(Int32,Int32)、GetDataScatterPoint与GetPoint均为正式成员；当前实现选择Values/ValueData与Points读取。主仓集成及421项检查见上级integration-star-analyses-scattering.md；原生准备测试以主仓后续修正版为准。

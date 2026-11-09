# D012 逐项计划：STAR 组件、坐标与性能分析（14 项）

- 开发组：**D012**（`development/current.md` D012 段；`development/tracking/d00x-pass-20261108.json` 中 `development_group=="D012"` 共 14 项）
- 权威来源：主项目 `C:/Users/tonge/Desktop/Zemax_MCP/development/`（本冻结工作区无 `tracking/d00x-pass-20261108.json`）
- 顺序按 pass 文件：`EXT-STAR.Components.define` → `.configure` → `.coordinate_breaks` → `EXT-STAR.CoordinateTransform` → `EXT-STAR.RigidBody` → `.remove_rbms` → `CV-01.STARInspectFEA` → `CV-01.STARAlignCheck` → `CV-01.STAR2DDefPlot` → `CV-01.STARIndexVsTemp` → `CV-01.STARPerfChange` → `CV-01.STARSysViewer` → `EXT-STAR.Components.remove` → `EXT-STAR.Components`
- 公共台账只读；本轮不启动原生；源码改动仅在本 worker 工作区

## 0. 本轮新增的静态事实（离线，依据 `verification/development/BASE-01/probe/api-interfaces.json`）

- `ZOSAPI.Analysis.AnalysisIDM` **确实包含**六个 STAR 专题：`STARAlignCheck`=155、`STARSysViewer`=156、`STAR2DDefPlot`=157、`STARPerfChange`=158、`STARIndexVsTemp`=159、`STARInspectFEA`=160。
- 因此**不能**把 CV-01 六项登记为"无分析工厂"；准确表述是"分析枚举存在，但静态接口转储中没有对应的 `IAS_` STAR 设置接口，且模块未启用"。
- STAR 控制接口齐备：`ISTAR_ComponentRBMs`（`SetSurfacesInComponent`/`RemoveComponent`/`RemoveComponentRBMsFromFEADataSets`/`AddComponentRBMsAsCoordinateBreaks`/`AdjustIndexDataWithComponentRBM`）、`ISTAR_CoordinateTransform`、`ISTAR_RBMs`、`ISTAR_RBM_ReferencePoint`、`ISTAR_Rotations`/`ISTAR_RotationValues`/`ISTAR_RotationAngles`、`ISTAR_FEAFitSettings`/`ISTAR_FEAFitResults` 等。
- 既有 typed 适配已确认：`src/zemax_mcp/star_models.py`（`StarDefineComponent`/`StarRemoveComponent`/`StarComponentRbm`/`StarRigidBody`/`StarCoordinateTransform`）、`src/zemax_mcp/star_controls.py`（`prepare_control`/`apply_control`/`run_control`，含成员、重叠、首面、重复操作与恢复检查）、`src/zemax_mcp/star.py`（读/拟合/导入）。
- 模块前置：`_require_star()` 在 `IsSTARModuleEnabled=false` 时于**写入前**返回 `FEATURE_UNAVAILABLE`，模型不变（证据 `development/evidence/EXT-STAR/readiness193.json`）。
- 既有普通测试可运行：`tests/unit/test_star.py`(10.1 KB)、`tests/unit/test_star_controls.py`(11.3 KB)、`tests/unit/test_star_materials.py`(3.5 KB)。

## 0.1 分类

- **A 类（控制项，7 条）**：`Components.define`/`.configure`/`.coordinate_breaks`/`.remove`/`.remove_rbms`、`CoordinateTransform`、`RigidBody`。接口与适配齐备，阻塞在模块许可 + 受控 FEA。
- **B 类（专题分析，6 条）**：`CV-01.*`。枚举存在（155–160），设置接口与结果出口未确认，模块未启用。
- **C 类（组项，1 条）**：`EXT-STAR.Components`（聚合 A 类四项的成员/RBM/坐标断点）。

## 1. EXT-STAR.Components.define（#113）

- 正式接口：`ISTAR_ComponentRBMs.SetSurfacesInComponent(first,last)`；成员读取 `FirstSurfaceInComponent`/`LastSurfaceInComponent`/`NumberOfSurfacesInComponent`/`IsPartOfAComponent`。
- 已有：`StarDefineComponent` typed 请求；写入前检查像面范围与既有组件重叠（`RELATION_PROTECTED`/`INDEX_OUT_OF_RANGE`）；写入后核对成员与首尾面；`component_inventory` 全清单对照。
- 可离线补齐：成员边界用例（单面组件、跨像面拒绝、与既有组件重叠拒绝、首面=1）；`SETTING_REJECTED` 时保留前后清单。
- 实际检查：`pytest tests/unit/test_star_controls.py -q` + 新增边界用例。
- 外部阻塞：`IsSTARModuleEnabled=false`，无受控 FEA/顺序模型副本。
- 解除条件：启用 STAR + 受控模型，验证成员、首尾面、保存/重载、失败恢复。

## 2. EXT-STAR.Components.configure（#111）

- 正式接口：`AdjustIndexDataWithComponentRBM` 属性（需显式 `adjust_index_data_with_rbm`），回读 `ComponentRBMIsAdjusted`。
- 已有：`component_rbm` `action='configure'` 要求显式布尔，缺失即拒绝；调用后回读。
- 可离线补齐：缺参拒绝、布尔双向回读、与 `.remove_rbms`/`.coordinate_breaks` 的状态互斥用例。
- 实际检查：`test_star_controls.py` + 新增互斥用例。
- 外部阻塞/解除条件：同 §1。

## 3. EXT-STAR.Components.coordinate_breaks（#112）

- 正式接口：`AddComponentRBMsAsCoordinateBreaks()`；回读 `CRBMsAreInCoordinateBreaks`、组件数、曲面数变化。
- 已有：`action='add_coordinate_breaks'` 适配 + 拓扑变化确认（组件数不变且曲面数增加）。
- 可离线补齐：拓扑未变（曲面数未增）时的 `SETTING_REJECTED` 用例；重复应用拒绝。
- 实际检查：`test_star_controls.py` + 新增拓扑用例。
- 外部阻塞/解除条件：同 §1。

## 4. EXT-STAR.CoordinateTransform

- 正式接口：`ISTAR_CoordinateTransform`（偏移/旋转写入与回读）；`star_controls.coordinate_state` 读取。
- 已有：`StarCoordinateTransform` typed 请求 + `coordinate_state` 回读对照。
- 可离线补齐：角度单位/顺序（`ISTAR_RotationAngles` vs `ISTAR_RotationValues`）映射用例；零偏移/纯旋转/纯平移三态；回读不一致拒绝。
- 实际检查：`test_star_controls.py` + 新增变换用例。
- 外部阻塞/解除条件：同 §1（另需确认角度顺序语义）。

## 5. EXT-STAR.RigidBody

- 正式接口：`ISTAR_RBMs` + `ISTAR_RBM_ReferencePoint` + `ISTAR_RBM_Centroid`；`FEAData.AreDeformationsImported` 前置。
- 已有：`StarRigidBody` typed 请求；`rigid_body_state` 回读；未导入形变时拒绝。
- 可离线补齐：参考点/质心二选一用例；未启用/未导入前置拒绝；移除后状态清零。
- 实际检查：`test_star_controls.py` + 新增参考点用例。`docs/star.md` 说明同步核对。
- 外部阻塞/解除条件：同 §1。

## 6. EXT-STAR.Components.remove_rbms（#115）

- 正式接口：`RemoveComponentRBMsFromFEADataSets()`；回读 `ComponentRBMsAreRemoved`。
- 已有：`action='remove_from_fea'`，调用前拒绝已移除状态，调用后回读。
- 可离线补齐：幂等性（重复移除拒绝）与移除后 `.configure` 拒绝的互斥用例。
- 实际检查：`test_star_controls.py` + 新增幂等用例。
- 外部阻塞/解除条件：同 §1。

## 7–12. CV-01 六项（STARInspectFEA / STARAlignCheck / STAR2DDefPlot / STARIndexVsTemp / STARPerfChange / STARSysViewer）

- 正式接口（本轮静态确认）：`AnalysisIDM` 枚举 160/155/157/159/158/156 **存在**；静态转储中**无** `IAS_` STAR 设置接口；结果出口未确认（`STARSysViewer` 亦无图像出口记录）。
- 已有：`development/evidence/CV-01/star-analysis-readiness-20261108.md`；`IsValidLicenseForAPI=true` 但 `IsSTARModuleEnabled=false`；无受控 FEA 输入；原生应用与分析对象关闭正常。
- 可离线补齐（每项同构）：① 枚举值与名称的静态一致性测试（防止版本漂移）；② 模块未启用时以 `FEATURE_UNAVAILABLE` 拒绝且不创建分析对象；③ 请求构造在无设置接口时不暴露虚假字段（沿用 kind-only 模式）。
- 实际检查：新增静态枚举/前置拒绝单元测试（合成对象，不连原生）。
- 外部阻塞：STAR 模块未启用 + 无受控 FEA 输入 + 设置/结果接口未确认（许可与资源，非代码）。
- 解除条件：启用 STAR 模块并提供受控 FEA 文件；逐个验证专题创建、设置采用、有效结果出口、关闭。
- **不登记**为"接口不存在"：仅记录"静态转储未提供设置接口，需启用后现场探查"。

## 13. EXT-STAR.Components.remove（#114）

- 正式接口：`RemoveComponent(firstSurface)`，请求必须用原生组件首面。
- 已有：`StarRemoveComponent` typed 请求；先读成员状态，非首面请求拒绝，调用后核对清单为空。
- 可离线补齐：非首面拒绝用例；移除后成员清单为空断言；移除不存在的组件拒绝。
- 实际检查：`test_star_controls.py` + 新增用例。
- 外部阻塞/解除条件：同 §1。

## 14. EXT-STAR.Components（组项）

- 正式接口：同上四项聚合（成员定义、索引数据调整、RBM 移除、坐标断点）。
- 已有：`component_inventory` 全清单；`_require_star()` 前置；关闭/断开沿用 readiness193。
- 可离线补齐：全清单不变量（组内成员两两不重叠、覆盖连续区间、像面前结束）作为独立断言；`_composite('star_operation')` 流程的中断/恢复用例。
- 实际检查：`test_star_controls.py` + `test_star.py` 回归 + 新增不变量用例。
- 外部阻塞/解除条件：同 §1。

## 15. 离线 / 原生划分

| 类别 | 可离线 | 需原生（或需许可） |
| --- | --- | --- |
| A 控制 7 项 | 边界/互斥/幂等/回读不一致用例、错误分层、模型不变断言 | 模块启用 + 受控 FEA：写入采用、数值、保存重载、恢复、关闭 |
| B 专题 6 项 | 枚举静态一致性、`FEATURE_UNAVAILABLE` 前置拒绝、kind-only 请求 | STAR 模块 + 受控 FEA + 设置/结果接口现场探查 |
| C 组项 | 成员不变量、复合流程恢复 | 同 A |

## 16. 完成条件（不降容差）

- 请求可构造、采用值回读一致、失败有分层码并保留原始结果与前后状态、模型不变、任务终态与关闭证据齐全。
- 未启用模块时**不得**产生任何写入或部分修改；`FEATURE_UNAVAILABLE` 必须在首个原生写调用之前。
- 不得以"控制反射资料"推断专题设置接口存在或不存在；只记录实测。

## 17. 下一步

1. 本计划与 `pass-d012-items.json` 交审查
2. 通过后先做 A 类离线用例（7 项，可并行），再做 B 类静态用例（6 项）
3. 原生部分随 STAR 许可解锁统一排队；未闭合项保留具体解除条件与证据索引

## 18. 最终状态（2026-11-08 收尾，离线）

- 六个 STAR kind（`star_align_check`…`star_inspect_fea`）已注册到 `ANALYSES` 与请求联合体，能力发现可见；通用工厂创建 + 实时 `IsSTARModuleEnabled` 门 + 单次 `GetSettings`。
- 采集器 `collect_star_results`：文本导出单独记录；网格读完整 `Ny×Nx`（`Values`/`ValueData`，无截断）；散点按 `scatter`（仅有限点）+ `rows`（含非法行、`invalid_count`）合同；消息按 `ErrorType` 14 值区分，致命优先 `ANALYSIS_FAILED` 并保留 `partial_result`；空 X/零列曲线与 `NumPoints=0` 散点块不计结构结果。
- 共享合同：`plotting.export_image` 散点图项按 `points` 非空过滤（空散点块 → `NO_PLOTTABLE_DATA`）；真实 `Backend._page_task_result` 散点 `rows` 分页与非方形 grid 区域已测。
- 其余 A 类 7 项与 B 类 6 项原生采用仍受 STAR 许可与受控 FEA 阻塞；未启用模块时零写入。
- 定向测试与 XML：`pass-d012-star-targeted.xml`（225 项，0 失败 0 错误 0 跳过）。

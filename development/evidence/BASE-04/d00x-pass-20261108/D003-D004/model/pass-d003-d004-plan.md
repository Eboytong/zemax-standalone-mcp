# D003 / D004 本轮计划（12 项）

工作区 `C:\Users\tonge\.codex\worktrees\zemax-p01-material-model\Zemax_MCP`，分支 `codex/d002-material-model`，基线 `34e1a18494015c2b383ec700b958015020b660fe`。
权威来源：`development/tracking/d00x-pass-20261108.json`（96 项，本 worker 29 项）+ `development/ledgers/operations.csv`、`development/ledgers/analyses.csv`。
本 worker 负责 D002 MaterialModel（1 项）、D003（5 项）、D004（7 项），随后 D011（16 项）。
**本计划只提交方案；未改产品代码、未运行原生、未改台账/schema/批次、未提交。**

## 0. 本轮共同前提

- **原生启动已登记延后**：`application_create` 已有 runtime-recovery-01/02/05 三次 180 s 超时独立证据（`development/evidence/BASE-04/runtime-phase-environment-20261108.md`）。本轮不再重复排查同一启动，所有原生作业只准备不执行。
- 每项先交短计划与证据索引，由协调者审核后实施。
- 不覆盖其他 worker 源码；STAR 共用入口补丁由 runtime 集成。
- 公共台账由协调者更新，本 worker 不改。

## 1. 顺序

按 tracking 的组序与台账状态排列，先做"已可离线推进"的项：

| 序 | 组 | 条目 | 台账状态 | 本轮性质 |
| --- | --- | --- | --- | --- |
| 1 | D003 | `ED-02.SurfacePickup.ChipZone` | blocked | 控制实验已备，待原生 |
| 2 | D003 | `ED-02.SurfacePickup.MechanicalSemiDiameter` | blocked | 同上 |
| 3 | D003 | `ED-02.SolveExtensions018` | 待验收（聚合） | 离线可补齐聚合范围 |
| 4 | D003 | `NS-01.Conversion` | implemented | 离线复核范围映射 |
| 5 | D003 | `ED-04.RayAimingWizard` | blocked | 离线复核 + 阻塞证据整理 |
| 6 | D004 | `CV-02.PowerFieldMapSettings` | implemented | 探针与合同测试已完成，待原生 |
| 7 | D004 | `CV-02.PowerPupilMapSettings` | implemented | 同上（共用验收） |
| 8 | D004 | `CV-01.SeidelDiagram` | blocked | 出口清单审计（限定范围） |
| 9 | D004 | `CV-01.FullFieldSpot` | implemented | 结果出口阻塞归档 |
| 10 | D004 | `CV-01.MatrixSpot` | implemented | 同上 |
| 11 | D004 | `CV-01.ConfigurationMatrixSpot` | implemented | 同上 |
| 12 | D004 | `CV-01.FftSurfaceMtf` | implemented | 离轴映射门槛复核 |

---

## 2. D003 逐项

### 2.1 `ED-02.SurfacePickup.ChipZone`（blocked）

- **当前正式接口**：`ILDERow.ChipZoneCell`（反射类型为通用 `ZOSAPI.Editors.IEditorCell`）→ `CreateSolveType(SurfacePickup)` / `SetSolveData`；`ISolveSurfacePickup{Surface,Column,ScaleFactor,Offset}`；回读经 `backend._surface_data` → `cells.chip_zone`。列枚举 `SurfaceColumn.ChipZone=7`。
- **已有输入/结果**：自建顺序模型，源 0.5 / 目标 0.2；`SetSolveData` 返回 Success 但 `cell.Solve=Automatic`；适配器 `SOLVE_UPDATE_FAILED` + `PARTIAL_UPDATE`，rev 6；检查点重载恢复通过。原始 stdio：`.local/runs/runs/chip_zone_pickup_refusal_cdca2ea390/calls.json`（11 条调用）。
- **可离线补齐**：C2/C3 控制探针 + 5 项普通测试已完成（§3）；接口逐项核对 5/5。
- **实际检查（本轮已执行）**：`pytest tests/unit/test_pickup_probe_contracts.py` → 5 passed；`d003-interface-check.py` → 5/5 接口成员命中，exit 0。
- **外部阻塞**：原生不采用该模式（`SetSolveData` Success 但回退 `Automatic`）。
- **解除条件**：四时刻任一处三路回读均为 SurfacePickup，且 `Surface/Column/Scale/Offset` 正确、数值联动、保存重载、关闭全部通过。

### 2.2 `ED-02.SurfacePickup.MechanicalSemiDiameter`（blocked）

- **当前正式接口**：`ILDERow.MechanicalSemiDiameterCell`（同为通用 `IEditorCell`）；列枚举 `MechanicalSemiDiameter=8`。
- **已有输入/结果**：源 5.5 / 目标 5.2 → 回退 `Fixed`；`SOLVE_UPDATE_FAILED` + `PARTIAL_UPDATE`；检查点恢复通过。**新增观察**：失败写入把目标值由 5.2 改写为 5.0（等于面 1 的 `semi_diameter=5`），ChipZone 则不变。
- **可离线补齐**：同一探针覆盖（两单元格各跑一遍）。
- **实际检查**：同 2.1（5 passed）。
- **外部阻塞**：原生不采用该模式，且失败路径有数值副作用。
- **解除条件**：同 2.1；另需证明失败/成功路径不残留数值改写。

### 2.3 `ED-02.SolveExtensions018`（聚合项，待验收）

- **当前正式接口**：`SOLVES` / `SOLVE_FIELDS` / `SOLVE_ALIASES`（`modeling.py:14` 起）+ `backend._validate_solve` / `_set_solve`。
- **已有输入/结果**：`remaining-ranked.md` 记"已实现待验收"，前置为 MaterialModel 与两类 SurfacePickup；`solve-extensions.md:76-79` 已登记 4 条限制。
- **可离线补齐**：从源码枚举"已确认可采用"的 solve 集合与"已登记限制"的集合，生成一张聚合范围表（哪些 mode 有单元测试、哪些有原生证据、哪些仅登记限制）。
- **实际检查**：尚未执行（本轮新任务）。
- **外部阻塞**：依赖 2.1/2.2 与 D002 MaterialModel。
- **解除条件**：前置三项收口，且聚合表与台账口径一致。

### 2.4 `NS-01.Conversion`（implemented）

- **当前正式接口**：`src/zemax_mcp/conversion.py`、`conversion_models.py`；正式顺序转 NSC 工具。
- **已有输入/结果**：纯 NSC 已验收；混合组在 dummy 边界与关闭光阑孔径下 `TASK_START_FAILED` / `An unknown error occurred`；失败工具关闭与检查点恢复已通过。
- **可离线补齐**：复核转换范围与对象/曲面映射表，把"已验收范围"与"失败范围"写成明确边界；不改实现。
- **实际检查**：尚未执行。
- **外部阻塞**：混合组原生转换失败。
- **解除条件**：混合组原生设置、光线、保存重载、取消全部通过。

### 2.5 `ED-04.RayAimingWizard`（blocked）

- **当前正式接口**：design tool `RayAimingWizard`（`models.py` 请求 + `backend.py` 执行）；`RunAndWaitWithTimeout` / `Cancel` / `WaitWithTimeout` / `IsRunning` / `Close`。
- **已有输入/结果**：受控模型 `RunAndWaitWithTimeout(10)` → `TimedOut`；`Cancel=true` 后 `WaitWithTimeout(10)` 仍 `TimedOut` 且 `IsRunning=true`；`Close=false`；应用断连成功。证据 `verification/development/ED-04/ray-aiming276/probe.json`。
- **可离线补齐**：复核请求模型与文档一致性；整理"工具不可完成/不可取消"的最小复现描述。
- **实际检查**：尚未执行。
- **外部阻塞**：正式完成/取消/关闭路径不可用。
- **解除条件**：取得可靠的完成/取消/关闭路径或修正后的原生版本，再验预览、Apply、保存重载与模型保持。

---

## 3. D004 逐项

### 3.1 / 3.2 `CV-02.PowerFieldMapSettings`、`CV-02.PowerPupilMapSettings`（implemented）

- **当前正式接口**：`run_analysis` 的 `power_field_map` / `power_pupil_map`（`power_maps.py:12-29`）；原生 POWF/POWP 操作数；`backend._page_task_result` 分页。
- **已有输入/结果**：596 值状态、593 孔径环、474 解析参考（`1.934985890557074e-4` 最大绝对差）、互逆不变量 14 点 `4.74e-6`。
- **可离线补齐（本轮已完成）**：E1 判别表；E2/E3 探针五项合同修正；17 项离线契约测试；`power-maps-review3-report.md`。
- **实际检查**：`pytest test_power_maps.py + test_power_probe_contracts.py` → 44 passed；三份探针编译通过；两份 native jobs JSON 可读。
- **外部阻塞**：`application_create` 超时；零 EFL 语义与环状态仍无正式定义。
- **解除条件**：E2/E3 原生执行并给出可区分证据；否则保持 `unresolved` / `unavailable`。

### 3.3 `CV-01.SeidelDiagram`（blocked）

- **当前正式接口**：`run_analysis: seidel_diagram`（`analysis_models.py` + `analyses.py` 均存在，本轮已核）；设置接口为专用 `IAS_SeidelDiagram`。
- **已有输入/结果**：设置回读准确；原生设置/`EXPORT_FAILED` 关闭验收 1 项通过；独立 `SeidelCoefficients` 球面 S1 参考 `1e-6` 通过，但**不含图表**；`outlets265/summary.json` 已扫出口。
- **可离线补齐**：把已检查出口整理为**限定范围**结论（"已检查的这些出口没有图形/数值结果"），不推断"原生侧不存在"。
- **实际检查**：本轮已确认 typed request 与 dispatch 存在（`analysis_models.py`、`analyses.py` 各命中）。
- **外部阻塞**：无图形/数值结果出口。
- **解除条件**：出现正式结果出口，或验证等价数值实现（含图元映射）。

### 3.4 `CV-01.FullFieldSpot`（implemented）

- **当前正式接口**：`run_analysis: full_field_spot`，`AS_Spot` 设置。
- **已有输入/结果**：设置写入/回读/运行/关闭均采用；三种场/波长/参考点配置均 `RESULT_UNAVAILABLE`，`SpotData` 与正式出口为空；失败任务关闭、曲面基线保持。
- **可离线补齐**：归档"结果出口缺失"的最小证据链；复核 `AS_Spot` 设置回读字段清单。
- **实际检查**：本轮已确认 typed request 与 dispatch 存在。
- **外部阻塞**：结果出口缺失。
- **解除条件**：有效原生结果出口，或验证参考点/放大/布局映射后实现替代路径。

### 3.5 `CV-01.MatrixSpot`（implemented）

- **当前正式接口**：`run_analysis: matrix_spot`。
- **已有输入/结果**：完成计算但 `SpotData`/数组为空、`GetTextFile=false`，返回 `EXPORT_FAILED`；矩阵专题控制项确认模型状态与任务关闭。
- **可离线补齐**：同 3.4，出口缺失归档。
- **实际检查**：本轮已确认 typed request 与 dispatch 存在。
- **外部阻塞**：无正式数值/图形出口。
- **解除条件**：正式出口或经验证的等价计算。

### 3.6 `CV-01.ConfigurationMatrixSpot`（implemented）

- **当前正式接口**：`run_analysis: configuration_matrix_spot`；反射确认 `ConfigurationMatrixSpot`、`IAS_Spot` 及 11 项可写设置。
- **已有输入/结果**：双配置原生 1 项通过；与 MatrixSpot 同样无 `SpotData` 或文本，显式 `EXPORT_FAILED`；模型保持/关闭通过。
- **可离线补齐**：同 3.5。
- **实际检查**：本轮已确认 typed request 与 dispatch 存在。
- **外部阻塞**：无有效原生出口。
- **解除条件**：同 3.5。

### 3.7 `CV-01.FftSurfaceMtf`（implemented）

- **当前正式接口**：`run_analysis: fft_surface_mtf`；反射确认 6 项可写设置。
- **已有输入/结果**：6 项分析关闭、系统状态保持、断开通过；复瞳自相关对照最大误差 field1 `6.66e-16`、field3 `0.0049502`（< `0.005` 门槛）；离轴独立光线到复瞳坐标/幅度映射仍超限。
- **可离线补齐**：把"近轴/小视场通过、离轴映射超限"的边界写成明确门槛表；复核现有测试断言。
- **实际检查**：本轮已确认 typed request 与 dispatch 存在。
- **外部阻塞**：离轴映射超限。
- **解除条件**：离轴映射进入门槛，或把当前门槛与适用范围正式记录为限制。

---

## 4. 本轮不做的

- 不执行任何原生作业（E2/E3、C2/C3 只准备）。
- 不改 `src/` 产品逻辑；不改公共请求/响应 schema；不改台账、批次、tracking JSON。
- 不提交 Git、不自行发行。
- 不清理工作区根目录 `pytest-of-tonge/`（按指示保留并已记入两份交付报告）。

## 5. 证据索引

| 类别 | 路径 |
| --- | --- |
| 本计划 | `.local/coordination/pass-d003-d004-plan.md` |
| 条目表 | `.local/coordination/pass-d003-d004-items.json` |
| D003 计划/报告 | `.local/coordination/d003-pickup-plan.md`、`d003-pickup-implementation-report.md`、`d003-pickup-native-jobs.json` |
| D003 离线复算 | `.local/coordination/d003-calls-index.py`、`d003-calls-detail.py`、`d003-interface-check.py` |
| D003 探针/测试 | `scripts/probes/ED-02/pickup_solve_adoption018.py`、`tests/unit/test_pickup_probe_contracts.py` |
| D004 报告 | `.local/coordination/power-maps-review3-report.md`、`power-maps-implementation-report.md`、`power-maps-plan.md`、`power-maps-native-jobs.json` |
| D004 探针/测试 | `scripts/probes/CV-02/power_radius_sweep018.py`、`power_asymmetric_aperture018.py`、`tests/unit/test_power_probe_contracts.py` |
| 台账快照 | `.local/coordination/d003-d004-ledger.json`、`d004-analyses.json` |

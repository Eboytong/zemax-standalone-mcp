# D011 计划（EXT-STAR，16 项）

工作区 `C:\Users\tonge\.codex\worktrees\zemax-p01-material-model\Zemax_MCP`，分支 `codex/d002-material-model`，基线 `34e1a18494015c2b383ec700b958015020b660fe`。
权威来源：主仓 `development/tracking/d00x-pass-20261108.json` 顶层 `items` 中 `development_group=="D011"`（16 项）；台账 `development/ledgers/operations.csv`（16 项均为 `blocked`，BOM 编码 `utf-8-sig`）。

**本轮性质声明**：原生启动统一延后（`application_create` 三次 180 s 超时证据 `development/evidence/BASE-04/runtime-phase-environment-20261108.md`）。D011 本轮为**离线审计 + 实际实现（Unload）+ 已有原生证据复用**：逐项核对正式反射接口、当前适配器源码、历史原生证据，运行普通检查；不执行新的原生会话，不据此关闭条目，不增加批次完成数（B003 计数为历史来源）。**Unload 三型已在主仓实际实现**（`StarUnload` 联合 + `_run_star_unload`，21 个新测试通过），已合入主仓（待原生）。计划文本本身不算完成。

## 0. 共同前提与既有证据

- **原生阻塞证据（2026-11-06，`verification/development/EXT-STAR/readiness193.json`）**：`IsSTARModuleEnabled=false`，`IsValidLicenseForAPI=true`，`STARData_type=ZemaxUI.ZOSAPI.Editors.ZOSAPI_STAR_Data`；`native190-materials.xml` passed 0 / failed 1（首个波长折射率返回无效 0）；`native192-availability.xml` passed 1（FEATURE_UNAVAILABLE 门控、材料无效 0 拒绝、目录复用与源保持、正常断开）。
- **接口反射证据（2026-11-05）**：`probe037.json`（读/导入/拟合接口）、`probe038.json` + `parameters038.json`（控制接口与参数名）、`probe039.json`（`ISTARMaterials` 方法签名 + `ISTAR_*FEAData.UnloadData()` 卸载接口）。
- **对账记录（2026-11-08）**：`development/evidence/EXT-STAR/control-evidence-reconciliation-20261108.md`（静态复核，无新原生会话）。
- **文档**：`docs/topics/extensions/star.md`、`docs/topics/imaging/materials.md`。
- **普通检查基线**：`verification/development/EXT-STAR/ordinary049.xml`（passed 1531 / failed 0 / errors 0）。
- **代码模块**：`src/zemax_mcp/star.py`（读/导入/拟合，213 行）、`star_controls.py`（8 类控制，270 行）、`star_materials.py`（材料查询，31 行）、`star_models.py`（typed 请求，190 行）。

## 1. 顺序（沿用 tracking 次序）

| 序 | 条目 | 正式接口（反射确认） | 适配器入口 | 本轮离线动作 |
| --- | --- | --- | --- | --- |
| 1 | `EXT-STAR.Read` | `ILDERow.STARData.{Deformations,Temperatures,DirectIndex}.FEAData` + Fits | `star.py:get_star_data` | 复核分页/字段/单元、跑单测 |
| 2 | `EXT-STAR.UpdateMode` | `ISTARSubsystem.UpdateMode` + `DoManualUpdate()` | `star_controls.py:update_mode` | 复核枚举采用与回滚 |
| 3 | `EXT-STAR.Materials.refractive_index` | `ISTARMaterials.GetRefractiveIndex(...)` | `star_materials.py` | 复核参数顺序/正性门、跑单测 |
| 4 | `EXT-STAR.Materials.dndt` | `ISTARMaterials.GetDNDT(...)` | `star_materials.py` | 复核有限性门（正性缺失） |
| 5 | `EXT-STAR.ThermalControls` | `SetThermalFEAFitType` / `SetWorkingWavelength` | `star_controls.py:thermal_controls` | 复核编号范围校验 |
| 6 | `EXT-STAR.VolumeControls` | `GRINStep` / `Fits.GRINStep` | `star_controls.py:volume_controls` | 复核双成员补丁 |
| 7 | `EXT-STAR.ImportDeformation` | `ISTAR_DeformationsFEAData.ImportDeformations` | `star.py:run_star_operation(import_*)` | 复核暂存/单位/坐标系 |
| 8 | `EXT-STAR.FitDeformation` | `ISTAR_DeformationFits.Refit` + Options | `star.py:run_star_operation(fit_*)` | 复核 fit 设置/应用顺序 |
| 9 | `EXT-STAR.ImportTemperature` | `ISTAR_TemperaturesFEAData.ImportTemperatures` | 同上 | 同上 |
| 10 | `EXT-STAR.FitTemperature` | `ISTAR_TemperaturesFits.Refit` | 同上 | 同上 |
| 11 | `EXT-STAR.ImportDirectIndex` | `ISTAR_DirectIndexFEAData.ImportDirectIndex` | 同上 | 同上 |
| 12 | `EXT-STAR.FitDirectIndex` | `ISTAR_DirectIndexFits.Refit` | 同上 | 同上 |
| 13 | `EXT-STAR.FittedSamples` | `Fits.GetFitted*` | `star.py:get_star_data(sample_points=)` | 复核样本坐标约定 |
| 14 | `EXT-STAR.UnloadDeformation` | `ISTAR_DeformationsFEAData.UnloadData()` | `star.py:_run_star_unload`（已实现） | 已实现+21 测试，待原生 |
| 15 | `EXT-STAR.UnloadTemperature` | `ISTAR_TemperaturesFEAData.UnloadData()` | 同上 | 同上 |
| 16 | `EXT-STAR.UnloadDirectIndex` | `ISTAR_DirectIndexFEAData.UnloadData()` | 同上 | 同上 |

## 2. 每项计划要点

- **Read**：`get_star_data` 返回导入/启用、原生文件、坐标系、拟合设置、统计、刚体、坐标变换；FEA 点按 `rows` 分页（≤1000），先物化完整原生数组再切页。离线核 `StarRead` 校验（`remove_rigid_body` 仅变形、变形样本 z 必须 0）。解除：启用模块 + 受控 FEA，验数值/分页/重载/恢复/关闭。
- **UpdateMode**：`check_mode` 写后 `Equals` 回读；`manual_update` 调 `DoManualUpdate()`；失败回滚到 `mode_before`。离线核 `StarUpdateMode` 非空校验。
- **Materials.refractive_index**：参数顺序 `(catalog,material,wavelength,envP,envT,matP,matT)`；`value<=0` 或非有限 → `INVALID_RESULT_DATA`。历史原生六条件均返回 0。
- **Materials.dndt**：参数追加 `delta_temperature`；**仅校验有限性，未校验正性**（见 §3 发现 B），0 值会被静默接受，需独立热光参考才能验收。
- **ThermalControls**：`SetThermalFEAFitType` / `SetWorkingWavelength`；波长编号须 ≤ 系统波长数。fit_type 整数语义待原生确认。
- **VolumeControls**：分别改 `owner.GRINStep` 与 `owner.Fits.GRINStep` 并回读最终组合；物理步长约定待原生验收。
- **Import×3**：绝对路径存在性、长度单位必须匹配镜头单位（否则 `UNIT_MISMATCH`）、坐标系写后回读、导入后核对标志/非空点数/文件回读、失败 `_restore_model` 恢复。
- **Fit×3**：前置已导入；局部 `settings` 写入回读→`Refit`→`apply=keep/enable/disable`→启用态回读；变形 `deformation_option` 枚举比较按值。容差见 §4。
- **FittedSamples**：变形用 X/Y，温度/折射率用 X/Y/Z；`remove_rigid_body` 仅变形；输出保留原生坐标约定。
- **Unload×3**：反射接口 `ISTAR_*FEAData.UnloadData()` 已确认；本轮已实现 typed `unload_*` 操作（`StarUnload`）、受控调用、前读/后核导入标志、源资源保留与检查点/取消/恢复；21 个测试通过。已合入主仓，待原生验收。

## 3. 审计发现（本轮静态/离线可确认）

- **发现 A（已实现）**：三个 `Unload*` 原无适配器路径。本轮已实现：`star_models.py` 新增 `StarUnload` 并加入 `StarOperation`；`star.py` 新增 `_run_star_unload`（前读 `imported/NumberOfDataPoints/Filename`、`UnloadData()`、后核对导入标志清除、检查点/取消/恢复）；`backend.py` capabilities 加 `unload`；文档/示例补齐；21 个卸载测试通过。导入标志按 `BRANCHES[data_kind][1]`（`IsDirectIndexImported` 等）读取。详见 `d011-unload-patch.md`。台账 `entry_points` 映射偏差仅记录，不改台账。
- ~~发现 B（dn/dT 正性）~~ **撤销**：dn/dT 允许零或负，仅校验有限性是正确行为；历史零值靠独立热光参考与输入身份判定，不加 `value>0`。
- **发现 B（证据日期）**：readiness193 与 probe037/038/039 为 2026-11-05/06 采集；2026-11-08 仅为静态对账，无新原生会话。本轮沿用，不新增。

## 4. 容差（原文引用，不得改）

- 变形：`1e-8 镜头单位 + 1e-6×参考值`
- 温度：`1e-6 °C + 1e-6×参考值`
- 直接折射率：`1e-8 + 1e-7×参考值`

## 5. 不做的

- 不启动原生会话；不改 `src/` 共享 STAR 入口（由 runtime 集成）；不改 schema/台账/批次/tracking；不提交 Git；不清理临时目录。

## 6. 证据索引

| 类别 | 路径 |
| --- | --- |
| 计划 | `.local/coordination/pass-d011-plan.md` |
| 条目表 | `.local/coordination/pass-d011-items.json` |
| 审计报告 | `.local/coordination/pass-d011-report.md` |
| 台账快照 | `.local/coordination/d011-ledger.json` |
| 接口反射 | `verification/development/EXT-STAR/probe037.json`、`probe038.json`、`parameters038.json`、`probe039.json` |
| 原生就绪/材料 | `verification/development/EXT-STAR/readiness193.json`、`native190-materials.xml`、`native192-availability.xml` |
| 对账 | `development/evidence/EXT-STAR/control-evidence-reconciliation-20261108.md` |
| 文档 | `docs/topics/extensions/star.md`、`docs/topics/imaging/materials.md` |
| 源码 | `src/zemax_mcp/star.py`、`star_controls.py`、`star_materials.py`、`star_models.py` |
| 单测 | `tests/unit/test_star.py`、`test_star_controls.py`、`test_star_materials.py` |
| 卸载补丁规格 | `.local/coordination/d011-unload-patch.md` |

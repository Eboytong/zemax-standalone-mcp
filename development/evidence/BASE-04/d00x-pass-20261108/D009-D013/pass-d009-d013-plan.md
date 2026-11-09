# D009 / D013 逐项计划与证据索引（本轮）

- 日期：2026-11-08（Asia/Shanghai）
- Worker：`zemax-p01-runtime`
- 权威计划：`development/tracking/d00x-pass-20261108.json`（96 项，D001–D013）
- 分组定义：`development/tracking/development-groups.json` → D009「CAD与受保护格式交付」（5 项）、D013「HPC配置与分布式任务」（5 项）
- 状态来源：`development/ledgers/operations.csv`
- 本文件范围：**只覆盖 D009 五项 + D013 五项**。其余条目由各自 worker 负责。

## 0. 本轮边界与前置

1. **不重复原生启动**。`application_create` 已有 `runtime-recovery-01/02/05` 三次独立 180 s 超时证据
   （`development/tracking/d00x-pass-20261108.json` 的 `repeated_environment_blocker` 已登记
   `decision=defer_native_startup_for_this_pass`）。本轮所有条目**不再发起任何原生启动**。
2. 因此本轮对每项只产出：当前正式接口、已有输入/结果、可离线补齐内容、**实际做过的检查**、
   外部阻塞与**明确解除条件**。原生验收统一挂起到启动恢复之后。
3. 只读旁证（本轮未启动任何实例，仅查询既有状态，**不作为许可可用结论**）：
   - `ANSYS, Inc. License Manager CVD`、`ANSYSLicensingTomcat`、`FlexNet Licensing Service 64` 服务 `Running`；
   - 进程存在 `ansyslmd.exe`(14964)、`lmgrd.exe`×4；**当前无 `OpticStudio.exe` 进程**；
   - 环境 `ANSYSLMD_LICENSE_FILE=1055@localhost`，`ANSYSLIC_DIR=...\Shared Files\Licensing`。
   - ⚠ **服务 Running ≠ 许可可用**。许可是否可用必须由执行结果（`GetHPCSettingsFromPrefs`/导出运行）确认，不得据此判定许可故障已排除。

## 1. D009 — CAD 与受保护格式交付

组目标：统一导出设置、实际文件格式与版本、配置分层和正式创建协议（`development-groups.json` D009）。

| # | 条目 | 台账 state | 本轮结论 | 建议决议 |
| --- | --- | --- | --- | --- |
| 1 | EXT-EXPORT.CadSettings | implemented | 接口完整；受本机导出器格式/版本能力限定 | 保持 implemented，待原生格式矩阵 |
| 2 | EXT-EXPORT.CadMultipleConfigurations | blocked | STEP 五模式通过；IGES 层号不采用 | 保持 blocked（输出与请求不符） |
| 3 | EXT-EXPORT.LegacyLinework | blocked | 本机公开 API 无创建接口 | 保持 blocked（接口缺失） |
| 4 | EXT-EXPORT.BlackBox | blocked | 无 ZBB 创建工厂 | 保持 blocked（接口缺失） |
| 5 | EXT-EXPORT.EncryptedCoating | blocked | 无 ZEC 创建工厂 | 保持 blocked（接口缺失） |

### 1.1 EXT-EXPORT.CadSettings

- **当前正式接口**：工具 `run_cad_export(request: CadExport)`（`src/zemax_mcp/server.py:447`），
  契约 `src/zemax_mcp/export_models.py::CadExport`（21 种 `format` 字面量 + 13 个可选设置）；
  格式扩展名表 `src/zemax_mcp/exports.py::CAD_EXTENSIONS`；能力表由
  `src/zemax_mcp/backend.py:645` `get_capabilities` → `cad_formats`（含 `native_succeeded`/`native_rejected`）离线给出。
- **已有输入**：`examples/requests/cad-settings044.json`、`cad-nsc186.json`、`cad-multiple175.json`。
- **已有结果**：`development/evidence/EXT-EXPORT/cad-settings-repeat20261108.md`；
  21 格式原生矩阵中 **15 成功**（STEP/IGES/SAT/STL/SAB/OBJ/VRML/VisualizationJSON/ZMO/XT/XB/PRC/JT/N3MF/U3D）、
  **6 拒绝**（ASAT/ASAB/MODEL/CATPART/CATPRODUCT/XCGM，原生 `Unsupported export format`）；
  ACIS：SAT/SAB 的 V30 设置被 getter 接受，但**实际输出头 `version_code=500`（major 5）**，适配器返回 `SETTING_REJECTED`；`Current` 复用成功、头 500。
- **可离线补齐**：能力表（`get_capabilities.cad_formats`）与 request 模型校验已离线覆盖；无更多可离线内容。
- **实际检查（本轮）**：`pytest tests/unit/test_cad_adoption.py -q` → **63 passed**（XML `review-d009-cad.xml`）。
- **外部阻塞**：ASAT/ASAB 需本机正式导出器实际支持才能验版本；SAT/SAB 显式版本需原生输出头采用请求版本或上游提供正式版本设置路径。
- **解除条件**：上游导出器支持 ASAT/ASAB；SAT/SAB 支持显式版本；随后跑
  `tests/native/test_cad_formats_live.py`、`tests/native/test_cad_acis_live.py`、`tests/native/test_cad_advanced_acis_live.py`。

### 1.2 EXT-EXPORT.CadMultipleConfigurations

- **当前正式接口**：同 `run_cad_export`；配置选择经 `SetSingleConfiguration`，输出模式 `current/single/all_by_layer/all_at_once/all_by_file`。
- **已有输入**：`examples/requests/cad-multiple175.json`；原生用例 `tests/native/test_cad_multiple_live.py`、`test_cad_layer_modes_live.py`。
- **已有结果**：`development/evidence/EXT-EXPORT/cad-multiple-configurations-repeat20261108.md`：
  双配置圆柱模型（配置1/2 厚 2/4 mm）上 **五种 STEP 模式体积校验通过**（容差 `1e-5 mm³+1e-6×参考值`），配置/曲面/系统保持通过、任务均 `close_attempted=true` 无 cleanup 警告；
  但 **IGES 层号不采用**：`all_by_layer` 实际 `{65535}`（预期 `{10,11}`）、`all_at_once` 实际 `{65535}`（预期 `{10}`）。
- **可离线补齐**：可增补层模式名称→请求层号的纯单元断言（不触及原生），但**真正的层赋值只能原生验证**，本轮不新增。
- **实际检查（本轮）**：同 1.1 的 63 项 `test_cad_adoption.py` 通过（CAD 通用校验）；本条无独立普通测试文件。
- **外部阻塞**：IGES 层号设置可回读但原生输出只用默认 65535 —— 需正式层赋值导出能力或上游修复。
- **解除条件**：取得能输出请求层号的正式导出路径或上游修复后，重跑两个 IGES 模式复验层分配。

### 1.3 EXT-EXPORT.LegacyLinework

- **当前正式接口**：**不存在**。公开类型扫描 908 类型（`.local/evidence/development/EXT-EXPORT/public-types042.json`）无 `Linework/DXF/IGES` 专用创建方法；`run_cad_export` 的实体 CAD 不能替代旧线框范围。
- **已有输入/结果**：`development/evidence/EXT-EXPORT/legacy-linework-interface-followup-20261108.md`；本机手册第 49–51 页记载 GUI 的 2D DXF/3D DXF/IGES Linework。
- **可离线补齐**：无（无接口即无可写契约；伪造请求违反"不伪造"原则）。
- **实际检查（本轮）**：只读复核接口缺失（依既有扫描）；未新建工具、未改模型。
- **外部阻塞**：本机版本无旧线框创建工厂/自动化协议。
- **解除条件**：本机版本提供旧线框创建工厂/自动化协议、参数与许可说明。

### 1.4 EXT-EXPORT.BlackBox

- **当前正式接口**：**不存在创建接口**。`ISurfaceBlackBoxLens` 仅消费已有 ZBB 面；`IOpticalSystemTools` 导出覆盖 CAD/布局/Speos，无 ZBB 创建工厂。
- **已有输入/结果**：`development/evidence/EXT-EXPORT/blackbox-interface-followup-20261108.md`；手册记载 GUI ZBB 创建；样例目录无 ZBB 样例。
- **可离线补齐**：无。
- **实际检查（本轮）**：只读复核 908 公开类型，确认无创建工厂；未修改模型。
- **外部阻塞**：无 ZBB 创建协议/工厂。
- **解除条件**：本机版本提供受支持的 ZBB 创建协议/工厂、参数与许可说明。

### 1.5 EXT-EXPORT.EncryptedCoating

- **当前正式接口**：**不存在**。908 类型扫描无 `EncryptedCoating/ZEC` 专用创建接口；CAD/布局/Speos/点云接口不能表达镀膜加密范围、文件名与重载条件。
- **已有输入/结果**：`development/evidence/EXT-EXPORT/encrypted-coating-interface-followup-20261108.md`；手册第 54、283 页记载 GUI Export Encrypted Coating 与 `.ZEC`。
- **可离线补齐**：无。
- **实际检查（本轮）**：只读复核接口缺失；未创建工具。
- **外部阻塞**：无 ZEC 创建工厂/自动化协议。
- **解除条件**：取得安装版本支持的 ZEC 创建工厂/自动化协议、参数与许可说明。

## 2. D013 — HPC 配置与分布式任务

组目标：先取得可用偏好配置，再完成四类节点作业的完整生命周期与结果回收（`development-groups.json` D013）。

| # | 条目 | 台账 state | 本机 HPC 工厂 | 本轮结论 | 建议决议 |
| --- | --- | --- | --- | --- | --- |
| 1 | EXT-HPC.Settings | implemented | `GetHPCSettingsFromPrefs` / `GetHPCSettingsCustom` | 接口在；正式查询返回 null（**原因未区分**） | 保持 implemented，原因待区分 |
| 2 | EXT-HPC.NSCTrace | implemented | `OpenNSCRayTrace_HPC` | 前提未满足，preflight 后 skip | 保持 implemented，待配置+原生 |
| 3 | EXT-HPC.Tolerancing | implemented | `OpenTolerancing_HPC` | 同上 | 同上 |
| 4 | EXT-HPC.GlobalOptimization | implemented | `OpenGlobalOptimization_HPC` | 同上 | 同上 |
| 5 | EXT-HPC.HammerOptimization | implemented | `OpenHammerOptimization_HPC` | 同上 | 同上 |

### 2.1 EXT-HPC.Settings

- **声明范围 = 配置查询**：只读取原生 `IHPCSettings` 并回报实际字段，**不提交、不运行、不观察、不取消任何 HPC 作业**。
- **当前正式接口**：工具 `get_hpc_settings(request: HpcSelection)`（`server.py:252`）；
  契约 `src/zemax_mcp/hpc_models.py`：`HpcPreferences{mode:'preferences'}` | `HpcCustom{mode:'custom',node_count≥1,instance_type∈Default/Tiny/Small/Medium/Large/XLarge}`（判别式联合 `HpcSelection`）；
  适配器 `src/zemax_mcp/hpc.py::prepare_hpc`，错误码 `HPC_SETTINGS_UNAVAILABLE`/`HPC_NOT_CONFIGURED`/`UNSUPPORTED_INTERFACE`。
- **已有输入**：`examples/requests/hpc040.json`。
- **已有结果**：`development/evidence/EXT-HPC/settings-preferences-20261108.md`：原生 `GetHPCSettingsFromPrefs` 返回 **null** → `HPC_SETTINGS_UNAVAILABLE`，`partial_changes_possible=false`，无节点数/实例/线程/关机 ticks；调用后 stdio 正常断开、无残留进程。原始调用 `.local/runs/runs/hpc_settings_a5fe9c5bd1/calls.json`。
- **可离线补齐**：`HpcSelection` 联合校验、custom 节点数/规格校验、错误映射已离线覆盖（见 2.2 的 34 项）。
- **实际检查（本轮）**：`pytest tests/unit/test_hpc.py tests/unit/test_hpc_execution.py -q` → **34 passed**（XML `review-d013-hpc.xml`）。
- **外部阻塞**：**观察事实**：正式查询 `GetHPCSettingsFromPrefs` 返回 **null**（`HPC_SETTINGS_UNAVAILABLE`）。
  ⚠ **尚未区分**原因——配置、许可、服务或版本条件都未被排除或确认；**不得**把"本机偏好未配置"写成已确认根因。
- **解除条件（仅配置查询）**：正式查询返回**非 null** 的 `IHPCSettings` 且**实际字段回读**成功（节点数/最大节点数/规格/每任务线程数/关机 ticks），
  **未创建任何 SystemTool**、**正常断开**；**即使 `is_configured=false` 也算查询完成**。再重跑
  `tests/native/test_hpc_live.py::test_hpc_native_configuration_query`。
  节点/作业就绪**不属于**本项（属于 2.2 四条执行项），不得用它扩充本门槛。

### 2.2 EXT-HPC.NSCTrace / Tolerancing / GlobalOptimization / HammerOptimization

四条同源，共用前置 `EXT-HPC.Settings`：

- **当前正式接口**：四个既有工具新增可选 `hpc` 对象（`docs/topics/extensions/hpc.md` 执行节）——
  `run_nsc_ray_trace→OpenNSCRayTrace_HPC`、`run_tolerance_analysis→OpenTolerancing_HPC`、
  `run_global_optimization→OpenGlobalOptimization_HPC`、`run_hammer_optimization→OpenHammerOptimization_HPC`；
  适配器 `hpc.py::open_execution_tool`/`check_tool_values`/`close_failed_setup`。
- **已有输入**：各自原生用例 `tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[nsc|tolerance|global|hammer]`。
- **已有结果**（逐条 preflight）：四份 preflight 文档均记录 stdio `connect` 成功 → `GetHPCSettingsFromPrefs` 返回 `HPC_SETTINGS_UNAVAILABLE`（`partial_changes_possible=false`、model revision 0）→ **未打开任何工具/未改模型** → `disconnect` 成功、无残留进程；原生用例 **1 skipped**（12.86–13.02 s）。
  - `nsc-trace-preflight20261108.md`（`.local/runs/runs/hpc_nsc_e100e36be9/calls.json`）
  - `tolerancing-preflight20261108.md`（`.local/runs/runs/hpc_tolerance_050d84f49e/calls.json`）
  - `global-optimization-preflight20261108.md`（`.local/runs/runs/hpc_global_b4c8326146/calls.json`）
  - `hammer-optimization-preflight20261108.md`（`.local/runs/runs/hpc_hammer_e5b2191e4c/calls.json`）
- **可离线补齐**：四类工厂选择、配置校验、失败清理顺序已被 34 项普通测试覆盖；无新增离线内容。
- **实际检查（本轮）**：同 2.1 的 34 项通过。
- **外部阻塞**：与 `EXT-HPC.Settings` **同一观察事实**（`GetHPCSettingsFromPrefs` 返回 null）；
  配置/许可/服务/版本四类条件均**尚未区分**。
- **解除条件**：先满足 `EXT-HPC.Settings`（配置查询）解除条件，再确认节点分配与功能许可，**各条目另需本项自有**的作业终态证据——
  逐条跑 `test_hpc_minimal_native_job_result_and_close[<kind>]`，验证队列/状态/取消/结果/关闭，并与本地参考对照
  （NSC 直接光线功率参考 1、容差 `1e-8+1e-7×参考值`）。作业终态**不并入** Settings 门槛。

## 3. 本轮实际检查汇总

| 检查 | 命令 | 结果 | XML |
| --- | --- | --- | --- |
| D009 普通 | `pytest tests/unit/test_cad_adoption.py -q` | **63 passed** | `review-d009-cad.xml` |
| D013 普通 | `pytest tests/unit/test_hpc.py tests/unit/test_hpc_execution.py -q` | **34 passed** | `review-d013-hpc.xml` |

XML 目录：`.local/evidence/development/BASE-04/parallel-01/`。
**未执行任何原生**（`--run-zemax` 全部跳过）。

**离线开发面已核实完成**：D009/D013 所有可离线实现的行为均**已实现且有单测覆盖**（63 CAD + 22+12 HPC = 97 项）：

- `test_cad_adoption.py` 已覆盖 settings/format/config-encoding 与 ACIS 头解析、`SETTING_REJECTED`、
  config 模式编码（L167 `all_by_file→5/all_by_layer→6/all_at_once→7`）、冲突拒绝（L176）、工厂选择（L192）。
- `test_hpc.py`(22) 覆盖 `HpcSelection` 联合、custom 节点/规格校验、`HPC_NOT_CONFIGURED`、
  工厂选择/清理/null-error 不回退；`test_hpc_execution.py`(12) 覆盖四类 `*_HPC` 工厂装配。

**结论**：无额外可安全离线实施的代码改动能推进这些条目；剩余进度只能靠**原生启动恢复**或**缺失的原生接口**。
逐项状态见 `pass-d009-d013-items.json` 的 `offline_development` 与 `actual_checks_this_round`。

## 4. 建议执行顺序（提交协调者审核后实施）

1. **D009-3/4/5（LegacyLinework/BlackBox/EncryptedCoating）**：接口缺失，建议**本轮直接按 blocked 收尾**，
   仅保留证据与解除条件，不排原生。
2. **D009-2（CadMultipleConfigurations）**：输出不符，建议保持 blocked，等待上游/正式层赋值能力，不排原生。
3. **D009-1（CadSettings）**：接口完整，待原生启动恢复后一次性跑三支 CAD 原生用例。
4. **D013-1（Settings）**：解除条件是**正式查询返回非 null** 并取得实际设置/节点/许可/作业终态证据；
   原因（配置/许可/服务/版本）**尚未区分**，不得预先判定为配置问题。
5. **D013-2..5**：依赖 4，解除后逐条最小任务验收。

## 5. 需协调者注意的台账/证据路径问题

- `operations.csv` 中 `EXT-HPC.*` 的 `evidence` 列引用了 `docs/hpc.md`，但**主区无此文件**；
  实际文档为 `docs/topics/extensions/hpc.md`。属**台账路径笔误**，未擅自改台账，提请协调者核正。
- `EXT-HPC.NSCTrace/Tolerancing/GlobalOptimization/HammerOptimization` 台账 `execution_state=implemented`
  且 `blocked_reason` 为空，但原生用例实际是 **skip**（`已实现待验收`、`Completion count: 0`）。
  台账未记录该原生未验收状态，建议协调者按 preflight 证据补记，避免被读成"已验收"。

## 6. 未做 / 不做

- 不重复 `application_create` 原生启动（01/02/05 已有独立证据，本轮 `defer_native_startup_for_this_pass`）。
- 不做 180 s 复测、不改 HPC 偏好（属环境操作；且失败原因**尚未区分**，不应据此改配置）。
- 不提交 Git、不改公共台账/版本、不自行发行。

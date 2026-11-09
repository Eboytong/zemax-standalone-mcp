# D008 实施报告：两个默认文本报告的有类型入口与真实文本解析

- 开发组：**D008**（`development/tracking/development-groups.json`：9 项，本组前两项）
- 条目：`NS-04.PrescriptionDataSettings`、`NS-04.SurfaceDataSettings`
- worker：Gradium/D008 模块 worker；分支 `codex/d002-gradium`；起点 `34e1a184...`；源码 0.1.62
- 本轮范围：**默认报告**的有类型入口、真实文本解析、错误分层与身份校验。**完整选择范围（章节/面号）仍 blocked**
- 未执行原生；未改公共台账/schema/组顺序；未提交 Git

## 1. 正式接口依据（只读事实，未新增猜测选择器）

| 事实 | 依据 |
| --- | --- |
| 两项运行时设置对象均为 `ZemaxUI.ZOSAPI.Analysis.AS_Default`，实现空 `IAS_` 基类；属性仅 `Analysis/TheDataID/IsValid/IsActiveWindow/Parent` | `development/evidence/NS-04/runtime068-sequential/settings.json` |
| 静态接口面无 `IAS_PrescriptionData`/`IAS_SurfaceData`；`IAS_` 基类属性为空 | `development/evidence/BASE-01/probe/api-interfaces.json` |
| 无文档化 `ModifySettings` 键；`SaveTo` 导出的 CFG 18448 B 含 null 字节、无 ASCII 记号 | `runtime068-sequential/{modifysettings.txt,settings.json}` |
| 手册仅记录 UI 控件（Surface 面号）与 14 个章节名，不是 API 属性 | 手册 p950–952（`runtime068-sequential/surface-prescription.txt`） |
| 枚举名：`PrescriptionDataSettings` / `SurfaceDataSettings` | `BASE-01/inventory0*.json`（114/115） |

因此本轮只提供 **kind-only** 请求，不提供 `section`/`surface` 字段，不猜测 CFG 键。

## 2. 代码改动

### 2.1 新增（本任务自有）

| 文件 | 内容 |
| --- | --- |
| `src/zemax_mcp/native_text_reports.py`（新） | `PrescriptionDataReport`/`SurfaceDataReport`（kind-only）；`decode_native_text`；`split_sections`/`document_header`；`parse_prescription_report`/`parse_surface_data_report`；`parse_report`；`native_text_path`/`report_payload`（collector）；`run_text_report`（复用 `AnalysisJob` 生命周期） |
| `tests/unit/test_native_text_reports.py`（新，42 项） | 真实样本回归、身份校验、错误分层、collector、`run_text_report` 关闭路径、请求契约 |
| `tests/support/native_samples/*.txt`（3 个，逐字节 UTF-16LE 副本） | 真实原生报告样本（任务号见文件内注释） |

**真实样本来源（主项目证据目录，逐字节复制）**

| 样本 | 原生任务 |
| --- | --- |
| `prescription_data_20261108_native.txt`（12826 B） | `68ace1bed8d14c1cb569d97dbc5bfb09` |
| `surface_data_20261108_native.txt`（938 B） | `80c79fad920a4e9e9f337b10a6b9aa9f` |
| `surface_data_20261107_native.txt`（954 B） | `48596bf64aa34056a25e744999a48f20` |

### 2.2 共享补丁（最小，交集成负责人）

| 补丁 | 文件 | 行数 | 内容 |
| --- | --- | --- | --- |
| P1 | `analysis_models.py` | +1 导入、+1 成员 | `from .native_text_reports import PrescriptionDataReport, SurfaceDataReport`；`AnalysisRequest` 联合体插入两项 |
| P2 | `analyses.py` | +1 行注册、+3 行分派 | `ANALYSES.update(prescription_data='PrescriptionDataSettings',surface_data='SurfaceDataSettings')`；`if q.kind in {...}: run_text_report(self,q)` |

未改 `server.py`；未改 `backend.py`；未新增依赖。

### 2.3 解析行为（以真实报告为准）

- **章节识别**：列首 `title:` 行且标题命中"观测到的中文标题 + 手册英文名"表；**不要求 14 章节齐全**（真实报告缺 `multi_config_data`，属正常），缺项记入 `missing_documented_sections`（信息项，不作失败）。
- **未知标题保留**：非表内标题进入 `candidate_titles`，其原始行仍在 `lines`（如 `预测坐标 ABCD 矩阵`）。
- **报告身份**：处方报告必须标题为 `系统/详细数据`、`System/Detail Data` 或 `Prescription Data`，否则 `INVALID_RESULT_DATA`；**仅出现熟悉的章节名不足以通过**。
- **面号身份**：标题 `表面 N 数据概要` 的 N 与各表面光焦块 `面 M` 的 M 必须一致；**冲突即 `INVALID_RESULT_DATA`**，并把已解析结果放入 `details.partial`。
- **单位与数值**：`毫米` 等原文保留；数值同时保留 `value_text`（原始显示精度）与 float。
- **无摘要计算**：不计算哈希/摘要，只保留原生文本、来源路径、任务号与行号。

### 2.4 错误分层（复用既有码）

| 情形 | 码 | 附带信息 |
| --- | --- | --- |
| 无 `native_text` 产物 | `NO_RESULT_DATA` | `artifacts`、`native_messages` |
| 空文本 | `NO_RESULT_DATA` | `native_text`、`analysis_kind`、`native_messages` |
| 解码失败 | `INVALID_RESULT_DATA` | `native_bytes`、`native_prefix`(hex)、`native_text`、`native_messages` |
| 身份不符（标题/面号冲突） | `INVALID_RESULT_DATA` | `report_title`/`title_surface`+`power_surfaces`、`native_preamble`、`partial` |
| 文本读取失败 | `INVALID_RESULT_DATA` | `native_text`、`analysis_kind`、`native_messages`、`native_error` |
| 工厂未创建/设置回读失败 | `NATIVE_INTERFACE_UNAVAILABLE`/`SETTING_UNAVAILABLE` | 关闭路径先执行，`cleanup_warnings` 保留 |

**默认报告解析成功**与**完整选择范围验收**在结果中分开：`acceptance_scope='default_report_only'`、`selection_scope={status:'blocked',supported:'default_only',reason,unlock_condition}`。

## 3. 实际执行的检查（命令与回执）

```
C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe -B -X utf8 -m pytest \
  tests/unit/test_gradium_profile.py tests/unit/test_grin_profile.py \
  tests/unit/test_native_text_reports.py tests/unit/test_system_check.py -q -p no:cacheprovider
→ 101 passed in 0.71s
```
构成：Gradium 30 + GRIN 19 + 文本报告 42 + system_check 10。

单文件回执：`pytest tests/unit/test_native_text_reports.py` → `42 passed in 0.35s`。

覆盖要点（均有断言）：真实样本 14 章节与行数 217；两版表面样本 `surface=1`、`unit=毫米`、折射率行 `0.55000/1.0000000000`、光焦块面号 1；`多配置数据` 缺失不失败；未知标题保留；处方身份拒收（`系统数据` 标题 + 熟悉章节名）；表面面号冲突拒收并保留 `partial`；空文本/解码失败/读取失败/无产物 四种分层的码与附带信息；`run_text_report` 的设置回读失败关闭（`cleanup_warnings` 两种）、工厂为 None、成功路径 `analysis=True` 且 `selection_support='default_only'`。

## 4. Gradium 元数据修正（同一交付的第二线）

| 修正 | 结果 |
| --- | --- |
| `resolve_profile_path` 保留相对路径身份（不再截成 `candidate.name`） | 相对子目录实读结果：`source=…\Glasscat\custom\MCP_SUB.GRD`、`path_origin=relative`；裸文件名不再被当成有效替代（`unavailable`） |
| 绝对 GRD 仍以 Glasscat 为原生资源根 | `path_origin=absolute`、`native_resource_root=…\Glasscat`、`profile.source=…\elsewhere\MCP_ABS.GRD`、`path_note` 说明在资源根之外 |
| `family_metadata` 不再把所选 GRD 旁的 SGRIN 当作原生活动族文件 | 只读资源根：`family.source=…\Glasscat\SGRIN.DAT`、`reference_wavelength_um=0.58756`；即便同目录另有 `0.60000` 的 SGRIN 也不采用 |
| 声明性质显式标注 | `declaration='candidate'`、`native_binding='unconfirmed'`、`binding_basis` 说明"无原生回读确认所用族文件" |

对应新测试：相对子目录身份、绝对路径 + `native_resource_root`、族文件取自资源根（含不同目录不同参考波长的对照）、缺族/缺根返回 `unavailable`。

## 5. 原生作业（仅准备，见 `d008-reports-native-jobs.json`）

三条最小作业：默认处方报告、默认表面数据报告、（可选）多面模型下的默认报告对照。**当前 `application_create` 已有 01/02/05 三次 180 秒超时独立证据，属外部阻塞，本轮不启动**。

## 6. 状态

- `NS-04.PrescriptionDataSettings` / `NS-04.SurfaceDataSettings`：**默认报告入口与解析 = 已实现且有普通测试**；**完整选择（章节/面号）与采用值回读 = blocked**。
- 不申报 done；台账仍为 `blocked`，由协调者统一更新。
- 剩余解除条件：出现官方章节/面号选择接口或文档化 `ModifySettings` 键，并能可靠回读实际采用值（届时按 `IAS_Surface` 同款模式接线，并补原生对照）。
- 未关闭风险：真实样本仅来自单一模型（单配置、单面），多面/多配置的章节组合尚未离线覆盖；解析器对未知标题只做保留不做语义解释。
- 遗留：工作区临时目录 `tmpo9_m8vru/`（演示脚本产物）按要求保留，未清理。

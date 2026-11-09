# 集成报告：D008 默认文本报告 + Gradium 元数据（Gradium 工作区交付）

- 批次：D008（`NS-04.PrescriptionDataSettings`、`NS-04.SurfaceDataSettings`，默认报告 only）
- 来源工作区：`C:/Users/tonge/.codex/worktrees/zemax-p01-gradium/Zemax_MCP`（分支 `codex/d002-gradium`，起点 `34e1a18`）
- 来源报告：`.local/coordination/d008-reports-implementation-report.md`
- 主区集成方式：**按最小共享 hunk**，未复制整文件；`git diff 34e1a18` 生成补丁后应用（`analysis_models.py` 因偏振已占位改为两处手工插入）
- 本轮未执行原生启动；未改公共台账/版本；未提交 Git

## 1. 实际合入文件

### 1.1 新增（源侧自有，逐字节按路径复制）

| 文件路径 | 用途 | 采用动作 |
| --- | --- | --- |
| `src/zemax_mcp/native_text_reports.py`（22136 B） | 两 default 报告的有类型入口（`PrescriptionDataReport`/`SurfaceDataReport`，kind-only）、`decode_native_text`、`split_sections`/`document_header`、`parse_prescription_report`/`parse_surface_data_report`、`parse_report`、`native_text_path`/`report_payload`、`run_text_report`（复用 `AnalysisJob` 生命周期） | 新增合入 |
| `tests/unit/test_native_text_reports.py`（20815 B，42 项） | 真实样本回归、身份校验、错误分层、collector、`run_text_report` 关闭路径、请求契约 | 新增合入 |
| `tests/unit/test_gradium_profile.py`（18034 B；收集 31，30 通过 + 1 E1 工件项） | GRADIUM 曲线/边界/元数据普通校验 | 新增合入 |
| `tests/support/native_samples/prescription_data_20261108_native.txt`（12826 B） | 真实处方报告样本（原生任务 `68ace1bed8d14c1cb569d97dbc5bfb09`） | 新增合入 |
| `tests/support/native_samples/surface_data_20261108_native.txt`（938 B） | 真实表面数据样本（原生任务 `80c79fad920a4e9e9f337b10a6b9aa9f`） | 新增合入 |
| `tests/support/native_samples/surface_data_20261107_native.txt`（954 B） | 真实表面数据样本（原生任务 `48596bf64aa34056a25e744999a48f20`） | 新增合入 |
| `src/zemax_mcp/gradium.py`（11870 B） | 已审查的声明型 GRD/SGRIN 元数据：`glasscat_directory`（Glasscat 根）、`resolve_profile_path`（相对子目录保留身份 / 绝对 GRD 直读且仍报 Glasscat 根）、`family_metadata`（SGRIN `declaration='candidate'`,`native_binding='unconfirmed'`）、`resource_metadata`（never raises） | 新增合入（仅已审查范围） |
| `tests/support/gradium_reference.py`（18177 B） | `test_gradium_profile.py` 的**必需依赖**（`PROBE_RECORDS`/`load_probe_record`/`residual_report`/`boundary_hypotheses` 等），读取主区留存 `development/evidence/MA-01/probe63*/basis.json` | 新增合入（**批准清单未列，属被测文件必需依赖，特此标注**） |
| `scripts/probes/MA-01/gradium_e1_residuals.py`（3339 B） | 已批准的**离线** E1 残差复算探针（纯有理数回放留存 637-639 记录，无原生实例）；生成 `.local/gradium/e1-residuals.json` | 新增合入（离线，无原生启动） |

### 1.2 共享补丁（最小 hunk）

| 文件 | 合入内容 |
| --- | --- |
| `src/zemax_mcp/analysis_models.py` | ①`from .native_text_reports import PrescriptionDataReport, SurfaceDataReport`（接在 `system_check` 导入后）；②`AnalysisRequest` 联合体在 `SystemCheck` 后插入 `PrescriptionDataReport\|SurfaceDataReport`。**仅此两处**（偏振/Hologram/athermal 既有改动保持不动） |
| `src/zemax_mcp/analyses.py` | ①`ANALYSES.update(prescription_data='PrescriptionDataSettings',surface_data='SurfaceDataSettings')`（`@@ -61,0 +65 @@`）；②`grin_source_context` 内 Gradium 元数据接线（`@@ -333,0 +385,9 @@`，见下）；③`run_analysis` 分派 `if q.kind in {"prescription_data","surface_data"}: run_text_report(self,q)`（`@@ -484,0 +545,3 @@`） |

**②Gradium 元数据接线（`grin_source_context` 内，try/except 包裹，纯附加 provenance，绝不影响原 profile 查询）：**

```python
try:
    from .gradium import resource_metadata
    context['gradium']['resource_metadata']=resource_metadata(
        getattr(getattr(backend,'native',None),'application',None),
        context['gradium']['profile_file'],context['material'])
except Exception as exc:
    context['gradium']['resource_metadata']=dict(status='unavailable',reason=f'metadata unavailable: {exc}')
```

> 说明：这是"Gradium 元数据相关"交付（来源报告 §4）的必要接线 hunk，内容即 `gradium.py` 的 `resource_metadata` 调用。若协调者认为该 hunk 超出 `analyses.py` 两项 kind 注册+分派的授权，可单独回退本 hunk（`gradium.py` 与 `test_gradium_profile.py` 仍独立可用）。**特此提请审查。**

## 2. 新增测试文件的来源与回执（`test_native_text_report_lifecycle.py`）

| 项 | 内容 |
| --- | --- |
| 来源 | **非 Gradium 工作区交付**，为本轮在主区新写，用于满足"按任务公共生命周期已有断言补取消/失败关闭定向消费者覆盖，避免只测 `_start_task` 调用就声称完整原生关闭" |
| 文件 | `tests/unit/test_native_text_report_lifecycle.py`（4599 B，4 项） |
| 手法 | 使用**真实** `Backend._start_task` / `cancel_task` / `tick` / `_close_task_native`；仅伪造原生工具（`ReportTool`：`GetSettings/Apply/Terminate/IsRunning/WaitForCompletion/Close`），并 monkeypatch `imaging.new_analysis`、`analyses.scalar_settings`、`backend.get_system_settings` 三个非生命周期钩子 |
| 4 项 | ①`test_cancel_terminates_then_closes_through_the_shared_lifecycle`（cancel→`Terminate`→tick→`Close`，`cancelled`，`close_attempted=True`，`active=None`）；②`test_failure_after_start_closes_the_native_tool`（`WaitForCompletion` 抛错→`failed`→仍 `Close` 一次）；③`test_close_failure_keeps_warnings_and_requires_reconnect`（`Close` 返回 false→`cleanup_warnings` 保留、`requires_reconnect=True`）；④`test_cancel_is_not_reported_before_the_native_stop_is_confirmed`（仅 `cancelling`，未 `close_attempted`，`Close` 0 次，`active` 保留） |
| 实际运行 | `pytest tests/unit/test_native_text_report_lifecycle.py -q` → **4 passed**（XML `review-gradium-unit.xml` 内同类计数；本文件另计 4） |

## 3. 本轮实际检查（命令与 XML 回执，精确计数）

XML 目录：`.local/evidence/development/BASE-04/parallel-01/`

| 检查 | 命令 | 实际结果 |
| --- | --- | --- |
| D008/Gradium 四文件（101 集） | `pytest tests/unit/test_native_text_reports.py tests/unit/test_gradium_profile.py tests/unit/test_grin_profile.py tests/unit/test_system_check.py -q` | **101 collected：100 passed + 1 skipped**（`review-d008-gradium-101.xml`）。组成：42 + 31 + 19 + 9 |
| 合并定向（101+契约+生命周期） | `pytest <上四文件> tests/unit/test_contracts.py tests/unit/test_native_text_report_lifecycle.py -q` | **132 collected：131 passed + 1 skipped**（`review-gradium-integration.xml`） |
| E1 工件项复测 | 生成 `.local/gradium/e1-residuals.json` 后 `pytest "tests/unit/test_gradium_profile.py::test_e1_artifact_matches_support" -q` | **1 passed**（`review-d008-e1-artifact-retest.xml`） |

**skip 说明（如实记录，不写"101/132 全通过"）**：skip 项为 `test_e1_artifact_matches_support`，原因是主区初始**未生成** `.local/gradium/e1-residuals.json`。上文已用**已批准的离线探针**（`scripts/probes/MA-01/gradium_e1_residuals.py`，读取主区留存的 `development/evidence/MA-01/probe63*/basis.json`，无原生启动）生成该工件，随后**只复测该 skip 项**得 1 passed；其余已通过项未重复执行。

## 4. 源码 kind 计数（按实际读取）

| 指标 | 实际值 |
| --- | --- |
| `ANALYSES` 条目（analysis kind 数） | **124** |
| `AnalysisRequest` 联合体成员数 | **96** |
| 新增两 kind 已注册 | `prescription_data -> PrescriptionDataSettings`、`surface_data -> SurfaceDataSettings` |

D001 四入口保留、未受影响（`phase_aberration→PhaseAberration`、`polarization_ray_trace→PolarizationRayTrace`、`polarization_transmission→Transmission`、`fiber_coupling_settings→FiberCouplingSettings`，均在 `ANALYSES` 与联合体内）。

## 5. 仍缺（未验收，不改 done）

- **完整两报告章节/面号选择**：仍 blocked。接线层 `acceptance_scope='default_report_only'`、`selection_scope={status:'blocked',supported:'default_only',...}`；本机设置对象为 `AS_Default` 空 `IAS_` 基类，无文档化 `ModifySettings` 键，不猜 CFG 键。
- **原生验收**：**未执行**（`application_create` 有 01/02/05 三次 180 s 超时独立证据，属外部阻塞）。`run_text_report` 的原生读取仅在单元层用伪造工具验证。
- **Gradium 数值**：E1 仅完成**离线**残差回放（低阶 0..9 最大残差 2.16e-15 ≤ 2.22e-15 界；H-B 文本精度/系数序被否证），**原生 E3 行**（可加性、zmax 不变性、列波长归属）仍未做，属未验收。
- 真实样本仅来自单一模型（单配置、单面）；多面/多配置章节组合未离线覆盖。

## 6. 未合入（明确排除）

- Gradium 工作区 `analyses.py` 里**其他未批准 hunk**：无（本交付 `analyses.py` 仅上述 3 hunk）。
- `tests/native/test_gradium_*_live.py`（4 个原生用例）——未在本轮范围，留给原生恢复后。
- `tmpo9_m8vru/` 临时目录——按来源要求保留原样，未清理。
- D005 `image_viewers` 元数据（错误归属返工中）——**未合入**。

## 7. 风险 / 待办

- `tests/support/gradium_reference.py` 与 `scripts/probes/MA-01/gradium_e1_residuals.py` 超出字面批准清单，但前者是被测文件必需依赖、后者是任务明确批准且纯离线；已在 §1.1 标注。
- `grin_source_context` 的 Gradium 元数据接线 hunk 属授权边界，已在 §1.2 提请审查。
- schema 计数由协调者统一刷新（本轮未改 `tool_count`/`analysis_kind_count`；源码 kind 实际 124）。

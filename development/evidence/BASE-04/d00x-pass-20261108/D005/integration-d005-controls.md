# 集成报告：D005 图像查看器/分析与 N1/N2/N3 控制探针

- 来源工作区：`C:/Users/tonge/.codex/worktrees/zemax-p01-polarization/Zemax_MCP`（分支 `codex/d001-polarization`，基线 `34e1a18`）
- 集成方式：按路径逐文件复制（新增/覆盖），未改 `analyses.py`/`analysis_models.py` 的公开请求面
- 未执行原生；未全量；未提交 Git；未改发行；未清理临时目录
- 未合入仍在审查的 gradium STAR 分析/散射补丁

## 1. 实际合入文件（主区）

| 文件路径 | 来源状态 | 说明 | 采用动作 |
| --- | --- | --- | --- |
| `src/zemax_mcp/image_viewers.py`（22165 B） | 新增 | **内部** D005 helper：AnalysisIDM 映射、`settings_surface`、纠偏后 `MODIFY_SETTINGS`、`KEY_ATTRIBUTION`/`FOREIGN_PREFIXES`、`source_file_identity`、`bitmap_identity`/`sniff_bitmap_header`、`declared_scope(verified=False)`、三报告解析器 | 新增合入（**不接公开请求**） |
| `tests/unit/test_image_viewers.py`（18648 B，53 项） | 新增 | 文档 ID、键归属、未接产品模块守护、源身份、解析器对真实文本/非有限/形状不匹配等 | 新增合入 |
| `scripts/probes/D005/parse_saved_reports.py`（3419 B） | 新增 | 离线控制探针：解析 probe442 三份真实 UTF-16 报告，写 `d005-saved-report-parse.json` | 新增合入 |
| `scripts/probes/PO-01/probe_common.py`（8752 B） | 新增 | N1/N2/N3 探针公共离线夹具 | 新增合入 |
| `scripts/probes/PO-01/n1_settings_surface.py`（11276 B） | 新增 | N1 设置面探针 | 新增合入 |
| `scripts/probes/PO-01/n2_system_polarization.py`（6974 B） | 新增 | N2 系统偏振探针 | 新增合入 |
| `scripts/probes/PO-01/phase_aberration_reference.py`（9400 B，覆盖主区 4411 B） | 修改 | N3 相位像差离线参考（审查版，相对基线 +187/−66） | 覆盖合入 |
| `tests/unit/test_native_controls.py`（27790 B，41 项） | 新增 | N1/N2/N3 有界控制探针的离线普通测试（真实 `RunAnalysis`/`SystemPatch`/`parse_phase_aberration_text`，原生会话/工具用离线假件替代） | 新增合入 |

## 2. 边界与 D001 保留

- **保留 D001 四公开入口**：`phase_aberration→PhaseAberration`、`polarization_ray_trace→PolarizationRayTrace`、`polarization_transmission→Transmission`、`fiber_coupling_settings→FiberCouplingSettings` 均在 `ANALYSES` 与 `AnalysisRequest` 联合体内（实读 `ANALYSES=124`、联合体=96）。
- **不接公开请求**：`analyses.py` 源码不含 `image_viewers` 引用；`AnalysisRequest` 联合体不含 `LightSource`/`BitmapFileViewer`/`BeamFileViewer`/`PartiallyCoherentImage`/`ExtendedDiffractionImage`；`test_image_viewers.py::test_metadata_is_not_wired_into_product_modules` 守护通过。D005 helper 仅内部可用。

## 3. 实际检查（命令与结果）

XML：`.local/evidence/development/BASE-04/parallel-01/review-d005-controls.xml`

```
python -B -X utf8 -m pytest tests/unit/test_image_viewers.py tests/unit/test_native_controls.py \
  -q -p no:cacheprovider --junitxml=.local/evidence/development/BASE-04/parallel-01/review-d005-controls.xml
```
结果：**94 passed**（0 failed / 0 error / 0 skipped）
- `tests/unit/test_image_viewers.py`：**53 passed**
- `tests/unit/test_native_controls.py`：**41 passed**

**重放三真实报告（离线，无原生）**：
```
python -B -X utf8 scripts/probes/D005/parse_saved_reports.py
```
证据目录默认 `.local/evidence/development/CV-02/probe442-b005` 在主区**已存在**，无需迁移。结果（`application_created=false`）：
- `light_source` → `finite_conjugate_only`（该系综仅一条有限共轭提示，非可用数据；报告 40 B，UTF-16）
- `partially_coherent_image` → `incoherent`，`dimensions_match_header=true`，`cell_count=169`，`min=2.221e-07`，`max=1.0`
- `extended_diffraction_image` → `dimensions_match_header=true`，`cell_count=65536`，`min=0.001034`，`max=1.0`

回放产物：`.local/coordination/d005-saved-report-parse.json`（`application_created=false`）。

## 4. Durable 副本（已复制）

目录：`development/evidence/BASE-04/d00x-pass-20261108/D005/`
- `pass-d005-plan.md`（10012 B）
- `pass-d005-report.md`（7476 B）
- `pass-d005-items.json`（13840 B，6 项，均 `verified=false`）
- `d005-interface-correction.md`（5610 B）
- `d005-saved-report-parse.json`（3361 B，本轮重放结果）
- `final-report.md`（5469 B）
- `native-controls-review-report.md`（6582 B）

## 5. D005 六项状态（未验收，不改 done）

| 条目 | 状态 |
| --- | --- |
| WP-01.BeamFileViewer | verified=false（无 documented 键，仅 ZBF 树 `<pop>`） |
| CV-02.BitmapFileViewer | verified=false（仅图像窗口，0 数据表、无文本导出） |
| IM-01.GeometricBitmapImageAnalysis | verified=false（`IAS_GeometricImageAnalysis`，RGB 数据表） |
| CV-02.LightSourceAnalysis | verified=false（仅有限共轭提示） |
| CV-02.ExtendedDiffractionImageAnalysis | verified=false（1 数据表 + 文本报告） |
| CV-02.PartiallyCoherentImageAnalysis | verified=false（1 数据表 + 文本报告） |

## 6. 剩余风险 / 阻塞

- **原生全部未运行**：`application_create` 三次 180 s 超时（`development/evidence/BASE-04/runtime-phase-environment-20261108.md`）；`verified` 置真需同时满足输入身份、设置实际采用、有效结果/参考、分页与生命周期四类条件。
- 三项无 documented 键（Light Source / Bitmap File Viewer / Beam File Viewer）只能声明"无可写选择面"，不得按名称联想补键。
- 未提交 Git、未改公共台账/版本/tracking；`pytest-of-tonge/` 残留按要求未清理。
- worker 最新通过数按实际：**94**（image_viewers 53 + native_controls 41）。

# D001/D005 最终交付报告（runtime 合入用）

- 日期：2026-11-08
- 工作单元：D001偏振、透射与光纤耦合（模块 worker）
- 分支：`codex/d001-polarization`，基线 `34e1a18494015c2b383ec700b958015020b660fe`
- 本次范围：三处文案/事实修订 + 受影响测试 + 交付清单；未创建 OpticStudio 应用、未跑全量、未提交 Git、未清理临时目录

## 1. 本轮三处修订（已完成）

| # | 位置 | 修订前 | 修订后 |
| --- | --- | --- | --- |
| 1 | `scripts/probes/PO-01/n1_settings_surface.py` 模块 docstring | "raw bytes and their digest are kept" | 删除 digest 表述，改为"保存文件本身留在磁盘作为证据，记录只保留路径、字节数、编码身份与短字节前缀" |
| 2 | `src/zemax_mcp/image_viewers.py` 开头 + `settings_surface` | "The others instantiate AS_Default …, so their dialog controls have no API surface" | 改为**observed/unconfirmed**：AS_Default 只是所探构建上的观测（附证据路径 `CV-02/probe442-b005/probe.json`、`CV-02/bitmap-viewer-repeat-20261108/probe.json`），不推断为所有构建永久无 API；`settings_surface` 新增 `api_surface_status`（`observed_confirmed` / `observed_unconfirmed`）与 `evidence` 字段 |
| 3 | `.local/coordination/pass-d005-report.md` §7 | "任一项拿到原生回执后即可把该项 verified 置真" | 改为四类**并列门槛**：输入身份（容器/数值语义/波长归属/像素标定）＋设置实际采用（写入后回读一致，无 documented 键者只能记"无可写选择面"）＋有效结果/参考（维度统计或容差内一致）＋分页与生命周期（游标严格前进、行数一致、终态明确、取消与断开回执确认） |

辅助约束：`image_viewers` 与 `probe_common` 仍为内部/离线资产——`image_viewers` 未被任何产品模块 import（守护测试 `test_metadata_is_not_wired_into_product_modules`），`probe_common` 只被三个探针引用；本轮未新增任何公开契约或请求模型。

## 2. 实际运行的检查（准确数量）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 受影响两文件（本轮） | `python -B -m pytest tests/unit/test_image_viewers.py tests/unit/test_native_controls.py -q -p no:cacheprovider` | **94 passed in 1.50s** |
| 其中 `test_image_viewers.py` | 同上（分项） | 53 passed |
| 其中 `test_native_controls.py` | 同上（分项） | 41 passed |
| 语法编译（探针四文件） | `python -B -m py_compile scripts/probes/PO-01/*.py` | 通过 |
| JSON 有效性 | `pass-d005-items.json`、`d005-saved-report-parse.json` | 均可解析 |
| 本会话较早一轮（非本轮）组合套件 | D001 四解析 + native_controls + polarization + transmission_fan + image_viewers | 220 passed in 1.96s（此后仅改探针脚本/探针测试/文档与两处 docstring，未触及产品逻辑） |

未运行：原生探针（N1/N2/N3 仍 `ready_not_run`）、全量测试、任何 OpticStudio 应用。

## 3. 文件清单

### 本轮修改

- `scripts/probes/PO-01/n1_settings_surface.py`（docstring 去 digest 表述）
- `src/zemax_mcp/image_viewers.py`（docstring 观察限定 + `settings_surface` 增加状态/证据字段）
- `tests/unit/test_image_viewers.py`（断言 `api_surface_status` 与 `evidence`）
- `.local/coordination/pass-d005-report.md`（§7 四类门槛）
- `.local/coordination/pass-d005-items.json`（`delivery_report` 指针、`text_revision_run` 计数）
- `.local/coordination/final-report.md`（本文件）

### 本分支累计新增

- `src/zemax_mcp/image_viewers.py`（D005 共享补丁，未接入产品路径）
- `src/zemax_mcp/polarization_topics.py`（D001 四专题）
- `scripts/probes/D005/parse_saved_reports.py`（D005 离线控制探针）
- `scripts/probes/PO-01/probe_common.py`、`n1_settings_surface.py`、`n2_system_polarization.py`
- `tests/unit/test_phase_aberration.py`、`test_polarization_ray_trace.py`、`test_polarization_transmission.py`、`test_fiber_coupling_settings.py`、`test_native_controls.py`、`test_image_viewers.py`
- `.local/coordination/{pass-d005-plan.md, pass-d005-items.json, pass-d005-report.md, d005-interface-correction.md, d005-saved-report-parse.json, native-controls-review-report.md, native-controls-plan.md, native-controls-report.md, native-jobs.json, pass-d001-items.json, plan.md, implementation-report.md}`

### 本分支累计修改

- `src/zemax_mcp/analyses.py`（+13 行，四个专题命令接线）
- `src/zemax_mcp/analysis_models.py`（+2/−1）
- `scripts/probes/PO-01/phase_aberration_reference.py`

未触碰：公共台账、schema、batch 文件、其他 worker 的文件；`pytest-of-tonge/` 未清理（按要求保留）。

## 4. 剩余风险与阻塞

1. **原生验收全未运行**：`application_create` 三次 180 s 超时（证据 `development/evidence/BASE-04/runtime-phase-environment-20261108.md`），D5-B1…D5-B6 与 N1/N2/N3 均 `not_run`。
2. D005 六项 `verified` 全为 `false`；须按报告 §7 四类门槛逐项取证后才可置真。
3. `AS_Default` 结论只对所探 24.2 构建成立，已标注 `observed_unconfirmed`；目标构建上的原生反射可能改变该结论。
4. 无 documented 键的三项（Light Source、Bitmap File Viewer、Beam File Viewer）只能声明"无可写选择面"，不得按名称联想补键。
5. 本轮仅验证离线契约与失败/超时/分页/关闭路径，不代表原生行为已验收。

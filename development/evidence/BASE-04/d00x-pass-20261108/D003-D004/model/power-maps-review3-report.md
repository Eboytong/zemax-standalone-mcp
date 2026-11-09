# Power Maps 探针：第三轮审查修正报告

条目：`CV-02.PowerFieldMapSettings`、`CV-02.PowerPupilMapSettings`，均维持 `implemented`，`zero_interpretation` 保持 `unresolved_native_zero_semantics`，`native_ring_validity` 保持 `'unavailable'`。
**本轮未运行原生、未改产品代码/合同/schema/台账/批次、未提交。** MaterialModel 与 D003 全部交付原样保留。

## 1. 审查项与落实

| # | 审查意见 | 落实 |
| --- | --- | --- |
| 1 | 缺离线契约测试（真实 `RunAnalysis`/`BatchRays` 校验、`Backend._page_task_result` 分页合同、FakeBackend 跑探针主路径） | 新增 `tests/unit/test_power_probe_contracts.py`，17 项 |
| 2 | E3 直接对 `position+direction` 求差，追迹失败为 None 会抛 TypeError 覆盖诊断 | 新增 `coordinate_delta()`：缺坐标时记 `evaluable=false`、`reason='trace_coordinates_missing'`、`missing=[...]` 及双方原始 `error_code/vignette_code/position/direction`，不求差 |
| 3 | `delta` 只查 None，未查有限性 | 改为 `any(v is None or not math.isfinite(v))`，并保留 `base_raw/case_raw/base_state/case_state` |
| 4 | `power-maps-native-jobs.json` 的 E2 `fields` 仍只有 (0,0) | 同步为 `[{x:0,y:0},{x:2,y:2}]`，并加 `fields_note` 说明用途 |

## 2. 探针修正细节

### 2.1 E3 映射评估（`power_asymmetric_aperture018.py`）

```python
def coordinate_delta(base, row):
    sides = dict(base=..., case=...)
    missing = [name for name, side in sides.items()
               if side["position"] is None or side["direction"] is None]
    if missing:
        return dict(px=..., py=..., evaluable=False, reason="trace_coordinates_missing",
                    missing=missing, max_abs_diff=None, unchanged=None, **sides)
    ...
```

- 基线自身也走 `coordinate_delta(row, row)`，保证逐点记录结构一致（差值恒 0、`unchanged=True`）。
- 每个 case 增加 `mapping_evaluable`；`mapping_unchanged` 改为 `all(m["unchanged"] is True ...)`，缺坐标不会被误记为"未变化"。
- `measure()` 不再用 `zip(strict=True)`：追迹返回行数不足时按点补 `position/direction=None` 的占位行并记 `trace_row_count_mismatch`，避免 `ValueError` 覆盖诊断。

### 2.2 E3 数值差值

`delta()` 对 Power 与 EFL **分别**判定；任一侧非有限即 `available=False` 并保留 `case_state`（`native_query_failed` / `non_finite`），不再相减。

### 2.3 E2/E3 结果读取（上一轮已修，本轮由测试固定）

- 优先读任务自带 JSON 产物（`Path(path).stem == task_id`，与 `tests/support/native.py:23-25` 的 `Evidence.finish` 同法）；
- 回退时显式区域分页 `grid=0, x_start=1, y_start=1, width=1, height=1`，读**单数键** `result["grid"]["values"][0][0]`；
- 记录 `result_source`（`artifact_json` / `paged_inline+grid_page`）与 `grid_center_matches_row`。

## 3. 新增离线契约测试（17 项，`tests/unit/test_power_probe_contracts.py`）

### 3.1 真实请求模型

| 测试 | 断言 |
| --- | --- |
| `test_run_analysis_accepts_power_field_map` | 真实 `RunAnalysis` 接受 `power_field_map` |
| `test_power_field_map_requires_positive_widths` | 宽度为 0 → `ValidationError` |
| `test_batch_rays_direct_mode_rejects_normalized_fields` | **旧 E3 写法**：`input_mode="Direct"` + `hx/hy/px/py` → `ValidationError`（`models.py:557`） |
| `test_batch_rays_normalized_mode_accepts_probe_rays` | 修正后 `Normalized` 通过 |

### 3.2 真实产品前置条件（`run_power_map`，非复制逻辑）

| 测试 | 断言 |
| --- | --- |
| `test_zero_field_scale_is_rejected_by_real_run_power_map` | `fields=[(0,0)]` → `PRECONDITION_FAILED`，`x_scale=0,y_scale=0`（`power_maps.py:71`） |
| `test_off_axis_field_passes_the_precondition` | `fields=[(0,0),(2,2)]` 通过前置，到达 `_composite`（哨兵异常） |
| `test_scan_wider_than_field_extent_is_rejected` | 宽度 8 > 尺度 2 → `INVALID_ARGUMENT`（`power_maps.py:72`） |

这三项用 `StubBackend` 直接调用**产品函数**，因此 E2 的 fields 修法是被产品代码验证的，而不是被测试复述。

### 3.3 真实 `Backend._page_task_result` 分页合同

| 测试 | 断言 |
| --- | --- |
| `test_default_paging_strips_grid_values` | 默认分页后 `grids[0]` 无 `values`、`grid_data_in_artifacts=True`，`["values"]` 抛 `KeyError`（固定该陷阱） |
| `test_region_paging_returns_single_centre_value` | `grid=0,x_start=1,y_start=1,width=1,height=1` → 返回单数键 `grid`，`values==[[6.814355276657183]]`，`next_x=next_y=2` |
| `test_grid_index_out_of_range_is_explicit` | `grid=3` → `INDEX_OUT_OF_RANGE` |

### 3.4 FakeBackend 执行两份探针主路径

`FakeBackend` 的 `get_task_result` **调用真实 `Backend._page_task_result`**，只伪造原生响应。

| 测试 | 覆盖 |
| --- | --- |
| `test_e2_probe_reads_full_artifact` | artifact 路径；`fields` 回读为 `[(0,0),(2,2)]`；中心值与行值一致；gate 记录 |
| `test_e2_probe_falls_back_to_grid_page` | 无 artifact → 默认分页无 values → 区域分页回退，`result_source='paged_inline+grid_page'` |
| `test_e2_probe_uses_four_radii_and_records_close_receipt` | 四个半径、`active_task_after_shutdown=False`、回执 `native.closed=true` |
| `test_e3_probe_records_unavailable_efl_and_failed_ray` | 追迹失败行（`error_code=1`，坐标 None）→ `evaluable=False`、`reason` 正确、**不抛 TypeError**；健康点仍 `evaluable=True`（6 个） |
| `test_e3_probe_keeps_missing_efl_as_state_not_exception` | EFL 查询抛错 → `available=False, case_state='native_query_failed'`；NaN → `'non_finite'`；Power 与 EFL 互不牵连 |
| `test_e3_probe_reads_aperture_from_properties` | 孔径读 `properties.aperture`，`x_decenter=3.0` |
| `test_e3_probe_writes_anchors_with_probe_metadata` | `anchors.json` 的 `evidence_only`、`single_variable`、四例 id |

## 4. 实际执行的检查与结果

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 新增离线契约测试 | `python -B -m pytest tests/unit/test_power_probe_contracts.py -q -p no:cacheprovider` | **17 passed** |
| Power Map 既有普通测试 | `python -B -m pytest tests/unit/test_power_maps.py -q` | **27 passed** |
| 合并运行 | 同上两文件 | **44 passed in 1.06s** |
| 两份探针编译 | `python -B -m py_compile` | 均 ok |
| `git status` | — | 无产品代码改动 |

首次运行有 4 项失败，均为**测试自身**问题（`StubBackend` 缺 `native.api`、区域分页 `next_x` 期望写成 None、`cleanup_error` 键仅在异常时存在、基线 mapping 结构不一致），已逐项修正后 17/17 通过；探针无失败项。

## 5. 状态与剩余风险

- 两条目仍 `implemented`；`zero_interpretation`、`native_ring_validity` 未变。
- E2/E3 仍**未执行原生**：`application_create` 180 s 超时未解除。
- 测试只证明"探针按合同请求与读取"，不证明原生数值或环语义；`evidence_only` 未变。
- FakeBackend 的原生响应是伪造的，真实 `POWF/POWP` 行为仍需原生作业确认。
- 机械/边界：`x_field_width=2` 与 `fields=(2,2)` 的相容性由产品前置检查保证（1 ≤ 2），若现场改用 Radial 归一化仍成立（2.828）。

## 6. 工作区遗留物（已知，不清理）

- 工作区根目录存在 `pytest-of-tonge/`（pytest 临时目录，来自本轮与上一轮的普通测试运行）。
- 依本轮指示**保留**该目录、**跳过清理**，且不重试先前被拒绝的删除命令。
- 该目录只含测试临时文件（`task*.json`、`anchors.json` 等），不含源码或产品资产；未纳入 Git（`git status` 显示为未跟踪），不影响任何交付物。
- 后续如需清理，应由协调者或用户在确认后统一处理。

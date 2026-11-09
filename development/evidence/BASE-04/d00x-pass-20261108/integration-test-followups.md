# 集成报告：后续测试补丁组（test-followups）

- 本组为三条已审查小补丁，均按最小改动落地；未执行原生、未提交 Git、未改发行/版本、未清理临时目录。
- 新的 STAR/散射源补丁仍在审查，**未合入**。

## 1. 实际合入文件

| 文件路径 | 来源 | 内容 | 采用动作 |
| --- | --- | --- | --- |
| `tests/native/test_glass_map_live.py`（6400 B） | material-reports 工作区 `C:/Users/tonge/.codex/worktrees/zemax-p01-material-reports/Zemax_MCP` | 大小写归一（`catalog_name.upper()==report_name.upper()`）、真实 missing 走显式断言失败、**移除旧 xfail**（注释明写"never an xfail reason"） | 按路径覆盖合入 |
| `tests/support/analysis_scenarios.py` | gradium 工作区（仅 2 条 SPECIALIZED） | 仅新增 `prescription_data`、`surface_data` 两条 SPECIALIZED 条目；其余共享 hunk（含 6 条 STAR 条目）**不复制** | 最小编辑合入 |
| `tests/native/test_native_text_reports_live.py`（2621 B，新） | gradium 工作区 | 两项准备用例 `test_prescription_default_report`（D008-R1）、`test_surface_default_report_identity`（D008-R2），均 `@pytest.mark.zemax` | 新增合入 |

**关键点**：`cooke_request` 含 `elif kind.startswith('surface_') ...: q['surface']=1`，会把 `surface_data` 误注入不存在的 `surface` 参数；把 `surface_data` 放入 `SPECIALIZED` 后，`test_analysis_scenarios.py` 的参数化 `sorted(set(ANALYSES) - set(SPECIALIZED))` 会将其排除，从而不经过 `cooke_request`，避免伪造字段。

**未复制**：`analysis_scenarios.py` 中 `star_align_check`/`star_sys_viewer`/`star_2d_def_plot`/`star_perf_change`/`star_index_vs_temp`/`star_inspect_fea` 等 6 条 STAR 条目（连同对应 `test_star_analysis_live.py` 属另一审查中的 STAR/散射补丁）。

## 2. 实际检查（命令与准确结果）

XML：`.local/evidence/development/BASE-04/parallel-01/test-followups.xml`

```
python -B -X utf8 -m pytest tests/unit/test_analysis_scenarios.py tests/unit/test_material_reports_reference.py \
  -q -p no:cacheprovider --junitxml=.local/evidence/development/BASE-04/parallel-01/test-followups.xml
```

结果：**85 passed**（0 failed / 0 error / 0 skipped）
- `tests/unit/test_analysis_scenarios.py`：**74 passed**
- `tests/unit/test_material_reports_reference.py`：**11 passed**

```
python -B -X utf8 -m pytest tests/native/test_glass_map_live.py tests/native/test_native_text_reports_live.py --collect-only -q
```

结果：**4 tests collected**（未执行，未原生）：
- `tests/native/test_glass_map_live.py::test_glass_map_native_catalog_points_and_lifecycle`
- `tests/native/test_glass_map_live.py::test_glass_map_selected_catalog_identity`
- `tests/native/test_native_text_reports_live.py::test_prescription_default_report`
- `tests/native/test_native_text_reports_live.py::test_surface_default_report_identity`

## 3. 剩余 native 条件（未验收）

- 上述 4 个 native 用例均需 `--run-zemax` 与可用原生会话；本机 `application_create` 有 01/02/05 三次 180 s 超时独立证据，属外部阻塞，**本轮不启动**。
- `test_glass_map_live.py`：需原生 GlassMap 目录点位与所选目录身份对照（大小写归一、真实 missing 必须失败而非 xfail）。
- `test_native_text_reports_live.py`：需 Cooke 40° 场模型上 `prescription_data`/`surface_data` 的 kind-only 默认报告成功、`acceptance_scope='default_report_only'`、`selection_scope.status='blocked'`、任务 `succeeded` 且 `close_attempted`、前后 `get_surfaces` 不变。完整章节/面号选择仍 blocked。

## 4. 边界

- 未全量跑测试；未执行原生；未 Git 提交/发行；未清理临时目录（如 `tmp...`/`tmpo9_m8vru` 保留）。
- schema 计数由协调者统一刷新。

# 集成报告：D003/D004 Power Map 与 Pickup/Solve 离线控制探针

- 来源工作区：`C:/Users/tonge/.codex/worktrees/zemax-p01-material-model/Zemax_MCP`（分支 `codex/d002-material-model`，基线 `34e1a18`）
- 集成方式：按路径逐文件复制（全部新增，不改生产代码）
- **不改生产 PowerMap/solve 语义**：未改 `src/zemax_mcp/power_maps.py`、`analysis_models.py`、求解/取回逻辑，仅新增离线探针脚本与合同测试
- **不改原门槛**：既有零值/正性/扫描范围等门槛原样保留
- 未执行原生；未全量；未提交 Git；未改发行；未清理临时目录

## 1. 实际合入文件（主区，5 个）

| 文件路径 | 大小 | 说明 |
| --- | --- | --- |
| `scripts/probes/ED-02/pickup_solve_adoption018.py` | 13153 B | E1 pickup/solve 采用探针：两主程序合同、三路回读、追迹目标 `total-1`、清理与错误分离 |
| `scripts/probes/CV-02/power_radius_sweep018.py` | 10958 B | **E2**（任务旧名 `power_aperture_vignetting018.py` 不存在，按实际文件名定位为半径扫描探针）：四半径 50/1e3/1e6/1e9、全量产物读取与 grid 分页回退、close 回执 |
| `scripts/probes/CV-02/power_asymmetric_aperture018.py` | 13089 B | **E3** 非对称孔径探针：EFL 缺失/失败光线记录为状态而非异常、从属性读孔径、锚点写入 |
| `tests/unit/test_pickup_probe_contracts.py` | 11469 B | 9 项合同测试（E1） |
| `tests/unit/test_power_probe_contracts.py` | 16114 B | 17 项合同测试（E2/E3 + RunAnalysis/BatchRays/paging 合同） |

> 文件名说明：任务所述 `power_aperture_vignetting018.py` 在工作区实际不存在；`scripts/probes/CV-02/` 下实际为 `power_radius_sweep018.py`（E2）与 `power_asymmetric_aperture018.py`（E3）。`test_power_probe_contracts.py` 内以 `load_probe("power_radius_sweep018.py")` / `load_probe("power_asymmetric_aperture018.py")` 加载，确认 E2/E3 对应关系。未合入未请求的 `power_radius_sweep` 额外变体/`lde_fill_solve_probe.py`。

## 2. 已审查要点（与实现一致）

- **两主程序合同**：E1 走真实 `BatchRays`/`SystemPatch`；E2/E3 走真实 `PowerFieldMap`/`run_power_map`/`RunAnalysis`，并复用真实 `Backend` 分页。
- **三路回读**：pickup 采用判定区分"从未采用 / 更新后采用"，并记录三路回读与活动状态。
- **追迹目标 `total-1`**：`test_probe_traces_to_image_surface_not_surface_one` 守护。
- **分页**：E2 全量产物读取 + 无全量时回退 grid 页（`test_e2_probe_reads_full_artifact` / `test_e2_probe_falls_back_to_grid_page`）。
- **非有限/缺坐标**：解析器拒非有限值、形状/像素数不匹配；E3 把缺失 EFL 与失败光线记录为状态，不抛异常。

## 3. 实际检查（命令与结果）

XML：`.local/evidence/development/BASE-04/parallel-01/review-d003-power-pickup.xml`

```
python -B -X utf8 -m pytest tests/unit/test_pickup_probe_contracts.py \
  tests/unit/test_power_probe_contracts.py tests/unit/test_power_maps.py \
  -q -p no:cacheprovider --junitxml=.local/evidence/development/BASE-04/parallel-01/review-d003-power-pickup.xml
```
结果：**53 passed**（0 failed / 0 error / 0 skipped）
- `tests/unit/test_pickup_probe_contracts.py`：**9 passed**
- `tests/unit/test_power_probe_contracts.py`：**17 passed**
- `tests/unit/test_power_maps.py`：**27 passed**

> 计数口径：文档旧记 5/17/26 与本轮实际收集不同；**以本次真实结果为准：9 / 17 / 27，合计 53**。

## 4. Durable 副本（已复制）

目录：`development/evidence/BASE-04/d00x-pass-20261108/D003-D004/model/`
- `power-maps-review3-report.md`（7803 B）
- `d003-pickup-implementation-report.md`（6311 B）
- `pass-d003-d004-plan.md`（12369 B）
- `pass-d003-d004-report.md`（7452 B）
- `pass-d003-d004-items.json`（16813 B）
- `solve-extensions018-scope.json`（5496 B）
- 相关 nativejobs 清单：`d003-pickup-native-jobs.json`（4791 B）、`power-maps-native-jobs.json`（7792 B）、`native-jobs.json`（6661 B）

## 5. 剩余风险 / 阻塞

- **全部原生未运行**：`application_create` 三次 180 s 超时（`development/evidence/BASE-04/runtime-phase-environment-20261108.md`）。探针仅离线合同验证，原生验收（真实 OpticStudio 下运行 E1/E2/E3）仍未完成，条目不置 done。
- 生产 PowerMap/solve 语义与门槛均未改动；若后续需合入生产改动须另行审批。
- 未提交 Git、未改公共台账/版本/tracking；临时目录按要求未清理。

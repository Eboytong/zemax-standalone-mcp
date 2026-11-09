# ED-02 SurfacePickup — parallel-02 离线集成记录

- 日期：2026-11-08
- 主仓：`C:\Users\tonge\Desktop\Zemax_MCP`
- 导入来源（实测）：`PYTHONPATH=C:\Users\tonge\Desktop\Zemax_MCP\src` → `zemax_mcp.__file__=…\Zemax_MCP\src\zemax_mcp\__init__.py`
- 性质：**离线集成 + 普通定向测试，非原生验收**；未启动 OpticStudio。

## 1. 实施计划（协调者已逐函数审查批准）

集成 polarization rev3 的两份新增文件（24 项新 helper 检查；worker 工作树 75 项通过）；**保留旧 `pickup_solve_adoption018.py` 与旧合同测试，不覆盖**；将 worker 的 `pickup-native-jobs.json` 保留到主仓 `.local/coordination/parallel-02/` 作为 **prepared_not_executed** 作业。

## 2. 实际修改（主仓）

- **新增** `scripts/probes/ED-02/pickup_adoption_helper.py`（29667 B）：五读回时刻 × 五字段、source 变更联动、两次 save/reload 往返、pre-check 与 native-partial 失败恢复；adoption 与 complete 两层分离、strict close、失败/意外成功皆回滚。
- **新增** `tests/unit/test_pickup_adoption_helper.py`（21052 B）：**24 项 helper 检查**（finalize 缺恢复阻止 complete、strict close、失败/意外成功皆恢复、rows 结构/索引/计数/有限坐标/零 error+vignette 等）。
- **新增** `.local/coordination/parallel-02/pickup-native-jobs.json`（6303 B）：`status="prepared, NOT executed; native gate still closed (application_create 180 s timeout)"`，含两作业与 close_conditions/interpretation_rules。
- **保留（未覆盖）**：`scripts/probes/ED-02/pickup_solve_adoption018.py`（13153 B）、`tests/unit/test_pickup_probe_contracts.py`（11469 B，旧合同，9 用例）。

## 3. 请求 / 参数 / 原容差

- `JOB-ED02-P01-ChipZone`：surface 2、cell `chip_zone`、source_surface 1、source_value 0.5、target_start 0.2、source_after 0.7；scale=1.25（SupportsScale 时）、offset=0.05（SupportsOffset 时）。
- `JOB-ED02-P02-MechanicalSemiDiameter`：surface 2、cell `mechanical_semi_diameter`、source_surface 1、source_value 5.5、target_start 5.2、source_after 6.0。
- moments：`immediate` / `after_update_status` / `after_ray_trace` / `after_save_reload` / `after_source_change` / `after_save_reload_post_linkage`。
- 比较口径：参数 `PARAM_TOL=1e-12`；rows 结构/索引/计数/有限坐标/零 error+vignette；`native.closed is True`、`forced is False`、`native.error` 空、任务终态、无 cleanup_error 的 **strict close**。

## 4. 单次主仓联合定向普通测试

```powershell
cd C:\Users\tonge\Desktop\Zemax_MCP
$env:PYTHONPATH='C:\Users\tonge\Desktop\Zemax_MCP\src'
.\.venv\Scripts\python.exe -B -X utf8 -m pytest `
  tests/unit/test_material_model_reference.py tests/unit/test_pickup_adoption_helper.py `
  tests/unit/test_pickup_probe_contracts.py tests/unit/test_modeling.py `
  tests/unit/test_extended_solves.py tests/unit/test_solve_support.py `
  -q -p no:cacheprovider `
  --basetemp=.local\pytest-tmp\ed02-p02-20261108180236 `
  --junitxml=.local\evidence\development\ED-02\parallel-02\integrated-units.xml
```

- 结果：**183 passed / 0 failed / 0 errors / 0 skipped**。XML：`.local/evidence/development/ED-02/parallel-02/integrated-units.xml`。
- 本文件用例数：`test_pickup_adoption_helper.py` = **24**；旧合同 `test_pickup_probe_contracts.py` = **9**（保留生效）。
- HPC 45 / 启动 38 已通过且未改，**沿用不重复**。

## 5. 准备未执行的原生范围

`pickup-native-jobs.json` 中两作业（`JOB-ED02-P01-ChipZone`、`JOB-ED02-P02-MechanicalSemiDiameter`）**未执行**；native gate 关闭（`application_create` 180 s 超时未解）。两作业严格串行、独占单实例，仅由 runtime 执行。

## 6. 缺口与解除条件

- 缺口：无原生运行，`adoption_passed`/`complete` **未原生证明**；failure recovery 需真实触发并恢复（无重复失败则记 `failure_recovery_not_exercised`，仍回滚，不伪造）；意外成功也回滚并记 `available=False`。
- 解除条件：`application_create` 可用且**两进程恢复门槛通过**后，runtime 串行执行两作业，产出 `adoption_passed` 且 `complete=True`（strict close receipt）。
- 终态：SurfacePickup（ChipZone / MechanicalSemiDiameter）保持 **blocked**；本轮完整计数 **0 新增**。离线测试不代表原生成功。

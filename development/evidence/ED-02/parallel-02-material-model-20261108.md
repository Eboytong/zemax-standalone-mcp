# ED-02 MaterialModel — parallel-02 离线集成记录

- 日期：2026-11-08
- 主仓：`C:\Users\tonge\Desktop\Zemax_MCP`
- 导入来源（实测）：`PYTHONPATH=C:\Users\tonge\Desktop\Zemax_MCP\src` → `zemax_mcp.__file__=C:\Users\tonge\Desktop\Zemax_MCP\src\zemax_mcp\__init__.py`
- 性质：**离线集成 + 普通定向测试，非原生验收**；未启动 OpticStudio。

## 1. 实施计划（协调者已逐函数审查批准）

集成 material-model worker 最新收尾版：正式 physical-d 的 `build_gates` + 两条反例测试、纯函数 `solve_contract.py`、`close` 严格判定。**保留主仓既有成果，不回退新版 physical-d / closed 修正，不整包移入其他分支 `src/` 或报告目录。** 先读 worker 最新报告/XML 确认 physical-d 补充已收尾（phase2 报告 §5、XML 105 passed 含两条反例）再拷贝。

## 2. 实际修改（主仓，3 个文件）

- **新增** `scripts/probes/D002-MODEL_GLASS/solve_contract.py`：`SOLVE_PARAM_KEYS`（index_nd/abbe_vd/dpgf/vary_index/vary_abbe/vary_dpgf）、`solve_actual(surface)`、`solve_readback_checks`（`_match` 严格：bool 仅真 bool 相等；数值须可转 float 且 `math.isfinite`；rtol=1e-9/atol=1e-12）、`close_receipt_verdict`（严格 `native.closed is True AND forced is False AND native.error 空`，缺 `forced` 即 fail）、`session_closed`（回执通过 + 无活动任务 + 无 cleanup_error；不从 disconnect 返回推关闭）。
- **补丁** `scripts/probes/D002-MODEL_GLASS/model_glass_control018.py`（+71/−13，替换旧内联 gate 与 `closed=True` 为严格判定）：新增 `build_gates(direct, model)` —— **Nd 主门槛取物理 d=`line_positions(...,PHYSICAL_LINES)["d"]`（.5875618）**，四位经典 d（.5876）另存 `nd_classic` 诊断；Vd 分 `vd_physical`(主) 与 `vd_classic`(诊断)；`formal_convention="physical"`；`acceptance_passed` 仅基于正式 Nd/Vd + readback + diagnostics。`disconnect` 仅置 `disconnect_returned=True`，`finally` 内由 `session_closed(close_receipt_verdict, active_task_after_shutdown, cleanup_error)` 计算 `closed`。
- **扩测** `tests/unit/test_material_model_reference.py`（+119/−0，纯新增）：六字段提取/回读比对、四舍五入 Abbe 失配标记、非 model 单元、close 严格、`_match` 严格与有限数值、`session_closed`（含 cleanup 失败）、`build_gates` 物理/经典双反例（物理匹配→主通过；经典失配→诊断失败；经典匹配而物理失配→主失败、诊断通过）。

主仓其他既有文件未覆盖/未回退。

## 3. 请求 / 参数 / 原容差

- 请求：`material_model` 单变量矩阵 `BASELINE_MODEL=dict(mode="material_model", index_nd=1.6, abbe_vd=60, dpgf=.001, vary_index=True, vary_dpgf=True)`；PLAN = B0(基线) / C1(`adjust_index_to_environment=False`) / C2(`pressure_atm=0`) / C3(`temperature_c=10`) / B1(`index_nd=1.5`) / B2(`abbe_vd=50`) / B3(`dpgf=0`)。
- 波长表：`WAVELENGTHS=[.5875618,.5876,.4861327,.4861,.6562725,.6563]`。
- **原容差（不变）**：Nd `1e-6 + 1e-7·|ref|`；Vd `1e-5 + 1e-7·|ref|`；诊断 `1e-10 + 1e-10·|ref|`。正式约定 `formal_convention="physical"`（Nd 用物理 d，非经典四位 d）。

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

- 结果：**183 passed / 0 failed / 0 errors / 0 skipped**（1.03 s）。XML：`.local/evidence/development/ED-02/parallel-02/integrated-units.xml`。
- 本文件用例数：`test_material_model_reference.py` = **23**。
- 其余同批：extended_solves 82、modeling 42、pickup_adoption_helper 24、pickup_probe_contracts 9、solve_support 3。
- HPC 45 / 启动 38 已通过且未改，**沿用不重复**。

## 5. 准备未执行的原生范围

`scripts/probes/D002-MODEL_GLASS/model_glass_control018.py` 的 `run(output)` 已准备 A/B/C 矩阵、双入射角光线、solve 回读及关闭证据，本轮尚未原生执行。当前探针的完整标记固定为 complete=False；保存重载、失败恢复等声明范围仍待实现。

## 6. 缺口与解除条件

- 缺口：官方 Model Glass 定义已找到，公式待转录、Vd 偏差原因未定位；当前探针尚未实现 save/reload 和 failure recovery，尚缺 dPgF/环境独立参考及 vary_abbe=True 用例。原生矩阵未执行。
- 解除条件：先补上述探针范围及独立参考；两进程恢复门槛通过后，由 runtime 执行控制实验，满足正式谱线下原 Nd/Vd 门槛、保存重载和失败恢复，并取得正常关闭回执后再判定完整条目。
- 终态：MaterialModel 保持 **implemented**（非原生验收）；本轮完整计数 **0 新增**。离线测试不代表原生成功。

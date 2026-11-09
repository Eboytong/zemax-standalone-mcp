# EXT-HPC 配置查询：parallel-02 定向普通检查记录

- 日期：2026-11-08
- 主仓：`C:\Users\tonge\Desktop\Zemax_MCP`
- Python：`C:\Users\tonge\Desktop\Zemax_MCP\.venv\Scripts\python.exe`（`-B -X utf8`）
- 导入来源（实测）：`PYTHONPATH=C:\Users\tonge\Desktop\Zemax_MCP\src` → `zemax_mcp.__file__ = C:\Users\tonge\Desktop\Zemax_MCP\src\zemax_mcp\__init__.py`

> **性质声明：本文件仅为普通（离线）定向检查，不是原生验收。** 未启动 OpticStudio、未执行 `get_hpc_settings` 的正式原生对象查询；原生队列处于暂停。**本轮不新增完成计数。**

## 1. 集成的已审查 HPC 最小补丁

从 material-reports 工作区（`C:\Users\tonge\.codex\worktrees\zemax-p01-material-reports\Zemax_MCP`）审查后移入主仓：

- `tests/native/test_hpc_live.py`：改为**归一化 `Evidence.call` 契约**（成功→`data` dict；失败→`{'ok':False,'error':...}`）；新增独立成功验收 `test_hpc_native_preferences_success_readback`（null 错误路径 skip 并给原因，非空成功才校验六字段+source）；`test_hpc_minimal_native_job_result_and_close` 同步归一化。
- `tests/unit/test_hpc_success_driver.py`（新）：用 stub MCP client 对**真实** `tests.support.native.Evidence.call` 归一化驱动同一成功流。
- `tests/support/hpc.py`（新）：共享成功流 `check_preferences_success` **移入 support**；`tests/native/test_hpc_live.py` 与 `tests/unit/test_hpc_success_driver.py` 均改为 `from tests.support.hpc import check_preferences_success`（unit 不再导入 native 测试模块）。

产品侧核对：`src/zemax_mcp/hpc.py`、`src/zemax_mcp/hpc_models.py` 主仓与 material-reports **逐字节无差异**（已审查的“新成功入口 + 归一 response 修正”已在主仓，本次未改产品 src/公开契约）。`shutdown` 回执待真实原生成功后另行审查；本轮普通测试只证明流程。

## 2. 新增覆盖（按要求）

- `is_configured=false` / `node_count=0` 视为**有效成功**响应：`test_driver_is_configured_false_zero_nodes_is_valid_success` → `outcome=='success'`，并执行 `disconnect`。
- `is_configured` 缺失时**必失败**：`test_driver_missing_field_fails_on_success[is_configured]`（以及 `node_count/max_node_count/threads_per_task/shutdown_time_ticks/instance_type/source/ownership`）→ 抛 `KeyError/AssertionError`，且失败发生在 `disconnect`/skip 之前。
- 保留原有错误路径：null/`HPC_SETTINGS_UNAVAILABLE` → skip 分支并记录 `disconnect`（`test_driver_null_skips_and_records_disconnect`、`test_hpc_native_configuration_query`）。

## 3. 运行命令

```powershell
cd C:\Users\tonge\Desktop\Zemax_MCP
$env:PYTHONPATH='C:\Users\tonge\Desktop\Zemax_MCP\src'
New-Item -ItemType Directory -Force -Path .local\pytest-tmp | Out-Null
.\.venv\Scripts\python.exe -B -X utf8 -m pytest `
  tests/unit/test_hpc.py tests/unit/test_hpc_execution.py tests/unit/test_hpc_success_driver.py `
  -q -p no:cacheprovider `
  --basetemp=.local\pytest-tmp\p02-hpc-20261108175624 `
  --junitxml=.local\evidence\development\EXT-HPC\parallel-02-hpc-units.xml
```

（`--basetemp` 使用 `.local` 下新目录；首次因 `.local\pytest-tmp` 父目录不存在导致 `tmp_path` 建目录失败，属环境路径问题、非用例失败，预建父目录后重跑通过。）

## 4. 结果

- **45 passed / 0 failed / 0 errors / 0 skipped**（0.914 s）。
- JUnit：`.local/evidence/development/EXT-HPC/parallel-02-hpc-units.xml`（tests=45, failures=0, errors=0, skipped=0）。
- 原生测试仅 `--collect-only` 验证导入连线，可收集 6 个用例（**未运行**，无原生实例）。

## 5. 判定与边界

- 以上证明：可配置查询成功/空配置(is_configured=false,node_count=0)/缺字段必失败/错误路径 skip 的**流程与归一化契约**正确，且两处调用均经 `tests.support.hpc` 共享流。
- **不等于** HPC 正式对象查询的原生验收：真实非空 `IHPCSettings`、全部字段实测、`shutdown` 回执均**未执行**。恢复两进程门槛通过并开放队列后再做原生验收；本轮完成计数不增加。

# parallel-02 原生恢复诊断报告（组A GUI + 组B API 阶段探测）

- 日期：2026-11-08
- 任务：环境恢复、唯一原生执行与共享集成（parallel-02，权威主仓 `C:/Users/tonge/Desktop/Zemax_MCP`）
- 性质：受控原生启动两组（GUI 优先，API 次之）后的诊断落盘。**从现在起停止全部原生启动与功能测试，不再重试**；等待协调者审查功能探针后集成。
- 核心结论：**原生仍未恢复**。组A（常规 GUI）在 180 秒内未出现可操作主窗口，协调者 sky 两次枚举均为 0 个自有 OpticStudio 窗口、未发送 Alt+F4，自有树被强制清理；组B（API `CreateNewApplication`）在 `application_create` 阶段 180 秒超时、无正常关闭回执。两者**共享的启动条件仍未定位**，**不据此判定为许可/机器全局根因**。

## 1. 范围与约束

- 只做两组受控启动：每组 180 秒启动预算、15 秒异常自有树收尾；先 GUI 后 API；不超预算重复试验；有明确修复前不再做确认运行。
- 窗口观察与关闭统一由协调者 computer-use `sky` 执行；本任务**不编写/调用** EnumWindows、WM_CLOSE、PowerShell UIAutomation 或其他自制 UI 路径。本任务只创建自有进程、记录 PID/时间/进程树/许可日志、写 ready 标记并保留监督进程。
- 仅用现有安装与项目依赖；未修改共享许可服务/机器设置。`runtime` 独占原生执行。
- 未改产品代码（`src/zemax_mcp/native.py` 未改）；共享功能补丁待协调者单独审查后集成。

## 2. 环境与源码导入

| 项 | 值 |
| --- | --- |
| 主仓 | `C:\Users\tonge\Desktop\Zemax_MCP` |
| Python | `C:\Users\tonge\Desktop\Zemax_MCP\.venv\Scripts\python.exe`（`-B -X utf8`），3.14.6 |
| 目标安装 | `C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio`（`OpticStudio.exe` 存在） |
| `COMPLUS_LoadFromRemoteSources` | 宿主显式设为 `1` 并保留、记录；两次运行 `comp_plus="1"`（supervisor / 子观测 / wrapper-child 均记录） |
| 源码导入来源 | `zemax_mcp.__file__ = C:\Users\tonge\Desktop\Zemax_MCP\src\zemax_mcp\__init__.py`（主仓 `src`，非分支工作区） |
| 普通检查 | `PYTHONPATH=C:\Users\tonge\Desktop\Zemax_MCP\src`，38 passed（JUnit 见 §8） |

## 3. 组A：常规 GUI 启动（非 `-server`）

### 3.1 `runtime-gui-01`：**审查中断（aborted_by_review）** — 偏离计划，需记录

- 协调者审查 `runtime_gui_launch_probe.py` 后要求在启动前先修两处证据问题，本任务据此 `job_kill` 中断该次运行。
- **该次不是启动超时，记为 `aborted_by_review`**（`runtime-gui-01/status.json`）。原始 `gui-launch-ready.json` 与协调者 sky 观测保留，不据此下任何结论。
- PID `41804` 即为该中断尝试；协调者早期 sky 观测曾针对该已终止 PID，故 0 窗口不属本次有效结果。

### 3.2 `runtime-gui-02`：有效组A，强制收尾

| 项 | 值 |
| --- | --- |
| 自有进程 | `OpticStudio.exe` PID **12736**，父为探针 python；命令 `"C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio\OpticStudio.exe"`（**正常非 `-server`**） |
| started_at / deadline_at (UTC) | `2026-11-08T09:36:41.524Z` / `2026-11-08T09:39:41.524Z` |
| 结果状态 | `close_timeout`（180 秒内未退出） |
| elapsed | 180.897 s |
| 关闭方式 | **强制清理** `taskkill /PID 12736 /T /F`，returncode 0（`close_source=forced_cleanup`） |
| exit_code / child_alive | 1 / false |
| normal_close_observed | false（`normal_close_status=not_closed`） |
| 协调者 sky 观测 | **时序说明**：探针结束时（09:39:42Z）尚**未读到**观测文件（`observation_status=no_observation_file`）；协调者随后**补交同 PID 12736** 的观测：`sky.list_windows`@09:36:58 与 `sky.list_apps`@09:40:21 两次 `owned_opticstudio_window_count=0`；`alt_f4_sent=false`、`main_ui_observed=false`、`license_dialog_observed=false`。据此 reconcile 为 `observation_status=matched_pid_alt_f4_false`。 |
| 许可日志 | 48 个已扫文件，本次窗口内 `changed_since_start=0` |
| 残留 | 无 OpticStudio 进程 |

- 说明：本探针侧 `Get-Process` 曾见 PID 12736 顶层标题“应用程序正在打开，请稍候”，即**存在加载/启动窗口但未进入可操作主界面**；协调者 sky 以可操作窗口口径两次枚举为 0 且未 Alt+F4。
- 结论（限定证据）：GUI 常规路径在预算内**未到达可用/正常关闭**；是否与 API 同因**未定位**。按指示**不**把“GUI 无窗口/两者超时”直接判定为许可或全局根因，记为**共享启动条件未定位**。

## 4. 组B：API Standalone 阶段探测（`CreateNewApplication`）

- 证据目录：`runtime-standalone-stage-01`；监督器复用 `tests/support/connection_probe019.py`（180 s 启动 / 15 s 自有树清理，语义未改）。
- 唯一一次 API 探测，未重复启动。`COMPLUS_LoadFromRemoteSources=1` 全程记录（`comp_plus="1"`）。

### 4.1 监督结果

| 项 | 值 |
| --- | --- |
| state | `initialization_timeout` |
| elapsed | **180.1439575 s** |
| completed_stages | install_check, environment, clr_load, nethelper_assembly, zos_initialize, api_assemblies, connection_create |
| unfinished_stages | `probe_connect`, **`application_create`** |
| `application_create` started | `2026-11-08T09:40:50.383Z`，相对启动 0.788 s，之后无 completed |
| child_alive / 清理 | false；`taskkill /T /F` returncode 0 |
| native.json / 许可/PrimarySystem/CloseApplication | **无**（未取得许可值、无 PrimarySystem、无正常关闭回执） |

### 4.2 30/60/120 秒采样（原始 `stage-samples.jsonl`，未重跑）

自有树在三个采样点的 OpticStudio 子进程均为 PID **1236**（父为宿主 python 41476）。逐点实测：

| 采样 | 相对时刻 | 线程数（状态） | 等待原因样本 | 模块数 | 累计 CPU(s) | 工作集 | 许可文件(变更) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t30 | 30.063 s | 15（1 Running + 14 Wait） | EventPairLow | 101 | 30.4375 | ~86.26 MB | 48(0) |
| t60 | 60.071 s | 12（1 Running + 11 Wait） | UserRequest | 101 | 59.8125 | ~86.20 MB | 48(0) |
| t120 | 120.020 s | 11（1 Running + 10 Wait） | UserRequest | 101 | 118.328 | ~86.18 MB | 48(0) |

观测事实（不作推断）：
- 全程各有 **1 个线程处于 Running**，其余为 Wait（`EventPairLow` 或 `UserRequest`）；模块数恒为 **101**，工作集约 **86 MB** 稳定；许可日志目录内 48 个文件在本次时间窗内**无变更**。
- CPU 累计 30.4 → 59.8 → 118.3 s（约 ~1 核平均占用），但**Running 不等于自旋**，累计占用**不能**区分自旋/密集计算/空闲等待，也**不能**定位到代码位置；**不据此判定 spin 或互等**。
- 许可日志无新增**不能**证明许可代码未执行（可能不记录/记到别处/缓冲未刷盘），亦**不能**替本次背书；因此不足以判定许可根因。

### 4.3 观测能力与缺项（明确登记，不推断）

- **已取得**：自有进程树、OpticStudio 子进程逐线程 `ThreadState/WaitReason/TotalProcessorTime`、加载模块清单（101）、进程累计 CPU/工作集、许可日志目录文件清单与 mtime 变更。
- **缺项 `unavailable`**：命名管道/命名事件（无可靠现有工具，按指示**记 unavailable、不另造底层枚举**）。
- **证据局限**：许可日志“无变更”不等于“许可未执行”；单进程线程 Running 不等于自旋；故**共享启动条件未定位**，不推导根因。

### 4.4 父摘要回填与 reviewed-summary.json（原始事实保留，supervisor 非原件）

- **原始事实（必须保留）**：`run()` 执行时由父进程写出的 `supervisor.json` 中 `stage_sample_count=0`、`stage_samples_summary=[]`。原因是 `run()` 经父进程全局 `_journal`（恒 `None`）读取，`_read_samples()` 返回空；**并非**子进程无采样——子进程确实写入了 t30/t60/t120 三条原始样本。
- **supervisor.json 已被回填**：本任务于 **`2026-11-08T09:48:57.134Z`** 将该 `supervisor.json` 的 `stage_sample_count` 回填为 3 并追加可用性/缺项字段（`summary_corrected=true`）。因此 **`supervisor.json` 不是未改动的原件**；其 `stage_samples_summary` 仍为 `[]`，**不得**当作权威样本列表。本报告**不声称** supervisor 原件完全未改。
- **权威来源**：逐行原始 `stage-samples.jsonl`（未改动）保留全部执行事实（t30/t60/t120 各一条 `sample`）。
- **修正另存**：`.local/evidence/development/BASE-04/parallel-02/runtime-standalone-stage-01/reviewed-summary.json`，登记 `source=stage-samples.jsonl`、`original_summary_error`（`stage_sample_count=0`、`stage_samples_summary=[]` 及原因）、`supervisor_backfilled_at=2026-11-08T09:48:57.134Z`、`supervisor_not_pristine` 说明；修正结果 `stage_sample_count=3`、t30/t60/t120 全 present、缺项仅 `named_pipes_events=unavailable`。

## 5. 证据脚本修正（仅修证据问题，无重跑）

协调者审查 API 组B 代码提出三项证据修正，已改并 `py_compile` 通过（**未为修正观测脚本重启原生**；现有 `runtime-standalone-stage-01` 原始 `stage-samples.jsonl` 保留不动）：

1. `runtime_standalone_stage_probe.run` 父进程 `_journal` 恒 None 导致摘要恒 0 → 改为**按 folder 显式读取** `stage-samples.jsonl`；新增 `summarize(folder)`，登记 `expected_samples=[t30,t60,t120]`、`present_samples`、`missing_samples` 与缺项原因、逐样本 `threads/modules/license/named_pipes_events` 可用性。**已对既有运行回填修正**：`stage_sample_count=3`，t30/t60/t120 全 present，缺项仅 `named_pipes_events=unavailable`。
2. `runtime_observe._run_ps` 的 stderr/returncode 曾被丢弃 → 增加 `set_error_sink()`，真实失败写入 `observation-errors.jsonl`；并给 PowerShell 调用加 `encoding='utf-8', errors='replace'`，避免本地化（GBK）输出解码异常影响读取。
3. `Thread.WaitReason` 仅 Waiting 线程可读 → 仅 `ThreadState=="Wait"` 时读取，其余记 `wait_reason=null` 并保留 `state/CPU`，不因该属性抛错吞掉整条线程。
4. `_sample` 每样本用**一次 tree 快照**筛选 OpticStudio（不再重复采集）。

另：组A 脚本已按审查改为“进程退出≠正常关闭”：读取协调者 `gui-observation.json` 的 Alt+F4 标记并结合退出码判定；无标记记 `exit_observed`、正常关闭 `unknown/false`；`taskkill` 与 `proc.wait` 共用同一 15 秒 monotonic cleanup deadline。

## 6. 普通检查（可复用，不重跑未改产品集合）

- 定向启动/生命周期普通测试（早前已执行，**38 passed**）：
  `tests/unit/test_native_startup.py`、`tests/unit/test_startup_license_probe.py`、`tests/unit/test_runtime_lifecycle.py`
  命令：`.\.venv\Scripts\python.exe -B -X utf8 -m pytest <三个文件> -q -p no:cacheprovider --junitxml=.local\evidence\development\BASE-04\parallel-02\runtime-startup-units.xml`
- JUnit：`.local/evidence/development/BASE-04/parallel-02/runtime-startup-units.xml`
- 导入来源：主仓 `src/zemax_mcp/__init__.py`（见 §2）。
- 产品未改，故该集合**不重跑**；脚本改动仅做 `py_compile`（exit 0）。

## 7. 风险 / 阻塞

1. **根因未定位**：`application_create` 超时；H2 空闲互斥/单实例等待、H3 服务端↔宿主握手互等、H4 许可、H5 启动期重复初始化 均**保留**。线程 Running + CPU 上升不足以区分自旋/计算/等待。
2. **GUI 与 API 均未正常关闭**：GUI 无操作窗口、API 无 CloseApplication 回执；两者关系**未定位**，`共享启动条件未定位`。
3. **强杀残留风险**：`-server` 进程外状态可能残留，后续任何判读需先确认无残留 OpticStudio（当前确认 0 进程）。
4. 单席位许可必须串行；任何机器/服务配置变更需先提交证据与影响方案（本任务未改任何配置）。

## 8. 原生队列与后续（集成不等于恢复）

- **集成后保持原生暂停**：本轮完成离线 HPC 测试集成（见 `development/evidence/EXT-HPC/parallel-02-query-checks-20261108.md`），但**集成不等于恢复**；仅当**两进程恢复门槛通过**后才开放原生队列（先 HPC→MaterialModel→ChipZone→机械半口径），本轮不新增完成计数。
- **原生队列暂停**：停止所有原生启动与功能测试，不再重试；无明确修复前不做确认运行。
- 本任务保持 `runtime` 独占原生执行。

### 8.1 精确命令（本轮实际执行）

```powershell
# 组A GUI（正常非 -server；窗口由协调者 sky 观察/关闭）
$env:COMPLUS_LoadFromRemoteSources='1'; $env:PYTHONPATH='C:\Users\tonge\Desktop\Zemax_MCP\src'
.\.venv\Scripts\python.exe -B -X utf8 .local\coordination\runtime_gui_launch_probe.py `
  --output-dir .local\evidence\development\BASE-04\parallel-02\runtime-gui-02 `
  --startup-seconds 180 --cleanup-seconds 15 --observation-wait-seconds 30

# 组B API（复用原监督器 + 30/60/120 采样）
$env:COMPLUS_LoadFromRemoteSources='1'; $env:PYTHONPATH='C:\Users\tonge\Desktop\Zemax_MCP\src'
.\.venv\Scripts\python.exe -B -X utf8 .local\coordination\runtime_standalone_stage_probe.py `
  --output-dir .local\evidence\development\BASE-04\parallel-02\runtime-standalone-stage-01 `
  --startup-seconds 180 --cleanup-seconds 15

# 38 项启动普通检查（早前；产品未改不重跑）
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_native_startup.py tests/unit/test_startup_license_probe.py tests/unit/test_runtime_lifecycle.py -q -p no:cacheprovider --junitxml=.local\evidence\development\BASE-04\parallel-02\runtime-startup-units.xml
```

### 8.2 三个实际 PID

| 用途 | PID | 说明 |
| --- | --- | --- |
| GUI-01（审查中断） | **41804** | 因代码审查被 `job_kill`，记 `aborted_by_review`，非启动超时 |
| GUI-02（有效组A） | **12736** | 正常非 `-server` OpticStudio；180 秒 `close_timeout`，强制清理 |
| 组B OpticStudio 子进程 | **1236** | `application_create` 阶段自有 `OpticStudio.exe`（宿主 python 41476） |

### 8.3 解除条件（可检验，逐条独立；满足后才重开原生）

- **L1｜两进程门槛通过**：进程一（连接/许可/PrimarySystem/`new_system`/`get_system_settings`/正常关闭）与进程二（真实 stdio Cooke 相对照度/结果/分页/PNG/正常断开）**均通过**。
- **L2｜正常关闭回执**：`CloseApplication` 按本机实际返回定义判据（非假定必为 True），记录调用结果、`application` 归零与自有进程退出。
- **L3｜启动阶段推进**：`application_create` 在预算内 completed（不再 180 秒超时）并出现 `license_check`/`primary_system`。
- **L4｜证据充分性**：线程/模块/许可日志的缺项已按 `unavailable` 登记且不据此推断根因；若引入新假设，须说明其排除了哪条剩余假设（H2/H3/H4/H5）后再派发。
- **前置**：任何机器/服务/许可配置变更须先提交证据与影响方案并获批（本任务未改）。

## 9. 关键文件

- 计划：`.local/coordination/runtime-plan-parallel-02.md`
- 脚本：`.local/coordination/runtime_observe.py`、`runtime_gui_launch_probe.py`、`runtime_standalone_stage_probe.py`
- 组A：`.local/evidence/development/BASE-04/parallel-02/runtime-gui-01/status.json`（aborted_by_review）、`runtime-gui-02/gui-supervisor.json`、`gui-launch-ready.json`、`.local/coordination/parallel-02/gui-observation.json`
- 组B：`.local/evidence/development/BASE-04/parallel-02/runtime-standalone-stage-01/{supervisor.json, stage-samples.jsonl, wrapper-child.json}`
- 普通检查：`.local/evidence/development/BASE-04/parallel-02/runtime-startup-units.xml`
- 文档修正：`docs/guides/native-startup.md`（L3 旧 CLR 提示）、`development/assignments/parallel-01/00-runtime.md`（起点修正）

## 10. 状态

`IDLE_FOR_INTEGRATION`

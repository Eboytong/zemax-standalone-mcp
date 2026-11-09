# DSH parallel-02：诊断、离线修复与验收收口

日期：2026-11-08。权威主仓 `C:/Users/tonge/Desktop/Zemax_MCP`。六个既有 worker、session 和工作区继续复用，按计划审查、实施、返修、集成和定向检查推进。

本轮完成启动诊断和三条验收准备工作线的修复。**新增完整验收 0 项，累计 3/10**；原生启动仍受阻，四项候选的本轮原生验收均未执行。源码和发行版本保持 0.1.62，源码为 101 工具/130 分析，已发行包为 101/118。剩余 100 条源记录、95 个不同编号、93 组共同功能。

## 1. 原生恢复结果

| 对照 | 实际结果 | 生命周期 |
| --- | --- | --- |
| GUI-01，PID 41804 | 因代码审查中断，aborted_by_review | 单独记录中断原因 |
| GUI-02，PID 12736 | 180 秒内未取得可操作主界面；探针曾读到加载窗口标题 | 无可操作窗口可关闭，强制清理自有树；无正常关闭回执 |
| API，OpticStudio PID 1236 | CLR/API/connection 通过；application_create 超时 180.1439575 秒 | 无 API 许可值、PrimarySystem 或 CloseApplication 回执；强制清理自有树 |

实际环境为本机 Windows、Python 3.14.6、OpticStudio v242；命令使用主仓 Python、主仓 PYTHONPATH，COMPLUS_LoadFromRemoteSources=1。API 在 30/60/120 秒记录了进程树、线程和 101 个模块；所查 48 个许可目录文件在采样时间窗内无新增写入。超时原因未定位。详细命令、输入、观测及关闭事实见[诊断报告](parallel-02-runtime-20261108.md)。

API 父摘要曾误记采样为 0，runtime 于 09:48:57 UTC 回填 supervisor.json；逐行 stage-samples.jsonl 保留执行来源，修正解释另存 reviewed-summary.json。GUI-02 的同 PID 观察文件为监督结束后补交，原监督器当时未读到标记；正常关闭判定仍为 false。

本轮两组有界对照结束后，原生队列保持暂停。两个独立进程的恢复门槛尚未通过。

## 2. 四项候选的交付与实际状态

| 条目 | 本轮已交付 | 实际状态与验收缺口 |
| --- | --- | --- |
| D013 / EXT-HPC.Settings | 修复 Evidence.call 成功时已返回 data 却再次读取 ok/data 的错误；新增独立成功验收和共享检查，核对六项字段、来源、无新任务及断开；覆盖未配置/零节点和缺字段 | implemented；历史正式工厂返回 null，本轮未取得非空原生对象 |
| D002 / MaterialModel | 正式 Model Glass 定义审查；Nd 主门槛由四位 d 线修为精确 d 线，Vd 按正式谱线主比较，旧约定分列诊断；solve 六字段回读、严格布尔/有限数值及关闭判定 | implemented；历史 Vd 误差继续保留；公式转录、PgF/环境独立参考、vary_abbe=True、保存重载与失败恢复待补 |
| D003 / ChipZone SurfacePickup | 新探针记录各时刻三路 solve、来源/比例/偏移、源值联动、两次保存重载、逐光线状态、原生失败恢复和关闭 | blocked；历史成功返回后回退 Automatic，当前原生作业 prepared_not_executed |
| D003 / 机械半口径 SurfacePickup | 复用上述探针；失败实验的临时修改在探测请求被接受时也回滚；缺恢复、缺正常关闭或坏光线均阻止 complete | blocked；历史回退 Fixed 及失败数值改写仍待定位，当前作业未执行 |

HPC 的 is_configured=false 为有效查询结果。成功验收要求非空正式对象与实际字段；空对象错误处理保留独立记录。

MaterialModel 容差保持 Nd `1e-6 + 1e-7×|参考值|`、Vd `1e-5 + 1e-7×|参考值|`。四位谱线历史 Vd=59.99988524798844、精确谱线约 60.02418808 对参考 60 的误差均保留。本轮普通检查验证了波长选择和证据判定流程。

SurfacePickup 分别输出 adoption_passed 和 complete。构造的 alternate-column 请求在真实原生上的行为待执行；请求被接受时恢复该实验前状态，并以 failure_recovery_not_exercised 保持完整验收未完成。

逐项记录：[HPC](../EXT-HPC/parallel-02-query-checks-20261108.md)、[材料正式定义](../ED-02/parallel-02-material-definition-20261108.md)、[材料探针集成](../ED-02/parallel-02-material-model-20261108.md)、[两类拾取集成](../ED-02/parallel-02-pickup-20261108.md)。

## 3. 集成与检查

runtime 按审查结论依次将以下文件集成到主仓：

- tests/support/hpc.py、tests/native/test_hpc_live.py、tests/unit/test_hpc_success_driver.py。
- scripts/probes/D002-MODEL_GLASS/solve_contract.py、model_glass_control018.py、tests/unit/test_material_model_reference.py。
- scripts/probes/ED-02/pickup_adoption_helper.py、tests/unit/test_pickup_adoption_helper.py。

公开工具、请求模型和结果格式沿用当前契约；本轮改动集中在探针、测试和证据处理。相关检查均显式使用主仓源码，分支检查另存各自 worker 记录。

| 主仓定向范围 | 通过 | JUnit |
| --- | ---: | --- |
| 启动与生命周期 | 38 | `.local/evidence/development/BASE-04/parallel-02/runtime-startup-units.xml` |
| HPC查询与作业消费者 | 45 | `.local/evidence/development/EXT-HPC/parallel-02-hpc-units.xml` |
| 材料与拾取联合 | 183 | `.local/evidence/development/ED-02/parallel-02/integrated-units.xml` |
| 开发统计 | 17 | `.local/evidence/development/BASE-04/parallel-02/status-units.xml` |

四组共 **283 个不同普通用例通过**，失败/错误/跳过均为 0。分支阶段的 43/99/103/68 等旧结果及后续分支结果作为过程证据保留，主仓汇总按上表计数。HPC 原生入口仅收集 6 个用例检查导入关系，没有执行原生功能用例。

材料/拾取联合命令：

```powershell
$env:PYTHONPATH='C:/Users/tonge/Desktop/Zemax_MCP/src'
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_material_model_reference.py tests/unit/test_pickup_adoption_helper.py tests/unit/test_pickup_probe_contracts.py tests/unit/test_modeling.py tests/unit/test_extended_solves.py tests/unit/test_solve_support.py -q -p no:cacheprovider --basetemp=<本次.local临时目录> --junitxml=.local/evidence/development/ED-02/parallel-02/integrated-units.xml
```

准确 basetemp、导入路径及执行结果见两份 ED-02 集成记录。开发统计命令为 `scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json --ranked development/remaining-ranked.md`；统计定向命令为 `python -B -X utf8 -m pytest tests/unit/test_development_status_report.py -q -p no:cacheprovider --basetemp=.local/tmp/parallel-02-status-review --junitxml=.local/evidence/development/BASE-04/parallel-02/status-units.xml`。

## 4. 审查与监督

计划与审查负责人向原 worker 反馈了成功响应读取、错波长比较、提前标记 closed、恢复缺失仍 complete、光线任务成功却未检查逐行结果，以及临时探测成功后未恢复等问题。修正后由 runtime 在主仓集成并完成一次联合定向检查。

每 60 秒查询全部六个 worker，逐 worker 保存 nextSeq，hasMore=true 时继续取页。运行日志保留于 `.local/state/dsh-supervision/parallel-02/`，派工及评审结论同步至 [parallel-02.json](../../tracking/parallel-02.json)。两条停滞工作线曾中止当前回合并在原 session 恢复，最终修复和交付继续使用原工作区。

- calls.jsonl：MCP 调用、派工原文及返回。
- polls.jsonl：状态和增量事件页。
- progress-state.json：各 worker 的 session、工作区及读取游标。
- native-command-records.json：已抽取的原生命令，执行事件 seq 3803/3853/3923。
- supervision-closeout.json：最终 worker 状态、游标、监督停止时刻及原生残留检查。

独立审查指出启动探针的摘要读取、观测错误保留、线程 WaitReason 读取条件、GUI 关闭归属及时序问题。已采用修正或在诊断报告中登记其实际证据范围。阶段汇总与逐项台账状态保持一致。

## 5. 停止条件和下一步

本轮采用计划中的“原生启动仍受阻”停止条件。功能完整验收新增 0 项，集中检查仍为 3/10；下一次集中回归、构建、独立安装和 stdio 发行检查在十项首次完整验收时执行，目标版本 0.1.63。

下一步先取得新的启动日志或明确修复，使常规 OpticStudio 可以进入主界面并正常关闭；再完成两个独立进程的恢复门槛。通过后由 runtime 按 HPC→MaterialModel→ChipZone→机械半口径顺序执行已准备作业。离线可先转录已定位的 Model Glass 正式公式，补 PgF 和环境修正参考。完整状态及动作已同步 [current.md](../../current.md)、[handoff.md](../../handoff.md)、三份台账的适用记录和生成汇总。

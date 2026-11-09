# DSH首轮派工与监督

日期：2026-11-08。源码/发行0.1.62。当前按D00x记录开发；D010已完成3/3，集中检查累计3/10。

已使用本机`codex-dsh-desktop`的Streamable HTTP MCP入口完成握手、工具发现、worker创建和后续派发。实际服务提供六项工具，`dsh_wait_worker.timeoutMs`上限60000。

共同源码起点：`34e1a18494015c2b383ec700b958015020b660fe`，引用`codex/parallel-01-baseline`。通过独立Git索引保存当前有效源码、测试、文档及发行产物，原主区分支和索引保持原状；临时π脚本和pytest临时目录继续留在原位置。

| worker | 声明范围 | 工作区 |
| --- | --- | --- |
| zemax-p01-runtime | 环境恢复、集成、唯一原生执行 | 主项目 |
| zemax-p01-polarization | D001四项 | `.codex/worktrees/zemax-p01-polarization/Zemax_MCP` |
| zemax-p01-material-reports | D002四项材料报告 | `.codex/worktrees/zemax-p01-material-reports/Zemax_MCP` |
| zemax-p01-material-model | D002 MaterialModel | `.codex/worktrees/zemax-p01-material-model/Zemax_MCP` |
| zemax-p01-gradium | D002 Gradium | `.codex/worktrees/zemax-p01-gradium/Zemax_MCP` |
| zemax-p01-hologram | D010三项Hologram1效率 | `.codex/worktrees/zemax-p01-hologram/Zemax_MCP` |

表中功能工作区相对`C:/Users/tonge`。精确session ID、分支和实际状态见[分派登记](../../tracking/parallel-dispatch.json)。

运行原件：`.local/state/dsh-supervision/parallel-01/calls.jsonl`保留工具调用和返回，`polls.jsonl`保留事件页，`latest-summary.json`为最新状态；`baseline.json`记录共同起点。任务文本包含声明范围、必读文件、修改边界、原参考/容差、定向检查、原生作业和阶段审查要求。

监督采用本轮活动进程，每60秒查询全部worker并按各自`nextSeq`读取新增事件。接口研究、实现和普通检查并行；原生作业和共享补丁集成由runtime线依据审查结论串行执行。

当前阶段：六条工作线继续复用原worker和会话。Gradium、材料报告及偏振进入有界实现；Hologram1正在复核既有原生结果与当前声明范围。MaterialModel交付控制探查和普通检查后，同一worker已领取D004两种Power Map的计划阶段，分派累计覆盖15组候选功能。该早期阶段尚无新增验收完成项；最新收口见下文。

## 阶段审查与定向检查

协调者于2026-11-08在各任务工作区使用主项目Python环境执行以下普通检查：

| 工作线 | 测试入口 | 结果 | 证据 |
| --- | --- | --- | --- |
| Hologram1 | `tests/unit/test_diff_efficiency.py` | 24通过，0.29秒 | 本轮执行输出；监督目录`review-log.jsonl` |
| 偏振 | `tests/unit/test_polarization.py`、`test_transmission_fan.py` | 56通过，0.58秒 | `.local/evidence/development/BASE-04/parallel-01/review-polarization-unit.xml` |
| MaterialModel | `tests/unit/test_extended_solves.py`、`test_solve_support.py` | 85通过，0.71秒 | 同目录`review-material-model-unit.xml` |
| 原生启动与生命周期 | `test_native_startup.py`、`test_startup_license_probe.py`、`test_runtime_lifecycle.py` | 38通过，0.70秒 | 同目录`review-runtime-unit.xml` |

合计203项普通检查通过。DSH执行上下文中部分临时目录访问失败的用例，在协调者上述执行中通过；该问题与光学数值验收分别记录。

CLR对照：协调者与runtime均复现`Python.Runtime.Loader.Initialize`解析失败。runtime的.NET Framework控制实验中，本机新编译DLL的文件加载也返回`0x80131515`并报告网络位置限制；该错误发生在创建OpticStudio实例之前。`repro-06`的`ok=true`表示诊断脚本完成，其六个成员解析全部失败。报告位于`.local/coordination/runtime-report.md`，原始实验位于`.local/evidence/development/BASE-04/parallel-01/diagnostics/`。已授权项目临时目录内的netfx配置对照，结果待回报。

材料报告离线审查：SCHOTT报告346行全部匹配本机目录，原名称缺口由大小写和科学记数法公式编号解析解释；折射率、中心差分及解析导数按各自原门槛分别记录。Gradium高阶与MaterialModel的原数值门槛继续保留，完整功能状态等待控制实验及独立参考。

## 后续审查与当前执行条件

以下是后续改动对应的实际执行记录；与上表重叠的检查分别归于其执行版本：

| 工作线 | 最终定向范围 | 结果 | 证据 |
| --- | --- | --- | --- |
| 材料报告 | `test_glass_map.py`、`test_dispersion_diagram.py`、`test_contracts.py`、`test_material_reports_reference.py` | 64通过，0.68秒 | `.local/evidence/development/BASE-04/parallel-01/review-material-reports2-unit.xml` |
| MaterialModel | 两个既有solve测试文件及新增`test_material_model_reference.py` | 97通过，0.62秒 | 同目录`review-material-model2-unit.xml` |
| stdio测试参数 | `test_release_parameters.py`，含显式CLR开关传递与缺省不传递 | 5通过，0.507秒 | 同目录`review-release-parameters.xml` |

材料报告初次审查出现62通过/1失败，新增样例缺少真实原生报告的第一行列标题；修复夹具后64项通过。无热玻璃图解析读取报告实际`xE`比例，指数溢出或下溢保留具体结果错误。SCHOTT 346行折射率最大误差`4.96616834322339e-8`，中心差分99点最大误差约`3.49e-5`；解析导数另有4点超过`5.1e-8`，继续作为未通过诊断保留。MaterialModel七组A/B/C控制实验已准备，Nd/Vd原容差保留。

AppDomain配置对照没有解除装配加载限制；显式单进程`COMPLUS_LoadFromRemoteSources=1`可解除第一处加载限制。DSH子进程随后在pythonnet枚举本进程模块时得到`Process.get_Handle`拒绝访问；协调者常规进程成功初始化CLR。因此runtime保留排队、集成及生命周期审查职责，协调者执行已批准的原生命令。产品加载代码未自动启用该变量，测试stdio辅助只传递调用方已有的值。

首个常规进程连接恢复命令：

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B tests/support/connection_probe019.py --output-dir .local/evidence/development/BASE-04/parallel-01/runtime-recovery-01
```

结果：CLR、NetHelper、ZOS初始化、API装配和连接创建通过；`application_create`自2026-11-08T06:05:39.471Z起等待，180秒超时。监督器终止本次自有进程树，耗时180.10764秒，清理返回码0、`child_alive=false`。没有API许可结果、`native.json`或正常应用关闭回执。原件见该目录`supervisor.json`、`stages.jsonl`及stdout/stderr；状态登记于监督目录`native-execution.json`。后续原生启动等待有新日志依据的控制实验。

偏振模型服务流式中断后向原worker重新派发，session及工作区保持。所有后续任务优先复用现有worker，分派和阶段结论继续记入`calls.jsonl`与`review-log.jsonl`。


## 最新收口与复用

D010原生Hologram1三项已审查完成。主区显示修正和相关回归122项通过，完整二维网格S/P最大误差5.753e-11/5.245e-11，生命周期证据齐备。详见[逐项证据](../CO-01/hologram1-review-20261108/README.md)。台账已同步done，统计工具17项通过；剩余100条源记录、95个不同编号、93组共同功能。

材料报告解析主区64项通过、MaterialModel参考主区97项通过；D001适配器来源树144项通过并交runtime合入。热光参考359/364行有独立结果，其余五项资源和正式选择问题保留，参考输入条件正在修正。原hologram worker已复用至D008 SagTable计划，全部复用候选累计20组。各次测试按独立执行记录列示，有重叠的检查不相加。

原生启动01/02/05均到application_create后180秒超时。05确认环境变量分阶段移除已生效，仍未解决超时；自有进程树已终止，无正常CloseApplication回执。本轮其余工作未新建原生实例，运行记录见[runtime-phase-environment-20261108.md](runtime-phase-environment-20261108.md)。

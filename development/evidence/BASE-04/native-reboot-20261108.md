# 重启后 Standalone 诊断与排期冻结

日期：2026-11-08（Asia/Shanghai）。主仓`C:/Users/tonge/Desktop/Zemax_MCP`；源码0.1.62、101工具/130分析，发行101/118。基础设施诊断增加0项完整验收，累计3/10，剩余100条源记录、95个不同编号、93组共同功能。

## 实际执行

系统启动时间19:22:49。自动原生作业串行执行；用户手动实例PID23264自19:41:13起保留，未调用其CloseApplication、未修改其模型。用户打开过实例1的交互扩展等待窗口，随后自行关闭；此次没有调用ConnectAsExtension。

| 对照 | 输入与设置 | 结果 | 原始目录 |
| --- | --- | --- | --- |
| 常规GUI | 自有PID12836；安装目录为cwd，COMPLUS_LoadFromRemoteSources=1 | 180.004秒未进入可操作主界面；强制清理，child_alive=false，正常关闭=false | `reboot-20261108/gui` |
| 原有Standalone | 主仓Python3.14、继承环境、同一CLR开关 | application_create超时180.1029782秒；CLR/API/connection通过；无许可、PrimarySystem或正常关闭回执 | `reboot-20261108/api` |
| 登录PATH对照 | 仅将PATH替换为Windows登录环境值，CLR开关仍为1 | application_create超时180.1035901秒；PATH变化未解决本次故障 | `reboot-20261108/logon-path` |
| 去掉CLR开关 | 继承PATH，省略COMPLUS_LoadFromRemoteSources | 0.5785022秒失败于clr_load，Python.Runtime.Loader.Initialize无法解析；未创建原生应用 | `reboot-20261108/without-clr-switch` |
| 子应用阶段去掉CLR开关 | 先用开关加载Python CLR，再仅于application_create阶段移除；Python及.NET均回读空值 | application_create超时180.1119511秒；自有OpticStudio PID16380及Python树清理成功；child_alive=false | `reboot-20261108/child-without-clr-switch` |
| 用户手动GUI | 普通启动，PID23264 | 主界面、Premium标识及镜头编辑器可见，进程响应正常 | 用户截图、窗口观察及进程记录 |

相对原始目录均位于`.local/evidence/development/BASE-04/`。自动探测预算180秒，异常收尾15秒。API类对照的阶段及30/60/120秒采样由既有`runtime_standalone_stage_probe.py`生成。`supervisor.json`、`stages.jsonl`、`stage-samples.jsonl`保留；去掉CLR开关的短失败没有到达采样时刻。

GUI观察在19:32:42仍无可操作窗口，进程标题“应用程序正在打开，请稍候”，Responding=false。API原始对照读取末尾256KiB授权日志，在本次自有PID及时间窗内匹配0条事件，未定位启动根因。

## 新发现：进程完整性级别不同

使用Windows令牌正式查询接口只读取得：

| 进程 | PID | 完整性SID | TokenElevation | 会话 |
| --- | ---: | --- | ---: | ---: |
| 自动检查Python | 21388 | S-1-16-4096（Low） | 0 | 1 |
| 自动Standalone OpticStudio | 16380 | S-1-16-4096（Low） | 0 | 1 |
| 用户手动OpticStudio | 23264 | S-1-16-8192（Medium） | 0 | 1 |

来源：`child-without-clr-switch/process-context.json`。自动实例命令为`OpticStudio.exe -server -pid="28120"`；手动实例为同一安装的普通可执行文件。完整性与启动方式均有差异；当前证据尚未确认哪一项导致超时。

普通用户PowerShell对照已于20:08:31执行，证据为`normal-session-20261108T120831-5f1aa08c`。项目内Python仍为Low；入口返回`blocked_low_integrity_context`，未启动原生应用。此次结果尚未覆盖Medium上下文下的ZOS-API。

进一步只读检查确认：该PowerShell（PID32756）、父级explorer（PID12336）及WindowsTerminal（PID4316）均为Medium；项目根目录、`.venv`目录和`.venv\Scripts\python.exe`带有Low强制完整性标记，Anaconda基础解释器没有该标记。pywin32与直接Win32令牌API查询一致。双路径查询及文件标记见`reboot-20261108/token-label-observation.json`，增强入口的实际输出见`token-label-context/process-context.json`；本轮未改变任何安全设置。

历史已执行命令：

```powershell
& 'C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe' -B -X utf8 'C:/Users/tonge/Desktop/Zemax_MCP/scripts/development/native_startup_check.py'
```

下一实验从现有普通用户PowerShell使用项目外环境。新增入口先记录基础解释器上下文，再在`%USERPROFILE%\Zemax_MCP_Runtime\.venv`创建Python3.14环境并按现有约束安装源码及报告/测试依赖；随后运行同一180秒Standalone最小探针。输出写入`.local/evidence/development/BASE-04/external-runtime-<时间>-<编号>/`。本轮只完成入口准备，尚未从用户终端执行。

```powershell
& 'C:/Users/tonge/Desktop/Zemax_MCP/scripts/development/native_startup_clean_env.ps1'
```

## 调整与定向检查

两次早期超时收尾出现taskkill中文输出被UTF-8解码失败，原始退出码0及child_alive=false仍保留，stdout缺失。已将`tests/support/connection_probe019.py`的taskkill输出改为Windows OEM解码；最后一次对照完整记录中文清理回执。产品`native.py`及Standalone工具契约未修改。

冻结由`development/tracking/native-freeze.json`单独维护，状态工具在queue、status及逐项表中显示冻结。实现状态、别名证据和完成计数沿用台账；定向测试覆盖冻结/解冻、别名、已完成项及周期计数。

前次定向54项通过，XML为`.local/evidence/development/BASE-04/reboot-20261108/targeted-checks.xml`。新增普通终端入口5项用例后，最终命令为：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_native_startup.py tests/unit/test_connection_probe.py tests/unit/test_startup_license_probe.py tests/unit/test_development_status_report.py tests/unit/test_native_startup_check.py -q -p no:cacheprovider --basetemp=.local/tmp/reboot-20261108-final --junitxml=.local/evidence/development/BASE-04/reboot-20261108/final-checks.xml
```

此前最终结果为59项通过，见`final-checks.xml`及同目录`final-checks.json`。补充父进程/文件标记记录与context-only模式后，同范围62项通过、0失败、0错误、0跳过，XML为`token-label-checks.xml`；新PowerShell入口语法解析通过。当前Low上下文实测保存在`low-context-guard/`和`token-label-context/`，均未启动原生进程。此次未执行功能stdio、wheel或全量回归。

## 冻结与解除条件

剩余93组的在线接口探查、依赖未确认原生行为的开发、设置/结果/数值/恢复/关闭验收、功能stdio和原生发行检查冻结。D010已完成3组及既有功能代码、历史验收证据保留；在当前环境执行含原生调用的旧功能仍受Standalone启动故障影响。已有结果的离线读取、分页和绘图可独立使用。

离线资料、既有元数据、历史结果与数学参考、基于已确认接口的请求/解析逻辑、普通测试及文档整理可单独安排。各条目已有许可、资源、正式接口及数值缺口保留。

解除顺序：项目外运行时取得Medium上下文结论→独立进程通过API许可/PrimarySystem/建模/设置/正常关闭→第二个独立进程通过真实stdio Cooke相对照度、结果/分页/PNG/正常断开→审查后更新冻结标记。保留功能队列为HPC→MaterialModel→ChipZone→机械半口径。

DSH重启后返回127.0.0.1:59873拒绝连接，worker及监督循环未重启；后续继续复用原worker/session。原始现场保存在本机数据目录，此次未发布新版本。

## 未签名PowerShell入口与Python入口调整

用户执行PS入口时返回PSSecurityException/UnauthorizedAccess，脚本未进入执行。只读查询Windows PowerShell5.1取得CurrentUser=RemoteSigned、MachinePolicy/UserPolicy/Process/LocalMachine均Undefined；System.Security.Policy.Zone将本地PS文件识别为Internet，文件只列出:$DATA流。该记录解释本次签名拦截，未产生新的ZOS-API启动结果。

环境准备逻辑已迁到`scripts/development/native_startup_clean_env.py`，PS文件保留为薄包装；使用现有Anaconda基础Python执行当前入口。PowerShell策略及文件安全标记保持原值。入口记录bootstrap.json及子阶段退出码；Low基础进程、依赖安装失败和环境创建异常均在原生作业前停止，已有外部运行时继续复用。

当前命令：

```powershell
& 'C:/Users/tonge/anaconda3/python.exe' -B -X utf8 'C:/Users/tonge/Desktop/Zemax_MCP/scripts/development/native_startup_clean_env.py'
```

定向检查新增5项，涵盖Low阻断、安装失败、环境复用、项目内路径拒绝及创建异常，最终67项通过，XML为`reboot-20261108/python-entry-checks-fixed.xml`。首次新增测试的临时夹具目录位于真实项目内，触发外部路径保护；修正测试项目根路径后复测通过，首次记录保留于`python-entry-checks.xml`。Low上下文实测为`python-entry-low-context/bootstrap.json`，state=blocked_base_context、native_requested=false。外部环境的实际用户运行结果仍待收集，冻结与3/10计数保留。

## 项目外运行时首次成功（High上下文）

用户在20:30:21启动Python入口，证据为`.local/evidence/development/BASE-04/external-runtime-20261108T123021-43600515`。基础解释器、父级终端及外部运行时均为S-1-16-12288（High）、elevated=true、会话1；外部解释器文件无Low标记。环境创建及锁定约束下的源码/报告/测试依赖安装均退出0。

20:32:08开始最小Standalone探针，应用创建5.1277084秒，全程10.2708124秒，state=passed、exit_code=0、child_alive=false。原生24.2.0、PremiumEdition；API许可、PrimarySystem、新模型、系统设置读取与application_close全部完成，native.json记录closed=true、connected=true、minimal_model_passed=true。bootstrap.json全部阶段退出0，state=passed。

本次为High权限条件成功；普通用户Medium条件和第二个独立真实stdio Cooke相对照度/结果/分页/PNG尚未执行。此前Low失败与本次High成功同时改变运行时位置和进程权限，恢复原因仍按这些实际条件记录。用户原有OpticStudio实例未参与本次最小检查。

下一步在普通、未提升的PowerShell中复用已安装的外部解释器运行同一最小探针：

```powershell
& 'C:/Users/tonge/Zemax_MCP_Runtime/.venv/Scripts/python.exe' -B -X utf8 'C:/Users/tonge/Desktop/Zemax_MCP/scripts/development/native_startup_check.py'
```

已有环境无需重建。普通用户通过后继续真实stdio恢复门槛，再审查解除原生冻结；累计完整功能仍3/10。此次只更新运行证据、计划和交接，未执行新一轮代码测试或发行。

## 普通用户Medium最小Standalone通过

20:35:29用户使用项目外解释器运行最小探针，原始目录为`.local/evidence/development/BASE-04/normal-session-20261108T123529-4579db0d`。Python2256、父终端32008均为S-1-16-8192、elevated=false、会话1，解释器文件无Low标记。state=passed、exit_code=0、child_alive=false，耗时9.2417344秒，应用创建5.064828999999918秒；原生版本24.2.0、许可PremiumEdition。API许可、PrimarySystem、新建模型、系统设置读取及application_close全部通过，closed=true。管理员权限与普通用户权限下分别取得独立成功记录，Medium恢复门槛已满足。

下一步为第二个独立真实stdio会话：`scripts/development/native_stdio_check.py`。该入口要求Medium未提升上下文，读取run_analysis schema，打开Cooke自有副本，完成相对照度最大值归一化检查、两段曲线分页与原结果对照、PNG导出、任务关闭、disconnect及application_close事件核对；调用和结果写入stdio-recovery独立目录。成功或异常均尝试断开，关闭异常单独保存并保留原始分析错误。

```powershell
& 'C:/Users/tonge/Zemax_MCP_Runtime/.venv/Scripts/python.exe' -B -X utf8 'C:/Users/tonge/Desktop/Zemax_MCP/scripts/development/native_stdio_check.py'
```

新入口相关普通检查13项通过，XML为`reboot-20261108/stdio-entry-checks-fixed.xml`。首次mock缺少finish成员的夹具错误已修正，首次结果保留于stdio-entry-checks.xml。此次未执行真实stdio；需要用户在刚才Medium窗口运行上述入口。原生排期继续等待此门槛，完整功能累计3/10保持。

## 真实stdio通过与解除统一冻结

2026-11-08 20:42:25（Asia/Shanghai）用户从普通窗口执行native_stdio_check.py。证据为`.local/evidence/development/BASE-04/stdio-recovery-20261108T124225-99c5ff22`，context为Medium、elevated=false，客户端使用项目外解释器。result.json为passed、analysis_passed=true、normal_close=true。客户端先取得run_analysis请求schema；Cooke自有副本输入身份、实际波长1/Plus_Y/光线密度10/视场密度21/偏振关闭/移除渐晕因子开启均有回读。

任务6dc1b64c68a040feb7bc28aa9edea0ec为succeeded，close_attempted=true。相对照度最大值1.0，参考1，容差1e-6+1e-7×参考值，实际误差0。曲线start=0和7两段各取7点，均与完整结果对应切片一致。PNG成功生成并已查看；原生文本、JSON及CSV均在任务结果中登记。disconnect成功，get_status返回connected=false、running_tasks=[]，application_close完成事件存在。审查摘要另存原目录review.json。

独立Medium最小Standalone与真实stdio两项恢复门槛均通过，native-freeze.json的active改为false，恢复原生任务排期。适用执行条件固定为`C:/Users/tonge/Zemax_MCP_Runtime/.venv/Scripts/python.exe`、普通未提升用户上下文，诊断中使用的COMPLUS_LoadFromRemoteSources=1仅随执行进程设置。产品继续Standalone。

自动命令工具仍处于Low上下文；从该工具启动外部解释器仍继承Low。功能原生任务需经已验证的用户上下文执行通道安排。DSH本机59873端口本轮未发现监听，尚未恢复worker监督；优先保留原worker复用。各条目的许可、资源、正式接口与数值缺口沿台账保留。统一启动冻结解除不增加完整功能计数，累计仍3/10，剩余93组。

下一动作：恢复DSH连接并登记可用的Medium执行通道，然后按HPC配置→MaterialModel→ChipZone拾取→机械半口径拾取串行收口。原生通道恢复与各条目验收分别记录。未运行全量回归、构建或发行。

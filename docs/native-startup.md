# 原生启动诊断

当前基线：0.1.61已完成原生发行验收；637–641状态见[当前交接](development-handoff.md)。以下为历史启动故障及诊断方法，按实际新故障选用。

# 原生启动阶段与受控探测

## 2026-11-05 重启后恢复

系统启动时间为 13:25:47。重启后的既有隔离探测 connection-20261105T052807-f269b612 已结束，无存活子进程；总耗时 14.674 秒，应用创建耗时 11.615 秒。API 许可检查、PrimarySystem、新建模型、系统设置读取和 application_close 均完成；最小探测返回 ProfessionalEdition。后续业务会话记录实际许可，部分为 PremiumEdition。

本轮通过真实 stdio 执行 ED-01 七项原生回归、建模及 POP 集成、扩展资源查询和 CAD 设置。0.1.46 独立安装包五项原生冒烟通过。FRU__delta_init 的 stderr 警告仍出现在成功会话中，继续作为独立诊断项保留。

证据：verification/development/BASE-04/reboot046.json、release046.json。下文的 connection045 超时、旧代理 PID 和待重启描述属于重启前历史记录；当前继续按功能条目执行原生验收。

0.1.45继续使用既有connect/disconnect入口，新增内部阶段记录；get_status.native_startup返回events与observer_warnings。阶段错误保留原始错误码或NATIVE_ERROR、startup_stage和startup_events；二次关闭失败保留cleanup_error。记录写入内存及探测文件，保持stdio协议输出清晰。

阶段依次为install_check、environment、clr_load、nethelper_assembly、zos_initialize、api_assemblies、connection_create、application_create、license_check、primary_system，关闭记录application_close。每个事件含UTC时间、开始/完成/失败状态、相对耗时及原始异常。

首个安装目录DLL加载后即锁定目录；切换目录要求重启进程。验证未完成的应用不得复用。关闭失败时保留所有权并要求重连，后续disconnect可跳过已不可用系统的检查点读取，继续尝试关闭。

```powershell
.venv/Scripts/python.exe -B tests/support/connection_probe019.py
```

默认每次创建独立目录。指定目录时要求目录尚不存在：

```powershell
.venv/Scripts/python.exe -B tests/support/connection_probe019.py --output-dir verification/development/BASE-04/connection-next
```

探测启动预算180秒，清理预算15秒。超时只终止本次创建的子进程树，记录child_alive；清理未完成则保留cleanup_pending供后续检查。目录包含stages.jsonl、stdout.txt、stderr.txt、supervisor.json；子进程正常返回时另有native.json。最后一行写入中断时仍可读取此前完整事件。成功路径通过Backend执行连接、新建模型、系统设置读取和关闭；该探测使用进程内Backend，真实stdio验收单独执行。

## 2026-11-05实际结果

connection045在180.761秒结束，停于application_create。CLR和程序集加载、zos_initialize、connection_create均完成；zos_initialize约0.010秒，connection_create约0.584秒。CreateNewApplication未返回，因此未取得API许可状态、PrimarySystem或正常CloseApplication回执。本次子进程树终止成功，child_alive=false。此结果将此前“初始化超时”定位到具体应用创建阶段。

只读lmstat查询显示1055@localhost服务器及ansyslmd为UP，zos_level2报告1000许可、0占用；该查询与API许可检查分别记录。授权客户端日志最后写入11:40，本次探测12:16启动，查看的尾部没有本次启动记录。当前证据尚未确定应用创建停滞的根因。

证据：verification/development/BASE-04/startup045.json、connection045/supervisor.json及lmstat045.json。28项定向普通测试通过；成功应用创建、最小模型及正常原生关闭等待启动恢复。后续定位OpticStudio应用启动，在相关条件变化后重试分阶段探测，再串行开放原生验收队列。

## 本轮定位：本地授权代理握手超时

进一步检查原生授权调试日志，定位到与 connection045 同一自有子进程 PID 25608 的记录。2026-11-05 12:17:42 和 12:19:02 均出现 HANDSHAKE_ERROR，目标为 51820@127.0.0.1；12:19:02 另有两条 CONNECT_ERROR，原始原因均为 SSL 握手超时。此前读取的代理日志没有新增记录，本次读取的是 licdebug.TONGEB.ANSYS OPTICSTUDIO.242.out。

监督记录的 taskkill 回执确认 PID 25608 属于本次自有进程树。事件位于 12:16:19 至 12:19:22 的启动窗口内。本机端口观察确认 51820 当前由 ansyscl.exe（PID 22292，创建于 2026-11-04 23:40:00）监听，路径为 C:/Program Files/ANSYS Inc/v242/licensingclient/winx64/ansyscl.exe。证据将本次应用创建失败定位到本地授权代理握手；代理为何未完成握手仍待排查。

新增只读关联脚本按自有 PID 和本地时间窗口筛选日志，最多读取末尾 256 KiB，可直接分析已有探测目录：

```powershell
.venv/Scripts/python.exe -B tests/support/startup_license_probe.py --attempt verification/development/BASE-04/connection045 --output verification/development/BASE-04/licensing-correlation045.json
```

实际匹配四条失败事件。关联结果 licensing-correlation045.json、当前代理与监听信息 license-proxy045.json 位于 verification/development/BASE-04/。34 项定向普通测试通过，其中新增 6 项覆盖历史及无关 PID 排除、父进程排除、失败终止回执、时间换算、日志读取上限、缺失日志和缺失时间戳。

下一项受控排查动作：重新核对代理路径与创建时间，经授权重启该本地客户端代理后，执行一次新的隔离启动探测，判断握手是否恢复，再运行最小模型。该代理供本机 Ansys 应用共享，重启可能打断其他会话的授权通信。本轮保留现有进程及服务状态，尚未执行重启或新建原生应用。

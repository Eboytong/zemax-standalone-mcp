# 原生启动：阶段环境变量对照

2026-11-08；源码0.1.62，Python3.14.6，目标安装为OpticStudio2024R2。运行由协调者常规进程执行，DSH runtime保留排队与集成职责。

已知前两次探查在CLR/API/connection完成后进入`application_create`，180秒超时。第二次观察到OpticStudio.exe的CPU增加；这些观测尚未定位具体内部等待或计算位置。

本次计划测试阶段环境变量的影响：宿主启动时显式设置`COMPLUS_LoadFromRemoteSources=1`，在`application_create started`事件中移除；此前CLR、API及connection阶段均已完成。复用原connection_probe019监督与自有进程树清理，产品代码保持原状。

命令（主项目根目录）：

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B .local/coordination/runtime_child_env_probe.py --output-dir .local/evidence/development/BASE-04/parallel-01/runtime-recovery-05 --startup-seconds 180 --cleanup-seconds 15
```

原件目录为`.local/evidence/development/BASE-04/parallel-01/runtime-recovery-05/`。`wrapper-child.json`确认本次wrapper；`child-env.jsonl`记录移除前为1、移除后为空，新建Python进程分别读到1和unset，`child_env_drop_ok=true`。`application_create`开始于2026-11-08T06:56:47.688Z；观察到OpticStudio.exe PID40756、宿主PID2756。

结果为`initialization_timeout`，总耗时180.1160528秒，命令退出1。监督器对自有进程树执行清理，返回0，`child_alive=false`。本次未取得`native.json`、API许可值或正常应用关闭回执。

结论：在这一阶段移除环境变量未解除应用创建超时。继续保留原生启动阻塞，后续执行需要新的可区分假设或启动条件变化。当前可继续普通测试、正式资料探查及已审查补丁集成；完整光学原生验收仍待恢复。

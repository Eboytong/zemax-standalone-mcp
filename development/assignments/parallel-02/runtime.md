# 环境恢复、唯一原生执行与共享集成

本轮 parallel-02。权威主仓 C:/Users/tonge/Desktop/Zemax_MCP；Python C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe（-B -X utf8）。源码0.1.62，101工具/130分析；发行101/118。上一轮96项审查：3完整、38部分、55待条件，剩余93组；本轮目标恢复原生并新增3完整验收，候选仅HPC配置、MaterialModel和两种SurfacePickup。完整计数由协调者审查后更新。原生执行由runtime唯一负责，其他worker提交作业申请。分支普通检查必须显式PYTHONPATH为本工作区src并记录导入来源；最终验收针对集成主仓。共享入口以主仓当前内容为准，由runtime集成最小补丁。原有工作区和会话继续复用。
必读主仓 development/handoff.md、development/current.md、development/plan.md第7节，以及本项的最新证据和实际源码。当前第一阶段只提交具体实施计划及只读发现，写本任务plan文件；提交后结束本回合等待协调者审查。计划需列正式接口、现有缺口、输入与参考、原门槛、精确检查命令、原生作业、关闭/恢复与完成条件。此阶段不启动OpticStudio或原生测试。

任务职责：环境恢复、唯一原生执行与共享集成
重点阅读主仓 development/evidence/BASE-04/runtime-phase-environment-20261108.md、.local/coordination/runtime-timeout-review.md、tests/support/connection_probe019.py、src/zemax_mcp/native.py。最新阶段是application_create，CLR/API/connection已在三次受控尝试通过；别把旧CLR异常当最新结论。
提出两组受控对照的精确实施计划：常规GUI启动（识别自有PID、窗口/对话框和许可信息，随后正常关闭）；关闭后Standalone阶段探测，在30/60/120秒收集自有树、线程状态/CPU增量、可取得模块及本次PID/时间窗许可日志。每次180秒启动、15秒异常收尾；最多这两组，有明确修复后加一次确认。只用现有安装和项目依赖；涉及共享许可服务/机器设置的实际需求返回具体动作、证据和影响。当前未授权改变这些配置。
需交付子进程执行及观测脚本设计、对照判别表、正常/强制收尾区别。恢复门槛是两个独立Python进程：先连接/许可/PrimarySystem/建模/设置/正常关闭，再真实stdio Cooke相对照度/结果/分页/PNG/正常断开。门槛通过后依HPC→MaterialModel→ChipZone→机械半口径执行经审查作业。
拥有本轮启动脚本及必要native.py最小修复、启动诊断文档的旧CLR提示、原00-runtime任务书起点修正；功能共享补丁仅按协调审查合入。先计划，不执行启动。

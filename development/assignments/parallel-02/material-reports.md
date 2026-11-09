# D013 HPC配置查询成功路径验收

本轮 parallel-02。权威主仓 C:/Users/tonge/Desktop/Zemax_MCP；Python C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe（-B -X utf8）。源码0.1.62，101工具/130分析；发行101/118。上一轮96项审查：3完整、38部分、55待条件，剩余93组；本轮目标恢复原生并新增3完整验收，候选仅HPC配置、MaterialModel和两种SurfacePickup。完整计数由协调者审查后更新。原生执行由runtime唯一负责，其他worker提交作业申请。分支普通检查必须显式PYTHONPATH为本工作区src并记录导入来源；最终验收针对集成主仓。共享入口以主仓当前内容为准，由runtime集成最小补丁。原有工作区和会话继续复用。
必读主仓 development/handoff.md、development/current.md、development/plan.md第7节，以及本项的最新证据和实际源码。当前第一阶段只提交具体实施计划及只读发现，写本任务plan文件；提交后结束本回合等待协调者审查。计划需列正式接口、现有缺口、输入与参考、原门槛、精确检查命令、原生作业、关闭/恢复与完成条件。此阶段不启动OpticStudio或原生测试。

任务职责：D013 HPC配置查询成功路径验收
只处理EXT-HPC.Settings，读取主仓src/zemax_mcp/hpc.py、tests/native/test_hpc_live.py、tests/unit/test_hpc.py和development/evidence/EXT-HPC/settings-preferences-20261108.md。GetHPCSettingsFromPrefs历史返回null；当前native测试允许HPC_SETTINGS_UNAVAILABLE也通过。这是错误处理覆盖，完整验收另需非空IHPCSettings、实际全部字段/source/ownership、未创建SystemTool和正常断开；is_configured=false可完成配置查询。
计划保留现有错误路径用例，新增独立的成功验收判定与结果证据（null/错误不计通过完整功能）；核对NodeCount/MaxNodeCount/InstanceType/ThreadsPerTask/ShutdownTimeTicks和原preferences/custom声明范围。不得为取得成功响应擅自配置节点或提交HPC工作负载。
输出本工作区 .local/coordination/parallel-02/hpc-plan.md，给出类型合同、普通测试、最小原生作业和完成判定。先计划，不实施或原生。

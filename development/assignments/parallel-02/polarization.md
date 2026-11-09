# D003两种SurfacePickup实际采用与恢复

本轮 parallel-02。权威主仓 C:/Users/tonge/Desktop/Zemax_MCP；Python C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe（-B -X utf8）。源码0.1.62，101工具/130分析；发行101/118。上一轮96项审查：3完整、38部分、55待条件，剩余93组；本轮目标恢复原生并新增3完整验收，候选仅HPC配置、MaterialModel和两种SurfacePickup。完整计数由协调者审查后更新。原生执行由runtime唯一负责，其他worker提交作业申请。分支普通检查必须显式PYTHONPATH为本工作区src并记录导入来源；最终验收针对集成主仓。共享入口以主仓当前内容为准，由runtime集成最小补丁。原有工作区和会话继续复用。
必读主仓 development/handoff.md、development/current.md、development/plan.md第7节，以及本项的最新证据和实际源码。当前第一阶段只提交具体实施计划及只读发现，写本任务plan文件；提交后结束本回合等待协调者审查。计划需列正式接口、现有缺口、输入与参考、原门槛、精确检查命令、原生作业、关闭/恢复与完成条件。此阶段不启动OpticStudio或原生测试。

任务职责：D003两种SurfacePickup实际采用与恢复
本轮改为处理ED-02.SurfacePickup.ChipZone、ED-02.SurfacePickup.MechanicalSemiDiameter。阅读主仓 scripts/probes/ED-02/pickup_solve_adoption018.py、tests/unit/test_pickup_probe_contracts.py、tests/native/test_extended_solves_live.py中两拒绝恢复用例、development/evidence/ED-02对应repeat报告及D003-D004/model集成记录。
复用已有三路回读：cell.Solve、GetSolveData.Type、_S_SurfacePickup。计划明确设置后/系统更新后/源值改变后/保存重载各时刻的模式、源面、比例偏移、目标值，代表光线到像面、失败部分改写与检查点恢复。SetSolveData Success不是完成标准；最终仍Automatic时保留真实拒绝。确认探针当前的任务层与Backend参数合同，提交可串行执行的两个子项作业。
修改只限本轮Pickup helper/定向测试；共享modeling/solve_support最小建议补丁交runtime集成。计划输出本工作区 .local/coordination/parallel-02/pickup-plan.md。不运行原生。

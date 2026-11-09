# 本轮独立证据与验收审查

本轮 parallel-02。权威主仓 C:/Users/tonge/Desktop/Zemax_MCP；Python C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe（-B -X utf8）。源码0.1.62，101工具/130分析；发行101/118。上一轮96项审查：3完整、38部分、55待条件，剩余93组；本轮目标恢复原生并新增3完整验收，候选仅HPC配置、MaterialModel和两种SurfacePickup。完整计数由协调者审查后更新。原生执行由runtime唯一负责，其他worker提交作业申请。分支普通检查必须显式PYTHONPATH为本工作区src并记录导入来源；最终验收针对集成主仓。共享入口以主仓当前内容为准，由runtime集成最小补丁。原有工作区和会话继续复用。
必读主仓 development/handoff.md、development/current.md、development/plan.md第7节，以及本项的最新证据和实际源码。当前第一阶段只提交具体实施计划及只读发现，写本任务plan文件；提交后结束本回合等待协调者审查。计划需列正式接口、现有缺口、输入与参考、原门槛、精确检查命令、原生作业、关闭/恢复与完成条件。此阶段不启动OpticStudio或原生测试。

任务职责：本轮独立证据与验收审查
只读独立审查本轮四候选与环境恢复门槛。你可读取主仓和其他固定工作区，不更改他人文件。核对原声明范围、普通通过/预期拒绝与原生成功的区别、数值参考独立性、原门槛、保存重载/恢复、close_attempted与实际关闭回执。重点指出MaterialModel探针、Pickup探针、HPC原生用例是否存在会误计完成或遗漏声明范围的断言。
先写本工作区 .local/coordination/parallel-02/reviewer-plan.md 和首轮具体审查发现；无需重复旧Hologram/FFT计算或测试。新的功能计划出来后由协调者派发第二阶段审查。

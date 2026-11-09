# D002 MaterialModel数值收口

本轮 parallel-02。权威主仓 C:/Users/tonge/Desktop/Zemax_MCP；Python C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe（-B -X utf8）。源码0.1.62，101工具/130分析；发行101/118。上一轮96项审查：3完整、38部分、55待条件，剩余93组；本轮目标恢复原生并新增3完整验收，候选仅HPC配置、MaterialModel和两种SurfacePickup。完整计数由协调者审查后更新。原生执行由runtime唯一负责，其他worker提交作业申请。分支普通检查必须显式PYTHONPATH为本工作区src并记录导入来源；最终验收针对集成主仓。共享入口以主仓当前内容为准，由runtime集成最小补丁。原有工作区和会话继续复用。
必读主仓 development/handoff.md、development/current.md、development/plan.md第7节，以及本项的最新证据和实际源码。当前第一阶段只提交具体实施计划及只读发现，写本任务plan文件；提交后结束本回合等待协调者审查。计划需列正式接口、现有缺口、输入与参考、原门槛、精确检查命令、原生作业、关闭/恢复与完成条件。此阶段不启动OpticStudio或原生测试。

任务职责：D002 MaterialModel数值收口
只处理ED-02.MaterialModel.Material。阅读主仓 scripts/probes/D002-MODEL_GLASS/model_glass_control018.py、tests/support/material_reference.py及development/evidence/ED-02/material-model-repeat20261108.md、上一轮D002-model集成记录。
复用B0/C1/C2/C3/B1/B2/B3矩阵，明确物理/经典d/F/C谱线、环境修正、直接ILDE.GetIndex及两个入射角Snell参考；Nd门槛1e-6+1e-7*abs(ref)，Vd门槛1e-5+1e-7*abs(ref)，Snell/直接比较沿用1e-10绝对/相对。旧Abbe59.99988524798844对60仍超限。计划必须指出当前探针是否完整覆盖原声明的dPgF、变量/solve、保存重载与恢复；原生未运行前不调整参考以贴合输出。功能修改限材料模型业务；不接手Pickup。
输出本工作区 .local/coordination/parallel-02/material-model-plan.md；提交最小实现/验收准备建议及原生作业，不运行原生。

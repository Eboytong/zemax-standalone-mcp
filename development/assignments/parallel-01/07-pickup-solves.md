# 复用任务：D003两项曲面拾取

负责人复用`zemax-p01-material-model`及其现有会话、分支和工作区；此前MaterialModel、Power Map交付继续保留。条目为`ED-02.SurfacePickup.ChipZone`、`ED-02.SurfacePickup.MechanicalSemiDiameter`。

先交计划，读取主项目最新台账、正式接口清单和原始调用。现有结果为ChipZone设置返回成功后仍为Automatic、机械半口径仍为Fixed；适配器已返回具体采用失败及检查点，恢复通过。

计划需区分设置当下未采用与后续更新覆盖，确认自动计算条件、目标列和源列、正式支持的依赖及保存重载行为。只有取得正式依据后才提出修复；已有接口不足则保存原始回读、限制和解除条件。不得用调用成功代替模式实际采用。

最小控制在独立模型中记录setter前、setter后、更新后、保存重载后的模式、值与拾取参数，并改变源值检查联动。成功、失败及恢复均记录配置、solve、修订和关闭。保留原条目数值门槛。

本阶段交付`.local/coordination/d003-pickup-plan.md`，审查后再准备探针或实现。原生执行由协调者串行安排。共享`modeling.py`、`backend.py`、请求模型补丁单列，台账和完成计数由协调者更新。

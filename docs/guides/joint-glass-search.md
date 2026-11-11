# 多材料槽位联合搜索

`get_glass_slots`读取当前顺序系统的材料段、目录身份及跳过原因。`run_analysis`的`glass_trials`请求支持`joint_slots`，每个槽位通过`group`引用`groups`列表。

```json
{"request":{"kind":"glass_trials","groups":[{"first_surface":1,"last_surface":2},{"first_surface":2,"last_surface":3}],"catalogs":["SCHOTT"],"joint_slots":[{"group":0,"materials":[{"catalog":"SCHOTT","material":"N-BK7"},{"catalog":"SCHOTT","material":"N-BAK4"}]},{"group":1,"materials":[{"catalog":"SCHOTT","material":"N-F2"},{"catalog":"SCHOTT","material":"N-SF5"}]}],"variables":[{"surface":3,"cell":"thickness","minimum":65,"maximum":110}],"objectives":[{"metric":"rms_spot"}],"search_strategy":"cartesian","max_evaluations":20,"total_budget_seconds":600}}
```

每个池自动保留原材料。`cartesian`枚举联合组合；`one_at_time`每次改变一个槽；`beam`按原生优化后的merit保留`beam_width`个候选并扩展下一槽。`pool_size`用于自动发现，显式`materials`直接读取指定材料，逐项按目录、Nd/Vd、波段和成本条件筛选；自动池按目录扫描并分批交还任务控制。

总时间预算从任务开始计时，在候选边界检查；正在执行的原生优化采用单候选预算与总剩余时间的较小值。材料发现、结果整理和资源关闭为串行原生调用，因此总运行时间可超过预算边界。结果记录实际优化预算、终止原因、失败候选和关闭计数。

每个组合从相同基线副本开始。`save_candidates=true`时保存独立模型，并接入[候选管理](candidates.md)；最佳模型重新加载和复算。`rows`返回逐候选数据、材料赋值、前后指标、边界检查和保存位置。spot单位为镜头单位，波前为waves，MTF无量纲。

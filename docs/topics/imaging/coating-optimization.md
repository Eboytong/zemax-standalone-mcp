# 固定膜系多条件优化

`run_analysis`的`coating_optimization`在独立原生副本中优化指定曲面的膜厚倍率，返回任务编号。适用空气与目录玻璃之间的固定层数、固定材料膜系；两方向均可设置目标。先通过`update_coating_layers`启用`use_layer_multiplier_and_offsets`。

```json
{
  "request": {
    "kind": "coating_optimization",
    "surface": 1,
    "variables": [{"layer": 1, "minimum": 0.2, "maximum": 1.8}],
    "objectives": [
      {"wavelength_um": 0.55, "angle_deg": 0, "direction": "inward", "polarization": "s", "metric": "reflection", "target": 0, "weight": 1},
      {"wavelength_um": 0.65, "angle_deg": 30, "direction": "outward", "polarization": "p", "metric": "transmission", "target": 1, "weight": 1}
    ],
    "algorithm": "DampedLeastSquares",
    "cycles": "Fixed_10_Cycles",
    "budget_seconds": 120,
    "save_best": true
  }
}
```

## 参数与实际采用

`variables`包含1—30个不同膜层，编号从1开始。倍率边界满足`0 < minimum < maximum <= 10`，起始倍率须在区间内；膜层存在厚度、折射率或消光Pickup时返回`SOLVE_PROTECTED`。膜层数、材料、折射率偏移和消光偏移按输入膜系保持。

`objectives`包含1—30个条件。每项的`wavelength`为系统波长编号，`wavelength_um`为明确的微米波长，两者互斥；都省略时用主波长。入射角0—89.9度，方向为`inward/outward`，偏振为`s/p`。`metric`可选`reflection/transmission/absorption`，目标0—1，权重必须大于0。

`algorithm`可选`DampedLeastSquares/OrthogonalDescent`；`cycles`可选`Fixed_1_Cycle/Fixed_5_Cycles/Fixed_10_Cycles/Fixed_50_Cycles`。优化使用1个原生核心，时间预算0—3600秒之间，默认120秒。预算由任务轮询在原生可取消边界执行。

每个条件生成原生配置，以GLSS设置前后介质、YFIE设置入射角；CONF/CODA生成S/P目标，CMGT/CMLT约束倍率。设置写入后回读，结果保留`native_mapping`、目标操作数位置、实际优化器设置及终态。

## 结果与膜厚定义

`before/after`含每个条件的S/P R/T/A；`summary.initial/optimized`给出加权均方误差和加权RMS误差，前者定义为`sum(weight × residual²) / sum(weight)`。原生评价函数同时包含边界权重，其数值单列在`native_optimization`，用于追踪原生执行。

物理厚度按目录中该层厚度乘倍率得到；相对波长膜厚按系统主波长换算，副本保留原主波长。性能数据来自原生CODA。`direct_before/direct_after`保留GetCoatingPerformance原始结果；本机24.2的该直接接口对相对膜厚使用查询波长换算，`direct_comparison_before/after`记录两者差异。绝对微米膜厚的两种出口已取得一致结果。

`constraints`按请求边界核对最终倍率。超界候选返回`COATING_BOUNDS_VIOLATED`；符合边界时比较前后目标，选择改善候选或基线，`summary.selected`给出选择。`save_best=true`将所选模型另存，路径为`summary.best_model`。

通过`get_task_result`分页读取`rows`，`series=0`读取前后目标曲线，并可用`export_analysis_image`导出。成功、失败和取消均保持原活动模型；优化副本和候选副本在任务结束时关闭。资源释放失败会返回原始操作错误及关闭错误，并要求重连。

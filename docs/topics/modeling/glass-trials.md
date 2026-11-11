# 玻璃贡献与自动替换试算

`run_analysis` 的 `glass_trials` 从本机原生材料目录筛选候选，在独立系统副本中替换指定镜片，再以相同变量、目标、配置、算法、循环数和优化预算运行 OpticStudio 局部优化。原材料同样参与优化，作为比较对照。

`include_contributions`默认true：贡献计算采用无穷远物方、空气起止、同轴Standard曲面、Y方向角度视场和三个递增波长，groups完整覆盖玻璃段。设为false后，材料试验采用本身的原生评价条件，支持有限共轭、非球面和单波长；reference_wavelength指定有效波长编号，field指定评价视场，采用Radial归一化。groups列出需要替换的材料段，内部保持同一目录材料且材料solve为Fixed。视场编号从1开始，target_group从0开始。

```json
{
  "request": {
    "kind": "glass_trials",
    "groups": [{"first_surface": 1, "last_surface": 2}, {"first_surface": 2, "last_surface": 3}],
    "target_group": 0,
    "catalogs": ["SCHOTT"],
    "nd_tolerance": 0.1,
    "vd_tolerance": 20,
    "max_candidates": 5,
    "blue_wavelength": 1,
    "reference_wavelength": 2,
    "red_wavelength": 3,
    "field": 2,
    "variables": [{"surface": 3, "cell": "thickness", "minimum": 65, "maximum": 110}],
    "objectives": [{"metric": "rms_spot", "target": 0, "weight": 1}],
    "algorithm": "DampedLeastSquares",
    "cycles": "Fixed_10_Cycles",
    "budget_per_candidate_seconds": 120,
    "save_candidates": true
  }
}
```

候选按原生 Nd、Vd、可用波段、ExcludeSubstitution 和可选的 `max_relative_cost` 筛选，再按归一化 Nd/Vd 距离排序，最多保留 `max_candidates` 个替换材料，另加原材料。成本 `?` 返回 null 及原始字符串；设置成本上限时会被筛除。材料状态随结果返回，Obsolete 材料仍可参与试算。加载目录中同名材料的归属须唯一。

优化变量为指定面的 `radius` 或 `thickness`。半径区间保持同号并避开零；厚度使用 CTGT/CTLT，半径换算为曲率后使用 CVGT/CVLT。原有半径/厚度 Variable 在副本中固定，其余 solve 受保护。越界候选返回失败记录。优化目标提供 `rms_spot`、`rms_wavefront`、`effective_focal_length`，每种最多一次，用户指定各项 target 和 weight。预算覆盖每个候选的原生局部优化过程。

每个候选返回优化前后 RMS 光斑、RMS 波前、EFL 和单频子午/弧矢 MTF。`rings=3` 控制 RSCE/RWCE 的原生高斯采样；`mtf_frequency=10` 使用当前系统 MTF 单位，MTFT/MTFS 固定 Samp=1、Grid=0、DataType=0。光斑和 EFL 使用镜头单位，波前使用 waves，MTF 为无量纲。原生 merit 参与排名，`change_from_optimized_control` 为相对优化后原材料的差值。

`contributions` 返回正则近轴矩阵参考、每块玻璃的折射率灵敏度及 Petzval 项。轴向/横向色差定义为长波减短波；贡献为参考波长处对该玻璃折射率的导数乘长短波折射率差。独立返回有限长短波色差与原生 AXCL/LACL；Petzval 使用原生像面曲率符号。各项定义、波长、逐段折射率及原生参考随结果保存。

关闭贡献时，`contributions`和逐候选`contributions_after`为null，`contribution_status`为`disabled by request`；原生材料回读、优化指标、保存重载和副本关闭照常返回。`get_glass_slots`将非Standard条件放入`contribution_conditions`，材料本身的目录和solve条件放入`skip_reasons`。

自主逐候选调用可按以下顺序组合：保存基线→修改指定材料→编辑MFE及几何边界→设置变量→调用原生局部/Global/Hammer优化→运行同条件分析→保存候选→恢复基线。统一预算搜索可用joint_slots与cartesian/one_at_time/beam；两条路径采用相同评价和预算时可直接比较。

调用返回任务编号，使用 `get_task_status` 和 `get_task_result` 读取。候选明细位于 `rows`，支持 start/count 分页；`series` 可由 `export_analysis_image` 导出。启用保存后，每个成功候选独立保存 ZOS 文件，最佳路径在 summary.best_model。成功、失败和取消均关闭自有副本，源模型及修订号保持原值。

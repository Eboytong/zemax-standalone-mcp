# NSC效率、ROI均匀性与原生优化

`run_analysis` 的 `nsc_efficiency` 请求在纯非序列系统中读取指定光源和矩形探测器，计算ROI功率、效率、CV及热点，并支持对象位置、角度、源功率扫描和原生局部优化。

```json
{
  "request": {
    "kind": "nsc_efficiency",
    "sources": [1],
    "detectors": [{"detector": 2, "x_start": 0, "y_start": 0, "width": 8, "height": 6}],
    "mode": "evaluate",
    "rays_per_source": 10000,
    "verification_rays_per_source": 40000,
    "random_seed": 42,
    "verification_seeds": [42, 43, 44]
  }
}
```

系统源单位采用无前缀Watts。探测器类型为`DetectorRectangle`、空间`DataType=0`。ROI索引从0开始，范围须完整位于探测器内，总像素数最多4096。源对象需提供正式`Power`与`NumberOfAnalysisRays`属性；本机已执行SourceRay和SourceRectangle。

## 指标与坐标

每个ROI返回功率、功率/所选光源总功率、像素平均功率、总体标准差、CV、峰均比、热点数、零值和无效像素数。CV采用全部ROI像素，包括零功率像素：

$$
\bar P=\frac{1}{N}\sum_i P_i,\qquad
\mathrm{CV}=\frac{\sqrt{\frac{1}{N}\sum_i(P_i-\bar P)^2}}{\bar P}.
$$

全暗ROI的CV为`null`；负值、非有限值或读取失败分别保留具体状态。热点为严格超过`hotspot_factor × 平均功率`的像素，默认倍数2。

网格`values[y][x]`为每像素W，坐标为探测器局部坐标的像素中心，长度采用镜头单位。像素面积和ROI面积使用镜头单位平方；平均辐照度为W/镜头单位平方。多个探测器分别除以同一总输入功率，可能重复接收同一光线；返回`double_count_warning`。效率排名使用各ROI效率的算术平均。

## 扫描

`mode="scan"`需要1—3个变量，每轴最多25个互异节点，笛卡尔积最多125个候选。变量的`cell`提供`XPosition/YPosition/ZPosition/TiltX/TiltY/TiltZ/Power`；位置采用镜头单位，角度为度，Power为W。位置和角度沿用对象参考坐标系。

```json
{
  "object": 1,
  "cell": "XPosition",
  "minimum": -1,
  "maximum": 1,
  "scan_values": [-1, 0, 1]
}
```

将上述对象放入请求的`variables`。`ranking`可选`efficiency`、`cv`或`target_error`；所有评分均按越小越好返回，效率评分取负号。初始状态参加排名。暗ROI和无效像素的CV不参加CV排名。

## 原生优化

设置`mode="optimize"`、`ranking="target_error"`，为每个ROI给出`target_power`，并定义1—10个有上下界的变量。Power变量须属于选定光源。原生入口为`OpenLocalOptimization`，评价函数为清空`NSDD`→`NSTR`→逐像素`NSDD`→`OSUM`；位置、角度和功率分别使用原生边界操作数，输出候选还会检查请求边界。

```json
{
  "request": {
    "kind": "nsc_efficiency",
    "sources": [1],
    "detectors": [{"detector": 2, "width": 8, "height": 6, "target_power": 0.8,
                   "power_weight": 1, "uniformity_weight": 1}],
    "mode": "optimize",
    "ranking": "target_error",
    "variables": [{"object": 1, "cell": "Power", "minimum": 0.1, "maximum": 2}],
    "algorithm": "DampedLeastSquares",
    "cycles": "Fixed_10_Cycles",
    "budget_seconds": 120
  }
}
```

优化目标是ROI总功率残差与各像素相对`target_power/N`的残差平方加权平均。`power_weight`控制总功率，`uniformity_weight`控制像素目标，默认0。均匀性目标与接收功率目标联合工作；CV作为独立结果返回。原生merit和工作流`target_error`分别记录其数值。

算法提供DLS和OrthogonalDescent，固定1/5/10/50轮、单核，`budget_seconds`为整个工作流预算。优化前重复计算两次MFE像素目标，差值大于`1e-12 W`返回`UNSTABLE_NSC_OBJECTIVE`。SourceRay通过正式RandomSeedCell设置NSTR种子；其他源采用原生NSTR可重复采样。独立复算通过追迹工具显式设置种子。部分原生源使用确定性采样，不同种子的输出可以相同。

## 结果与模型

初始模型、扫描候选和原生优化候选按同一基础采样评价；最佳候选以更多光线及`verification_seeds`复算。结果包含`baseline`、`candidates`、`verification`、`repeatability`、`summary`、`rows`、`grids`和`series`。`rows`可分页，网格和评分曲线可由`export_analysis_image`导出。

全部修改、清空与追迹均在自有模型副本中执行。源模型、源探测器缓冲区和修订保持。`save_best=true`将候选另存ZOS；候选中仅选定源启用分析光线，光线数为最后一次加密复算值。源模型已有Variable状态在副本中固定后，再设置本次优化变量；原模型solve保持。失败、取消和预算结束均关闭副本，关闭异常保留原始操作错误并要求重连。

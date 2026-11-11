# 非球面与制造几何评价

`run_analysis` 的 `manufacturing_geometry` 请求读取原生曲面矢高，在指定圆形口径内计算斜率、两个主曲率、球面偏离量及前后表面的厚度，并按输入阈值生成结论。

```json
{"request":{"kind":"manufacturing_geometry","surface":1,"back_surface":2,"aperture_radius":5,"sampling":"grid","samples":21,"meridians":16,"reference":{"kind":"vertex_sphere"},"limits":{"max_slope_rad":0.3,"max_abs_departure":0.02,"min_center_thickness":2,"min_edge_thickness":1}}}
```

支持 Standard、EvenAspheric 和 ExtendedPolynomial。曲面编号从1开始；`back_surface` 可省略，厚度阈值需要指定后表面。长度采用当前镜头单位，斜率角采用弧度，曲率采用镜头单位的倒数。所有调用为只读，保留当前配置、solve 和模型修订。

## 口径与参考

`aperture_radius` 是待评价圆盘的物理半径，`center_x/center_y` 是圆盘中心在前表面局部坐标中的位置，默认0。评价范围由请求给出，结果另记录原生半口径。

`reference.kind="vertex_sphere"` 采用曲面顶点半径；`specified_sphere` 使用显式 `radius`，0表示平面。参考球面在前表面局部坐标中以顶点为原点，可用 `vertex_sag` 增加轴向偏移。`departure` 为原生 sag 减参考球面 sag。它与原有几何规则中仅统计多项式项的指标有不同的参考定义。

## 采样与测量定义

`sampling="radial"` 为同心圆加方位角采样；`grid` 为圆盘内二维方格。两者都包含圆盘中心和明确采样的圆周。`samples` 为5—101的奇数，`meridians` 为4—64。默认 `refine=true`，进一步将每轴间隔、圆周角间隔和差分步长各减半。结果返回粗细采样的极值及绝对变化，极值位置对应实际采样点。

曲面导数从原生 `GetSag` 取值计算，X/Y一阶和纯二阶导数使用五点差分，混合二阶导数使用中心差分；由一、二基本形式求主曲率。`derivative_step` 可显式指定，默认口径半径的0.001倍。

厚度沿前表面局部 +Z 的物理直线测量。使用两表面的原生全局坐标变换，将直线变换到后表面局部坐标并求交。这样可处理偏心及倾斜后表面。`min_center_thickness` 对应所选圆盘中心，`min_edge_thickness` 为采样圆周的最小值；厚度保留该方向的正负号。

## 结果与阈值

返回任务编号后，通过 `get_task_status/get_task_result` 读取结果：

- `rows`：局部X/Y、sag、斜率、主曲率、球面偏离、厚度、有效性及失败原因，可分页。
- `summary.metrics`：各极值、采样点位置与编号；`invalid_count` 保留无效域或求交失败数量。
- `thresholds`：输入限值、实际值、位置及 `satisfied/violated/unverified`。存在无效点时保留 `unverified`。
- `convergence`：粗细两轮极值及变化；`actual_settings`：面型、基准、变换、配置和差分步长。
- `series/grids`：圆周几何曲线及二维 sag、偏离、斜率、曲率、厚度图；二维数据按 `values[y][x]`，圆盘外为 null，支持区域分页及 `export_analysis_image`。

`limits` 可设置 `max_abs_sag`、`max_slope_rad`、`max_abs_curvature`、`max_abs_departure`、`min_center_thickness`、`min_edge_thickness`。门槛由用户的具体工艺给出。采样预算 `budget_seconds` 默认120秒；取消在采样块边界生效，成功、失败和取消均保留模型状态。

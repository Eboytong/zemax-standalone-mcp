# 曲面与相位斜率

四种 `run_analysis.kind`：`surface_slope`、`surface_slope_cross`、`surface_phase_slope`、`surface_phase_slope_cross`。每项均要求正整数 `surface`，使用当前顺序配置。

```json
{"request":{"kind":"surface_slope","surface":1,"sampling":"S_65x65","data_type":"XSlope","remove_option":"BestFitSphere","best_fit_sphere":"MinimumVolume","reverse_direction":false}}
```

二维图使用 `S_33x33` 至 `S_8193x8193` 原生采样枚举，默认 `S_65x65`；提供 `show_as` 六种原生显示模式及可选 `contour_format`。截面图使用 `S_33` 至 `S_8193`，默认 `S_65`，提供有限角度 `angle`。两类请求分别约束其专属字段。

曲面斜率数据为 `TangentialSlope/SagittalSlope/XSlope/YSlope/SlopeModulus`。`remove_option` 支持 `None/BaseROC/BestFitSphere/BaseSag/CompositeSag`；最佳拟合球才接受 `best_fit_sphere`，其选项为 `MinimumVolume/MinimumRMS/MinimumRMSWithOffset`。只有 MinimumVolume 接受 `reverse_direction`。设置按移除模式、拟合条件、方向的依赖顺序写入并回读。`consider_off_axis_aperture` 控制离轴口径坐标。

相位斜率数据为 `PhaseSlopeTangential/PhaseSlopeSagittal/PhaseSlopeX/PhaseSlopeY/PhaseSlopeModulus`，提供 `remove_piston/remove_tilt_x/remove_tilt_y/remove_power`。这些开关默认关闭。

原生网格和截面曲线保留原始数组、标签、文本及无效点统计，复用任务、分页、绘图、报告和关闭。曲面坐标使用镜头单位；几何斜率为无量纲sag导数，相位斜率为cycles/镜头单位，即相位弧度导数除以2π。二维为`values[y][x]`；截面XData为局部X，YData两列为局部Y和所选斜率。曲面编号在创建Analysis前检查；设置拒绝时释放已创建资源并保留错误来源。

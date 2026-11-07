# 曲面与相位斜率

四种 `run_analysis.kind`：`surface_slope`、`surface_slope_cross`、`surface_phase_slope`、`surface_phase_slope_cross`。每项均要求正整数 `surface`，使用当前顺序配置。

```json
{"request":{"kind":"surface_slope","surface":1,"sampling":"S_65x65","data_type":"XSlope","remove_option":"BestFitSphere","best_fit_sphere":"MinimumVolume","reverse_direction":false}}
```

二维图使用 `S_33x33` 至 `S_8193x8193` 原生采样枚举，默认 `S_65x65`；提供 `show_as` 六种原生显示模式及可选 `contour_format`。截面图使用 `S_33` 至 `S_8193`，默认 `S_65`，提供有限角度 `angle`。两类请求分别约束其专属字段。

曲面斜率数据为 `TangentialSlope/SagittalSlope/XSlope/YSlope/SlopeModulus`。`remove_option` 支持 `None/BaseROC/BestFitSphere/BaseSag/CompositeSag`；最佳拟合球才接受 `best_fit_sphere`，其选项为 `MinimumVolume/MinimumRMS/MinimumRMSWithOffset`。只有 MinimumVolume 接受 `reverse_direction`。设置按移除模式、拟合条件、方向的依赖顺序写入并回读。`consider_off_axis_aperture` 控制离轴口径坐标。

相位斜率数据为 `PhaseSlopeTangential/PhaseSlopeSagittal/PhaseSlopeX/PhaseSlopeY/PhaseSlopeModulus`，提供 `remove_piston/remove_tilt_x/remove_tilt_y/remove_power`。这些开关默认关闭。

原生网格和截面曲线保留原始数组、标签、文本及无效点统计，复用任务、分页、绘图、报告和关闭。曲面坐标使用镜头单位；几何斜率为无量纲sag导数，相位斜率为cycles/镜头单位，即相位弧度导数除以2π。二维为`values[y][x]`；截面XData为局部X，YData两列为局部Y和所选斜率。曲面编号在创建Analysis前检查；设置拒绝时释放已创建资源并保留错误来源。

定义参考：[Surface Slope 2024 R2](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Surface_Slope.html)。四个专用接口反射见`verification/development/CV-01/surface-slopes034.json`。四项均完成代表性解析参考、设置回读、分页、图像、保存重载和生命周期验收，状态done；本轮证据见acceptance075.json及acceptance077.json。相位示例见`examples/phase-slopes077.json`。


2026-11-05：SurfaceSlope/SurfaceSlopeCross的五种量球面参考、平面、移除BaseROC、正负曲率圆锥面及三种最佳拟合球，共39613次检查最大差5.13e-10，固定容差1e-8+1e-7×参考值。保存重载、10张PNG、分页、无效面号、运行中取消与复用通过；截面取消请求前完成计算，状态succeeded/closed。见verification/development/CV-01/acceptance075.json。


2026-11-05：相位斜率二维图与截面完成，B002累计2/10。Binary2正负二次/四次相位五类导数、去功率、对称去活塞/倾斜及标准曲面零相位，36014次检查最大差5.79e-12，固定容差1e-8+1e-7×参考值。单位cycles/镜头单位；二维values[y][x]，截面XData=X、YData=[Y,相位导数/(2π)]。分页、10PNG、保存重载、失败/取消及复用和关闭通过。相关普通77通过、原生2通过；逐项未执行全量或wheel。证据verification/development/CV-01/acceptance077.json。MF-01三项原生探查均AS_Default且CFG导出/关闭成功，正式键、回读及输出契约待补，不计完成。

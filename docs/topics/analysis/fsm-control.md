# 双FSM离线闭环仿真

`run_analysis` 的 `fsm_control` 标定两个双轴平面镜到两个观测面的四自由度响应，模拟离散反馈，并对每个采样时刻的实际镜面姿态和输入扰动重新执行原生光线追迹。

输入光线状态为 `[x,y,l/n,m/n]`，观测为 `[plane1_x,plane1_y,plane2_x,plane2_y]`，镜面命令为 `[mirror1_X,mirror1_Y,mirror2_X,mirror2_Y]`。位置使用系统镜头单位，斜率无量纲，镜面角度为度。

```json
{
  "request": {
    "kind": "fsm_control",
    "start_surface": 1,
    "mirrors": [
      {"tilt_surface": 2, "mirror_surface": 3, "return_surface": 4},
      {"tilt_surface": 5, "mirror_surface": 6, "return_surface": 7}
    ],
    "observation_surfaces": [8, 9],
    "disturbances": [[0.01, -0.005, 0.0001, -0.00005], [0.01, -0.005, 0.0001, -0.00005]],
    "sample_period_seconds": 0.001,
    "gain": 0.5,
    "delay_samples": 0,
    "actuator_time_constant_seconds": 0,
    "limits_deg": [0.1, 0.1, 0.1, 0.1],
    "residual_tolerance": 0.000001,
    "validation_tolerance": 0.000001
  }
}
```

每个FSM由共点、相邻的前CoordinateBreak、Standard平面MIRROR、后CoordinateBreak组成。前断点Order=0，后断点Order=1，后断点X/Y旋转与前断点互逆；偏心与Z旋转为零。两个观测面位于镜组之后。运行中逐次检查观测面的全局变换保持固定。两观测面提供四个独立观测量；秩不足或条件数超过请求阈值时返回具体错误。

`disturbances` 为2–100个时刻的输入光线位置/斜率。请求显式设置采样周期；可设置执行器一阶时间常数、整采样延迟、角度范围和四通道测量噪声标准差。`seed` 固定噪声序列。控制器按延迟观测积分更新命令，再按角度范围截断；执行器按给定时间常数跟随命令。返回实际角度、下一命令、饱和通道和各时刻残差。

`response_matrix` 为观测位置对四轴镜面角度的原生中心差分；`disturbance_matrix` 为观测位置对输入状态的中心差分。`probe_angle_deg`、`probe_height`、`probe_slope` 控制标定步长。`condition_limit` 默认为1e8。

`native_residual` 为每时刻原生位置复算；`native_output_slope_residual` 和 `native_output_angle_residual_rad` 为末观测面的出射斜率和角度变化。原生复算与线性模型的最大差超过 `validation_tolerance` 时返回 `FSM_LINEAR_RANGE_EXCEEDED` 并保留已完成行。`summary` 返回稳定时间、收敛、饱和次数、条件数及一阶带宽。稳定时间采用显式采样周期，API执行耗时单独记录。

`rows` 支持分页，`series` 可导出残差曲线。所有计算使用模型工作副本，源镜面姿态和模型修订保持原值。

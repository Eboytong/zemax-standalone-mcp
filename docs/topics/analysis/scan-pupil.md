# 扫描镜与瞳共轭

`run_analysis` 的 `scan_pupil` 在系统副本中扫描实际平面镜，返回目标孔径面上的光束走离、采样通过率、光线分布、差分共轭、像面主光线角和扫描畸变。

模型按顺序包含输入面、前 CoordinateBreak、Standard 平面 MIRROR 和后 CoordinateBreak，四面相邻。前断点至镜面、镜面至后断点厚度均为0，形成位于镜面顶点的转轴。断点使用单一X或Y旋转、零偏心；后断点施加相反的扫描增量，使下游坐标保持基准。输入面至追迹终点的倾斜偏心用显式CoordinateBreak表示。

```json
{
  "request": {
    "kind": "scan_pupil",
    "start_surface": 1,
    "tilt_surface": 2,
    "mirror_surface": 3,
    "return_surface": 4,
    "pupil_surface": 7,
    "image_surface": 8,
    "axis": "Y",
    "angles_deg": [-1, 0, 1],
    "beam_radius": 1,
    "ray_density": 9,
    "wavelength": 1,
    "spacing": {"surface": 4, "values": [-45, -50, -55]},
    "save_best": true
  }
}
```

`angles_deg` 表示相对镜面名义姿态的角度增量，范围±15°；自动补入0°参考。`axis` 为绕轴名称，绕Y扫描主要在X方向产生偏转。所有坐标及厚度使用当前镜头单位，厚度保持原生有符号定义。`spacing` 可省略；启用时修改后断点至目标瞳面之间一个面的厚度。`beam_center_x/y` 指输入面局部坐标中的圆形平行光束中心。

`ray_density` 为3—21的奇数，方格中圆内点等权重采样；通过率为通过光线数/采样总数。结果分列追迹错误与截断。`cases` 包含镜面、瞳面、像面统计、局部光线数据和全局物理方向。反射奇偶性用于从原生顺序方向余弦恢复物理传播方向，每个扫描角同时与反射定律对照。

`conjugates` 用中心光线及X/Y位置、斜率正负扰动构造4×4差分矩阵，状态次序为 `(x,y,l/n,m/n)`。默认 `probe_height=0.001` 镜头单位、`probe_slope=0.00001`；可以减半检查收敛。每轴返回A/B/C/D，目标面相对镜面共轭的有符号局部Z距离为 `-B/D`。目标孔径在镜面侧的前像位置为 `B/A`，倍率为 `1/A`。目标面为系统光阑时，该前像给出镜面侧入瞳；`pupil_identity.is_system_stop` 保存实际归属。横轴耦合超过1e-6时标记coupled，并保留完整矩阵。

`beam_walk` 是目标面通过光线质心相对0°的移动。像面主光线位移对镜面弧度做过零最小二乘，返回扫描斜率、各点线性参考、绝对及相对畸变。主光线角使用像面局部方向，便于评价远心性。

间距候选按最小采样通过率从高到低、最大光束走离从低到高排列。最佳模型以0°名义姿态另存；所有计算在副本中进行，源模型、solve及修订号保持原值。返回任务编号，光线明细使用rows分页，series可由`export_analysis_image`绘图，resources记录关闭结果。

# 原生高斯光束查询


## 调用

```json
{"request":{"kind":"paraxial_gaussian_beam","wavelength":1,"waist_radius":0.05,"surface_1_to_waist":-10,"m2":4,"orientation":"Both","surface_start":1,"surface_end":6}}
```

```json
{"request":{"kind":"skew_gaussian_beam","wavelength":1,"field":2,"waist_radius_x":0.05,"waist_radius_y":0.08,"start_surface_to_waist":0,"orientation":"Both","start_surface":1,"end_surface":6}}
```

省略末曲面时取像面；曲面、波长和视场编号从1开始。近轴输入腰位置相对曲面1，skew输入腰位置相对起始曲面，正值表示腰位于其后。所有长度使用当前镜头单位，发散角为弧度。orientation 取 X、Y、Both。输入束腰半径必须正，M²不小于1。

## 计算来源和参数身份

本机专题窗口设置为 AS_Default。当前查询使用官方操作数 `GBPD/GBPP/GBPR/GBPS/GBPW/GBPZ` 和 `GBSD/GBSP/GBSR/GBSS/GBSW`，原生 `MFE.GetOperandValue` 直接接收参数，不修改评价函数编辑器。每行返回 `native_arguments` 和原始 `native_values`，`actual_settings` 保存请求和当前配置。资源归属于活动系统；该路径无独立分析窗口或工具实例。

近轴参数顺序为输出曲面、波长、UseX、嵌入基模腰半径、曲面1至腰位置、M²、0、0；skew参数顺序为起始曲面、输出曲面、波长、视场、起始曲面至腰位置、有符号腰半径、0、0。skew X 使用负腰半径、Y 使用正腰半径；公开请求保留正半径。

M²大于1时分别返回 embedded_TEM00 和 m2_scaled 两组；原生尺寸和发散半角按sqrt(M²)放大，位置、相位半径和瑞利长度保持嵌入基模定义。skew的瑞利长度由原生腰半径/tan(原生发散角)求得，并标记来源。skew方向由瞳边缘光线定义，随主光线移动。GBSS保留原生截面尺寸；受控平面系统Y视场20°时，Y向尺寸为垂直光束尺寸/cos(20°)，腰半径、距离及曲率保持沿光束的定义。原生在平坦波前处可返回1e10相位半径，结果保留该数值。

## 结果和检查

`rows` 提供每个曲面、方向和 beam_model 的完整参数，沿用start/count分页。`series` 按物理量、方向和beam_model分别给出曲线，横轴是曲面编号；可用既有图像导出工具。任务包含模型修订、配置、单位和原生版本。

输入越界在查询前拒绝。非有限数据及非正光束尺度返回INVALID_RESULT_DATA，查询异常保留原生异常类型、消息、操作数和参数。取消在每次查询前响应，已完成的行保留；仅完整取得所需物理量的行进入结果。

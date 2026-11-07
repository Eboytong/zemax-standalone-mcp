# Zernike 随视场与干涉图

## Zernike 系数随视场

```json
{"request":{"kind":"zernike_coefficients_vs_field","wavelength":1,"coefficient_type":"Standard","coefficients":[4,5,6],"sampling":"S_64x64","field_scan":"Plus_Y","field_density":21}}
```

使用本机 `IAS_ZernikeCoefficientsVsField`。`coefficient_type` 支持 Fringe、Standard、Annular；`coefficients` 为严格递增整数列表，Fringe 最大37、其余最大231。`[0]` 请求全部项。适配器生成原生逗号分隔字符串并回读确认。`obscuration` 取0至1之间，非零值用于Annular。四种 `field_scan` 为 `Plus_Y/Plus_X/Minus_Y/Minus_X`。

`field_density` 为2至1001的整数请求范围，实际采用由原生回读确认；`scale_minimum/scale_maximum` 默认0，表示原生自动尺度。请求使用当前有焦顺序配置和指定单色波长。

系数值单位为waves，曲线保留原生标签、坐标及数据；系数归属采用原生标签，视场轴尺度待原生验收确认。空曲线返回具体错误及原生文本路径。该专题独立于既有单视场 Zernike 系数表的解析和设置。

定义：[2024 R2 Zernike Coefficients vs. Field](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Zernike_Coefficients_vs_Field.html)。恢复原生启动后核对曲线标签与请求项的对应，使用相同瞳采样的单视场系数表交叉检查，预设容差 `1e-5 waves + 1%×参考值`。范围覆盖Fringe/Standard/Annular、四个扫描方向及多项选择。

## 干涉图

```json
{"request":{"kind":"interferogram","field":1,"wavelength":1,"beam_1":"Reference","beam_2":"Configuration_1","sampling":"S_64x64","scale_factor":1,"x_tilt":2,"y_tilt":0,"use_exit_pupil":false}}
```

使用本机 `IAS_Interferogram`。光束选择 Reference 或 Configuration_1至Configuration_20；执行前检查配置实际数量。`surface` 省略时使用像面。`field/wavelength` 为正整数；采样沿用32×32及以上的原生 SampleSizes。

`scale_factor` 为每波OPD对应条纹数，X/Y tilt单位为条纹。`ref_beam_1_to_vertex/ref_beam_2_to_vertex` 默认关闭，开启时要求缩放1。`consider_opl` 控制总光程差；`use_exit_pupil` 选择原生出瞳形状或归一化入瞳。`subaperture_x/y` 为归一化偏心，`subaperture_radius` 为归一化半径。显示方式和等高线格式由专属字段指定。

结果保留原生文本、标签与可用网格/曲线，条纹图数值的定义和尺度由原生标签及文本给出。定义：[2024 R2 Interferogram](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Interferogram.html)。原生恢复后以相同光束的均匀图和已知附加倾斜的周期图验收，再比较受控双配置OPD差；归一化图强度预设绝对差0.005，条纹周期相对差1%。

两项均复用任务状态、取消、结果分页、绘图、报告及资源关闭；实际设置保存在任务记录。成功/失败/取消释放和保存重载等待原生启动恢复。当前状态 implemented，逐项证据 `verification/development/CV-01/zernike-field035.json` 和 `verification/development/CV-02/interferogram035.json`。


2026-11-06：Zernike随视场完成。原生series为空时严格解析文本，系数列按标题或已回读的显式列表对应；[0]展开完整列表。field_density为区间数，N产生N+1点；负方向公开带符号坐标，native_x保留正距离。三类系数/四方向、Annular0.2遮挡、最高项6一致拟合，完整Fringe37与稀疏选择，共133次比较通过；系数容差1e-5waves+1%保持。12PNG、分页、保存重载、模型/solve保持、运行中取消和复用关闭通过。普通40通过，原生两个交付用例通过，证据verification/development/CV-01/acceptance089.json。高阶Annular231额外标量探查90s超时保留；执行高阶需相应预算。B002达到10/10，开始本批首次集中验收。


2026-11-06 Interferogram推进302：五组理想镜面条纹逐像素参考通过，最大误差5.270835989890088e-10，保持强度0.005容差。64样本的px=(列-31)/31、py=(行-31)/31；圆瞳外Reference/配置组合填1，同配置组合填0，原生网格未显式标记该区域。五次任务关闭、会话正常断连关闭。证据CV-02/progress302-interferogram.json；仍implemented，继续非零OPD/双配置、元数据与生命周期，B0044/10。


2026-11-06 Interferogram完成310：五组理想镜面、Cooke独立批量OPD、缩放/倾斜及交换光束、镜面/近轴双配置四分之一波长光程差通过；最大强度误差5.2709e-10，保持0.005容差。结果补归一化强度、相位约定、原生显示轴及瞳外有限填充值说明。设置选择/子孔径/vertex参考、5×4分页、有效PNG查看、失败/取消复用、保存重载及曲面/solve/配置/MFE保持、正常断连关闭通过。普通58通过、最终原生5通过，原始MCE精度拒绝及主光程符号参考定位分别保留。证据CV-02/acceptance310.json；B0045/10、剩余141组，下一条ContrastLoss。

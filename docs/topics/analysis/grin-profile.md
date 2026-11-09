# GRIN 折射率剖面

`run_analysis.kind=grin_profile` 使用本机 `IAS_GrinProfile`。必填 `surface`（从 1 开始）及 `show_index_vs=X/Y/Z`，默认波长 1；波长 0 沿用原生全部波长定义。支持顺序有焦及无焦系统，使用当前配置。

所选轴接受成对递增的 `minimum_x/maximum_x`、`minimum_y/maximum_y` 或 `minimum_z/maximum_z`。其余两轴通过 `x_value/y_value/z_value` 指定固定位置。扫描轴的固定值及其他轴的范围返回参数错误，避免原生活动轴属性产生覆盖。`minimum_index/maximum_index` 成对指定纵轴范围，省略保留原生默认设置。长度采用当前镜头单位，折射率无量纲。

设置写入回读保存在 `task.settings.native`，结果使用既有 `series` 分页和绘图。曲线明确返回扫描轴、坐标单位及折射率名称，原生标签保存在 `native_axes`；原生文本、头信息和消息保留。没有曲线与曲线维度错误分别报告 `NO_RESULT_DATA` 和 `INVALID_RESULT_DATA`。




RefN明确归属于材料族参考波长。请求与曲线数值保持，示例`examples/requests/gradium-profile629.json`。

624比较相同参考指数的常量Gradient5：GSF和无材料两路径在.58756um误差均小于5e-15，而Gradium仍最大3.3448e-8，排除共用SGRIN色散解释。631以零厚度平面界面、三种入射正弦和两个波长独立用Snell定律反推折射率，30条光线与GetIndex最大差小于3e-16，参考波长仍差3.3448e-8；实际入射折射采用该原生值。原1e-10+1e-9相对门槛保持。

629串行24组设置/48条直接光线：G14SFN/G14SFP正常区间各4个capping设置通过；右端延伸仅capping1/3通过，与手册一致。负偏移−.2mm的四个capping值均报错，其中两种轮廓的capping2/3共四组违背手册左端允许延伸规则。诊断测试通过生命周期和来源读取，`boundary_acceptance=false`单列。成功路径12个GRIN工具关闭，模型/solve/设置/MFE保持并断连。正反轮廓逐点GRD参考另存633，完整条目继续in_progress。


执行635补充正向G14SFP：五个DeltaZ1–2mm控制中，Gradium与GRD最大差6.250885e-6；同指数的常量Gradient5使用GSF/空材料均小于5e-15。633的12条完整曲线共1212点中，负向轮廓最大差4.5018e-8，正向轮廓最大差8.4130e-6，原门槛未通过。五个顶点的正/负误差比约−186.882889，作为待解释模式保存，未据此修正数值。



637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。



## 曲线波长归属

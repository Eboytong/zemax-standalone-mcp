# GRIN 折射率剖面

`run_analysis.kind=grin_profile` 使用本机 `IAS_GrinProfile`。必填 `surface`（从 1 开始）及 `show_index_vs=X/Y/Z`，默认波长 1；波长 0 沿用原生全部波长定义。支持顺序有焦及无焦系统，使用当前配置。

所选轴接受成对递增的 `minimum_x/maximum_x`、`minimum_y/maximum_y` 或 `minimum_z/maximum_z`。其余两轴通过 `x_value/y_value/z_value` 指定固定位置。扫描轴的固定值及其他轴的范围返回参数错误，避免原生活动轴属性产生覆盖。`minimum_index/maximum_index` 成对指定纵轴范围，省略保留原生默认设置。长度采用当前镜头单位，折射率无量纲。

设置写入回读保存在 `task.settings.native`，结果使用既有 `series` 分页和绘图。曲线明确返回扫描轴、坐标单位及折射率名称，原生标签保存在 `native_axes`；原生文本、头信息和消息保留。没有曲线与曲线维度错误分别报告 `NO_RESULT_DATA` 和 `INVALID_RESULT_DATA`。

原生参考使用 Gradient1：`n(r)=1.5-0.02*r^2+0.001*r`，`r=sqrt(x^2+y^2)`。参数名称回读为 n0、Nr2、Nr1；首次参考误将 Nr1 当作四次项，失败证据保留为 `grin-native054.xml`。修正参考后，X/Y/Z 每轴 101 点、保存重载前后共 606 次比较通过，预设容差 `1e-8+1e-7×参考值`，实际误差见 `.local/evidence/development/CV-02/grin-acceptance054/summary.json`。同时检查实际设置、模型状态、配置、solve、分页、PNG 和关闭。例子见 `examples/requests/grin-profile054.json`。


执行583–584：按本机手册241页公式独立读取GSF的SGRIN色散系数，用CopySystem中的正式GetIndex查询Gradium五个顶点偏移（DeltaZ1至2mm）。参考波长.58756um的五个值与441原GRIN曲线完全一致，排除仅图形显示误差；与GRD多项式最大差3.3448e-8。第二波长.55um按SGRIN公式最大差3.6260e-8，仍超原1e-10+1e-9×参考值。Ref n列与GRD一致，实际GetIndex采用值保留。源曲面/系统保持，副本关闭、原生会话断连。完整条目继续in_progress；后续需解释共用折射率求值精度，再完成反向、边界、capping与专题选择。证据.local/evidence/development/MA-01/progress584-native-index.json。

执行624–633：`task.settings.source_surface`新增实际曲面类型、材料、厚度、半口径和当前配置；Gradium还返回系统轮廓文件及正式参数1–8（步长、轴向偏移、RefN、偏心/倾斜、capping）。RefN明确归属于材料族参考波长。请求与曲线数值保持，示例`examples/requests/gradium-profile629.json`。

624比较相同参考指数的常量Gradient5：GSF和无材料两路径在.58756um误差均小于5e-15，而Gradium仍最大3.3448e-8，排除共用SGRIN色散解释。631以零厚度平面界面、三种入射正弦和两个波长独立用Snell定律反推折射率，30条光线与GetIndex最大差小于3e-16，参考波长仍差3.3448e-8；实际入射折射采用该原生值。原1e-10+1e-9相对门槛保持。

629串行24组设置/48条直接光线：G14SFN/G14SFP正常区间各4个capping设置通过；右端延伸仅capping1/3通过，与手册一致。负偏移−.2mm的四个capping值均报错，其中两种轮廓的capping2/3共四组违背手册左端允许延伸规则。诊断测试通过生命周期和来源读取，`boundary_acceptance=false`单列。成功路径12个GRIN工具关闭，模型/solve/设置/MFE保持并断连。正反轮廓逐点GRD参考另存633，完整条目继续in_progress。

普通631为97通过；原生629诊断1通过，632既有Gradient1 Z向回归1通过（202数值检查、保存重载、分页和PNG）。626/627左cap预期失败、628测试结果设置路径错误、630直接Backend调用包装错误全部保留；各失败会话已断连。证据`.local/evidence/development/MA-01/progress633-context-refraction-capping.json`。

执行635补充正向G14SFP：五个DeltaZ1–2mm控制中，Gradium与GRD最大差6.250885e-6；同指数的常量Gradient5使用GSF/空材料均小于5e-15。633的12条完整曲线共1212点中，负向轮廓最大差4.5018e-8，正向轮廓最大差8.4130e-6，原门槛未通过。五个顶点的正/负误差比约−186.882889，作为待解释模式保存，未据此修正数值。635源状态保持并断连；证据MA-01/progress636-positive-profile.json。


## 637–641证据同步（2026-11-07）

637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。

当前状态以[交接](../../../development/handoff.md)为准，历史计数属于对应执行记录。


## 曲线波长归属

每条曲线的`wavelength_number`标识选定系统波长，`index_definition`说明原生曲线的折射率定义。Gradium的`source_surface.gradium.reference_vertex_index`为材料族参考波长下的顶点参数。G14SFN受控模型在0.58756与0.55 µm的原生波长回读分别为1、2，101个相同坐标的曲线不同，顶点参考参数保持。见[波长证据](../../../development/evidence/MA-01/gradium-wavelength-20261109.md)。

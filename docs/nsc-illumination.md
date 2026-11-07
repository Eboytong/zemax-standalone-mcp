# 非序列几何MTF

`run_analysis.kind=nsc_geometric_mtf`适配当前纯非序列配置的DetectorRectangle，要求PsfWaveNumber=0。detector必填；maximum_frequency默认0表示原生自动Nyquist，单位cycles/mm。取两轴像素Nyquist较小值，显式超限返回SAMPLING_LIMIT。显示范围默认0至1。

省略path时使用当前探测器累积数据及trace_history；指定ZRD时使用任务工作副本回放，filter需显式ZRD输入。IAS_NSCGeometricMtf设置探测器、文件、筛选、频率与显示范围，并最终回读。成功、计算/结果失败和设置拒绝均沿既有任务关闭机制处理。

结果保留原生Tangential/Sagittal标签、series、文本和消息，可分页、绘图和报告。`direction_axes`说明Tangential=探测器局部Y、Sagittal=局部X；由三个非对称输入实验确认，证据progress491-asymmetric.json。镜头单位换算至毫米用于频率与Nyquist，不改变原始曲线值。

默认显示曲线保留原生采样值。点像原生曲线误差9.87512490668863e-7超过原门槛1e-7+1e-7×参考值。执行491使用X-only、Y-only和非对称三组1W像素分布；方向映射得到确认，多点全曲线正确轴最大误差6.233949225109559e-5。独立参考为归一化离散像素傅里叶和。

执行496将最大频率依次设为.625/299、.1、.3 cycles/mm，18个方向端点与精确DFT最大差5.551115123125783e-16；同一低频位置在全范围曲线内部仍超限。该实验确认误差随原生请求范围/重采样变化。完整曲线数值门槛继续保留；下一步探查正式原始节点出口或精确频率取样路径。所有原始曲线与误差保留。12次分析终态与关闭、1W功率及stdio断连通过，30次检查通过。

证据：`verification/development/NS-03/progress491-asymmetric.json`、`progress496-endpoint.json`及对应native XML；普通检查见BASE-01/ordinary495-targeted.xml。历史20项普通测试和点像/回放探查保留各自执行范围。NS-03其他专题的实际状态与正式接口缺口见CSV台账；当前原生启动正常。

请求示例见examples/illumination028_requests.json。

执行499完成公开运行时接口清单：AS_NSCGeometricMtf公开探测器/ZRD/筛选/最大频率/绘图范围，AR_NSCGeometricMtf只提供序列化曲线/通用数据和文本，未取得原始FFT节点或重采样控制。工具关闭、独立工作模型与断连通过。证据NS-03/progress499-outlets.json。解除完整曲线数值缺口需要正式原始节点/精确频率契约，或可复现的原生插值定义；继续保留implemented。

执行559–565新增显式`frequencies`路径。输入为1–301个非负、有限、严格递增的频率，单位cycles/mm；与非零`maximum_frequency`分别使用。每个正频率通过独立原生NSCGeometricMtf分析，将MaximumFrequency写为该值并回读，再读取对应终点。0频率读取原生DC节点。频率超出探测器Nyquist、原生终点不符、曲线身份变化或无效数据均明确失败。逐点路径复用复合任务、子任务关闭及取消机制。

```json
{"request":{"kind":"nsc_geometric_mtf","detector":4,"frequencies":[0,0.037,0.1,0.3,0.625]}}
```

结果`frequency_sampling=native_frequency_endpoints`，series仅含请求节点，rows/native_queries保留每个频率的实际设置、原生节点、子任务编号、消息、文件和输入归属。子任务结果中保留完整原生曲线与文本。省略frequencies时沿用`native_display_curve`，结果的numerical_precision说明已观察到的显示曲线精度及逐点入口。每个请求节点的原生分析次数为一次，运行成本随节点数增加。

native563四组用例覆盖单点与非对称1W输入、当前探测器与H4筛选ZRD；64个方向/频率对照最大差2.700854e-8，通过原1e-7+1e-7×参考值。设置、分页、PNG、活动子任务取消、复用、保存重载和关闭通过；PNG已查看。模型基线先保存重载一次以初始化原生光谱表默认值，随后逐项保持对象属性、solve、配置和系统设置。native565原有点像/回放及非对称诊断三项回归通过。560的请求包装失败、562的光谱表延迟初始化断言失败保留历史记录。逐点路径的数值验收与默认显示曲线的历史误差分别记录，见NS-03/acceptance565-endpoints.json。功能通过正式逐点路径完成，B006可计首次完成一次。

调用示例见examples/nsc-mtf-endpoints.json，schema见docs/tool-schemas.json。

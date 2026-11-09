# CV-01 Contrast Loss

通过`run_analysis`调用本机Contrast Loss Map分析，按视场和波长选择原生设置。采样值直接映射`SampleSizes_ContrastLoss`枚举；Frequency使用当前系统MTF频率单位。Normalize和ShowOPD为原生开关，所有字段经通用设置检查路径写入并回读。

```json
{"request":{"kind":"contrast_loss","field":1,"wavelength":1,"sampling":"S_41x41","frequency":50,"normalize":true,"show_opd":false}}
```

结果复用原生Analysis任务、状态、取消、结果读取和关闭路径；保留原生文本及其可用结构化曲线/网格，并附频率单位和分析标识。具体绘图栅格与OPD输出形式需在本机原生运行中确认。

本机反射、普通检查及原生运行待办见`.local/evidence/development/CV-01/contrast-loss032.json`。原生设置采用、结果数值与Analysis关闭等待BASE-04成功初始化。


2026-11-06 ContrastLoss完成314：原生四网格按描述识别子午/弧矢及相位/损失，保留原生轴并明确degrees和无量纲。受控离焦抛物面镜与独立双光线OPD的Moore-Elliott参考、自动5%截止频率、两方向有效瞳区逐点一致；最大损失误差2.3204e-14，相位误差1.3623e-11度，保持0.005和1e-5度容差。真实工作F数用于瞳剪切；Normalize/ShowOPD不改变原始网格。视场2/波长2、分页/有效PNG查看、错误/取消复用、保存重载及曲面/solve/配置/MFE保持、正常关闭通过。相关普通59通过，最终原生3通过，三种原生出口组合另由native313覆盖。证据CV-01/acceptance314.json；B0046/10，剩余140组，下一条FFT PSF Line/Edge Spread。

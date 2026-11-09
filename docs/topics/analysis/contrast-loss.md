# CV-01 Contrast Loss

通过`run_analysis`调用本机Contrast Loss Map分析，按视场和波长选择原生设置。采样值直接映射`SampleSizes_ContrastLoss`枚举；Frequency使用当前系统MTF频率单位。Normalize和ShowOPD为原生开关，所有字段经通用设置检查路径写入并回读。

```json
{"request":{"kind":"contrast_loss","field":1,"wavelength":1,"sampling":"S_41x41","frequency":50,"normalize":true,"show_opd":false}}
```

结果复用原生Analysis任务、状态、取消、结果读取和关闭路径；保留原生文本及其可用结构化曲线/网格，并附频率单位和分析标识。具体绘图栅格与OPD输出形式需在本机原生运行中确认。

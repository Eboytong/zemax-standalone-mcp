# Seidel 图

`run_analysis.kind=seidel_diagram` 对应本机 `IAS_SeidelDiagram`。请求示例：

```json
{"request":{"kind":"seidel_diagram","ignore_chromatic":false,"ignore_distortion":false,"suppress_frame":false,"plot_scale":0}}
```

三个开关直接对应 `IgnoreChromatic/IgnoreDistortion/SuppressFrame`；`plot_scale` 为有限非负数，默认0。全部设置逐项写入并回读。结果保留原生标签、尺度、文本以及原生可用的曲线或网格，接入现有任务、分页、绘图、报告与关闭路径。分析使用当前顺序配置。

2026-11-06 Cooke 原生探查确认设置采用，结果 `IsValid=true`；已检查的公开曲线、网格和散点数组均为空，`GetTextFile=false`。当前请求保留 `EXPORT_FAILED` 原始错误及关闭路径，条目状态为 blocked。证据见 `.local/evidence/development/CV-01/outlets265/summary.json`，早期实现记录为 `.local/evidence/development/CV-01/seidel-diagram034.json`。

解除条件：取得可用的正式数值或图形结果出口，完成最小复现后再与相同系统的 `seidel_coefficients` 逐面系数及求和交叉核对。已有 SeidelCoefficients 入口继续提供系数读取。

# Seidel 图

`run_analysis.kind=seidel_diagram`返回逐面未转换Seidel系数及所选面范围总和的分组条形图。计算定义依据本机2024 R2手册p.746，数据来自正式`SeidelCoefficients`。

```json
{"request":{"kind":"seidel_diagram","method":"coefficients","first_surface":2,"last_surface":5,"wavelength":2,"ignore_chromatic":true,"ignore_distortion":false,"plot_scale":0.5,"suppress_frame":false}}
```

默认auto采用系数路径。默认面范围1至像面前一面、波长1；色差和畸变显示开启，plot_scale=0自动，显示边框。IgnoreChromatic隐藏CLA/CTR，IgnoreDistortion隐藏DIST；plot_scale为镜头单位的±范围，suppress_frame控制绘图边框。面号、STOP及IMAGE标签实际归属检查后使用，像面排除。

rows包含逐面及Sum，series包含plot_kind=bar、面号刻度、单位及显示参数；保留实际原生波长设置、系数文本、分区来源、子任务最终关闭回执及原生适用性。原生显示系数精度保留，范围和按这些值计算。分页、PNG及报告沿用任务机制。

显式method=native沿用IAS_SeidelDiagram四个开关/尺度的写入回读；本机原生图表结果出口仍返回EXPORT_FAILED，显式面范围/波长设置返回UNSUPPORTED_SETTING。auto/coefficients使用正式系数路径提供可用图表。

58项逐面/总和/独立球差参考及原生生命周期验收通过；证据见[Seidel图完整验收](../../../development/evidence/CV-01/seidel-coefficient-diagram-20261109.md)。

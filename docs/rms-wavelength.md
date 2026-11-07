# RMS 随波长

`run_analysis.kind=rms_vs_wavelength` 对应本机 `RMSLambdaDiagram` 和 `IAS_RMSLambdaDiagram`，使用当前配置的有焦顺序系统。

```json
{"request":{"kind":"rms_vs_wavelength","field":0,"data_type":"SpotRadius","method":"RectArray","sampling":"S_256x256","wavelength_density":20}}
```

`field=0` 为全部视场，正整数选择单个视场。扫描范围取系统已定义波长的最小值和最大值。`wavelength_density` 接受 5–100、步长 5 的原生选项；返回实际曲线点数。

`data_type` 支持 `Wavefront/SpotRadius/Spot_X/Spot_Y/StrehlRatio`。Strehl 请求映射至本机 `StrehlRation` 枚举，每个波长采样点按单色计算。`reference` 支持 `Centroid/ChiefRay`。`RectArray` 使用 `sampling`，默认 64×64；`GaussQuad` 使用 `rings`，默认 3、范围 1–20。显式混用两类采样参数会被拒绝。

`plot_scale=0` 自动纵轴缩放；`use_dashes`、`use_polarization` 和 `show_diffraction_limit` 默认关闭。全部设置经逐项写入及回读；原生枚举按枚举值核对。此分析使用 `WaveDensity`，与 RMS 随视场的 `FieldDensity` 分别适配。

原生曲线保留标签和数值，波长轴为微米，光斑值为微米、波前为 waves、Strehl 为无量纲。曲线接入现有分页、绘图和报告；空曲线返回 `NO_RESULT_DATA` 并保留原生文本路径。任务沿用分析的取消、关闭和终态记录。

定义依据：[OpticStudio 2024 R2 RMS vs. Wavelength](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/RMS_vs_Wavelength.html)。本机接口、检查及原生待办见 `verification/development/CV-01/rms-wavelength033.json`。当前原生初始化超时；恢复后执行 Cooke 设置/结果/关闭检查，再以相同矩形瞳采样独立计算波长端点的 RMS，光斑容差预设为 `0.05 µm + 1%×参考值`，ChiefRay 波前为 `1e-5 waves + 1%×参考值`。多视场曲线归属、偏振、保存重载和失败/取消释放继续纳入原生验收。


2026-11-05：RMS随波长完成，B002累计4/10。五类量在Cooke扫描两端与同波长RMS曲线交叉检查，光斑及ChiefRay波前另以128×128矩形瞳追迹独立核对，全部固定容差通过。合计28次检查；设置最终组合回读、全部视场/GaussQuad/偏振/辅助线/虚线、分页、5PNG、保存重载及模型保持通过。运行中取消/关闭及下一分析复用通过；原生2通过，相关普通139通过。证据verification/development/CV-01/acceptance079.json。本项未执行全量或wheel，继续SystemCheck。

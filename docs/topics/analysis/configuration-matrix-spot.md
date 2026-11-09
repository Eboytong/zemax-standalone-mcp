# Configuration Matrix Spot

`run_analysis` accepts `kind="configuration_matrix_spot"`. The typed request exposes the `IAS_Spot` controls confirmed by OpticStudio 2024 R2 reflection: pupil pattern, reference point, displayed scale, ray color source, ray density, direction-cosine output, symbols, polarization, scattering, Airy disk, and lateral-color handling. The adapter writes and reads each value through the checked native setting path. Results use the shared analysis task and native text/data collector.

```json
{
  "request": {
    "kind": "configuration_matrix_spot",
    "pattern": "Hexapolar",
    "reference": "Centroid",
    "show_scale": "ScaleBar",
    "color_rays_by": "Config",
    "ray_density": 6,
    "use_polarization": false
  }
}
```

The controlled live case adds a second configuration. The native manual defines field rows and configuration columns; settings adoption and empty native outlets are recorded by the factory comparison.

2026-11-09：标准光斑的Configuration为原生选择器，双配置对照确认selector1计算活动配置；组合路径需显式切换物理配置，再使用当前选择器。标准SpotData没有逐光线维度，完整散点/独立参考/选项对应仍待完成，状态implemented。见[配置与参考合同](../../../development/evidence/CV-01/spot-current-configuration-20261109.md)。
2026-11-09：正式手册已确认视场逐行、波长/配置逐列及IgnoreLateralColor的独立参考语义。双配置模型下两种正式factory均无矩阵文本或SpotData，标准光斑对照正常；六诊断任务关闭、四类基线恢复及断开通过。当前仍implemented，下一步验证标准光斑组合的完整参考/散点/选项对应。见[证据](../../../development/evidence/CV-01/spot-factory-outlets-20261109.md)。

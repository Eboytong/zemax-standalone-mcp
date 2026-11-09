# Matrix Spot

`run_analysis` accepts `kind="matrix_spot"` and shares the checked `IAS_Spot` request with `configuration_matrix_spot`. It applies pattern, reference, scale display, ray color source, ray density, direction-cosine, symbol, polarization, scatter, Airy disk, and lateral-color settings, then runs the native MatrixSpot analysis through the standard result and close lifecycle.

```json
{
  "request": {
    "kind": "matrix_spot",
    "pattern": "Hexapolar",
    "reference": "Centroid",
    "show_scale": "ScaleBar",
    "color_rays_by": "Wavelength",
    "ray_density": 6
  }
}
```

The installed 2024 R2 API reflection confirms the analysis ID and settings. The native manual defines field rows and wavelength columns; controlled execution still returns no matrix output.

2026-11-09标准光斑组合合同：18项原生对照确认SpotData的波长槽重复当前分析聚合统计，单色需单独执行，15个getter均无逐光线维度。当前配置标准光斑采用selector1，物理配置单独记录。矩阵散点及IgnoreLateralColor完整对应仍待出口，保持implemented。见[证据](../../../development/evidence/CV-01/spot-current-configuration-20261109.md)。
2026-11-09：正式手册已确认视场逐行、波长/配置逐列及IgnoreLateralColor的独立参考语义。双配置模型下两种正式factory均无矩阵文本或SpotData，标准光斑对照正常；六诊断任务关闭、四类基线恢复及断开通过。当前仍implemented，下一步验证标准光斑组合的完整参考/散点/选项对应。见[证据](../../../development/evidence/CV-01/spot-factory-outlets-20261109.md)。

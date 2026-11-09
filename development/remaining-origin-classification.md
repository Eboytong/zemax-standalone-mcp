# 原定原生功能归属：96组

更新2026-11-08。原定96组已完成一轮审查，D010三组完整验收，当前剩余92组；本表保留原产品归属。当前范围由[scope.json](tracking/scope.json)维护，完整编号由[status.json](generated/status.json)生成。内建61组、官方STAR30组、官方HPC5组。本表记录产品能力归属；开发按[D001—D013](current.md)及组内顺序推进，逐项状态与动作见[D00x工作表](remaining-ranked.md)。

原115组分类及19组移出条目保存在[范围调整归档](archive/scope-native-only-20261108/README.md)。

## 内建功能适配（61组）

| 编号 | 功能 |
| --- | --- |
| `CO-01.DiffEfficiency2D` | 二维衍射效率完整范围 |
| `CO-01.DiffEfficiencyAngular` | 角度衍射效率完整范围 |
| `CO-01.DiffEfficiencyChromatic` | 波长衍射效率完整范围 |
| `CV-01.ConfigurationMatrixSpot` | 配置矩阵光斑 |
| `CV-01.FftSurfaceMtf` | FFT Surface MTF |
| `CV-01.FullFieldSpot` | 全视场光斑 |
| `CV-01.ISOElementDrawing` | ISO元件图 |
| `CV-01.MatrixSpot` | 矩阵光斑 |
| `CV-01.SeidelDiagram` | Seidel图 |
| `CV-01.SourceColorChart1931` | 1931色度图 |
| `CV-01.SourceColorChart1976` | 1976色度图 |
| `CV-02.BitmapFileViewer` | 位图查看器 |
| `CV-02.ExtendedDiffractionImageAnalysis` | 扩展衍射图像 |
| `CV-02.LightSourceAnalysis` | 光源分析 |
| `CV-02.PartiallyCoherentImageAnalysis` | 部分相干成像 |
| `CV-02.PowerFieldMapSettings` | 屈光力随视场Map |
| `CV-02.PowerPupilMapSettings` | 屈光力随瞳Map |
| `ED-01.Scattering` | 散射类型聚合范围 |
| `ED-01.Scattering.BSDF` | BSDF散射 |
| `ED-01.Scattering.ISScatterCatalog` | IS散射目录 |
| `ED-02.MaterialModel.Material` | 临时材料模型 |
| `ED-02.SolveExtensions018` | 扩展solve聚合范围 |
| `ED-02.SurfacePickup.ChipZone` | ChipZone曲面拾取 |
| `ED-02.SurfacePickup.MechanicalSemiDiameter` | 机械半口径拾取 |
| `ED-04.RayAimingWizard` | Ray Aiming完整生命周期 |
| `EXT-EXPORT.BlackBox` | 黑盒创建 |
| `EXT-EXPORT.CadMultipleConfigurations` | CAD多配置分层 |
| `EXT-EXPORT.CadSettings` | CAD实际格式与版本 |
| `EXT-EXPORT.EncryptedCoating` | 加密镀膜创建 |
| `EXT-EXPORT.LegacyLinework` | 旧线框导出 |
| `IM-01.GeometricBitmapImageAnalysis` | 几何位图图像分析 |
| `MA-01.AthermalGlassMap` | 消热差玻璃图 |
| `MA-01.DispersionDiagram` | 色散图 |
| `MA-01.DispersionvsWavelength` | 色散随波长 |
| `MA-01.GlassMap` | 玻璃图 |
| `MA-01.GradiumProfile` | Gradium完整剖面 |
| `MF-01.SagTable` | SagTable完整制造范围 |
| `MF-01.TestPlateList` | 样板目录 |
| `MF-01.ZemaxElementDrawing` | Zemax元件图 |
| `NS-01.Conversion` | 顺序转NSC混合组 |
| `NS-02.PathAnalysis` | 路径分析未分类功率 |
| `NS-03.DirectivityPlot` | 方向性图 |
| `NS-03.FluxvsWavelength` | 光通量随波长 |
| `NS-03.PhotoluminscenceViewer` | 光致发光查看器 |
| `NS-03.RadiantSourceModelViewerSettings` | Radiant光源模型查看器 |
| `NS-03.RoadwayLighting` | 道路照明 |
| `NS-03.ScatterFunctionViewer` | 散射函数查看器 |
| `NS-03.ScatterPolarPlotSettings` | 散射极坐标图 |
| `NS-03.SourceIlluminationMap` | 光源照明分布 |
| `NS-03.SourcePolarViewer` | 光源极坐标查看器 |
| `NS-03.SourceSpectrumViewer` | 光源光谱查看器 |
| `NS-04.NSCObjectViewer` | NSC对象查看器 |
| `NS-04.PartViewer` | 零件查看器 |
| `NS-04.PrescriptionDataSettings` | 系统说明文本报告 |
| `NS-04.PrescriptionGraphic` | 系统说明图 |
| `NS-04.SurfaceDataSettings` | 曲面数据报告 |
| `PO-01.PhaseAberration` | 相位像差 |
| `PO-01.PolarizationRayTrace` | 偏振光线专题 |
| `PO-01.Transmission` | 偏振透射专题 |
| `WP-01.BeamFileViewer` | 光束文件查看器 |
| `WP-01.FiberCouplingSettings` | 光纤耦合专题 |

## 官方STAR模块（30组）

| 编号 | 功能 |
| --- | --- |
| `CV-01.STAR2DDefPlot` | STAR二维形变图 |
| `CV-01.STARAlignCheck` | STAR对准检查 |
| `CV-01.STARIndexVsTemp` | STAR折射率随温度 |
| `CV-01.STARInspectFEA` | STAR FEA检查 |
| `CV-01.STARPerfChange` | STAR性能变化 |
| `CV-01.STARSysViewer` | STAR系统查看器 |
| `EXT-STAR.Components` | STAR组件管理 |
| `EXT-STAR.Components.configure` | STAR配置组件 |
| `EXT-STAR.Components.coordinate_breaks` | STAR组件坐标断点 |
| `EXT-STAR.Components.define` | STAR定义组件 |
| `EXT-STAR.Components.remove` | STAR删除组件 |
| `EXT-STAR.Components.remove_rbms` | STAR移除组件刚体运动 |
| `EXT-STAR.CoordinateTransform` | STAR坐标变换 |
| `EXT-STAR.FitDeformation` | STAR拟合形变 |
| `EXT-STAR.FitDirectIndex` | STAR拟合直接折射率 |
| `EXT-STAR.FitTemperature` | STAR拟合温度 |
| `EXT-STAR.FittedSamples` | STAR拟合采样 |
| `EXT-STAR.ImportDeformation` | STAR导入形变 |
| `EXT-STAR.ImportDirectIndex` | STAR导入直接折射率 |
| `EXT-STAR.ImportTemperature` | STAR导入温度 |
| `EXT-STAR.Materials.dndt` | STAR材料dn/dT |
| `EXT-STAR.Materials.refractive_index` | STAR材料折射率 |
| `EXT-STAR.Read` | STAR读取 |
| `EXT-STAR.RigidBody` | STAR刚体变换 |
| `EXT-STAR.ThermalControls` | STAR热控设置 |
| `EXT-STAR.UnloadDeformation` | STAR卸载形变 |
| `EXT-STAR.UnloadDirectIndex` | STAR卸载直接折射率 |
| `EXT-STAR.UnloadTemperature` | STAR卸载温度 |
| `EXT-STAR.UpdateMode` | STAR更新模式 |
| `EXT-STAR.VolumeControls` | STAR体积控制 |

## 官方HPC能力（5组）

| 编号 | 功能 |
| --- | --- |
| `EXT-HPC.GlobalOptimization` | HPC全局优化 |
| `EXT-HPC.HammerOptimization` | HPC Hammer优化 |
| `EXT-HPC.NSCTrace` | HPC非序列追迹 |
| `EXT-HPC.Settings` | HPC配置读取与采用 |
| `EXT-HPC.Tolerancing` | HPC公差任务 |

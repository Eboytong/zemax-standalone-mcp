# 剩余115组共同功能：能力归属分类

快照日期：2026-11-08；源码/发行0.1.62，B007为0/10。来源为[当前状态](generated/status.json)中的`canonical_remaining_ids`、[操作台账](ledgers/operations.csv)、[分析台账](ledgers/analyses.csv)及[排序表](remaining-ranked.md)。

分类按每项的主要交付对象互斥归类。能力归属、用户代码依赖、本机正式接口可用性和验收状态分别判断；完成状态仍以台账及逐项证据为准。

| 分类 | 数量 | 归属与边界 |
| --- | ---: | --- |
| OpticStudio内建功能适配 | 61 | 对应内建分析、编辑器、工具或导出；部分具体参数组合、结果出口及数值定义仍需确认。 |
| 官方STAR模块 | 30 | 24项EXT-STAR控制与6项CV-01.STAR专题；许可、FEA输入及本机执行待验收。 |
| 官方HPC能力 | 5 | 配置、NSC追迹、公差、全局优化和Hammer优化；计算配置与许可条件按台账记录。 |
| 自定义代码或DLL扩展接入 | 11 | 7项EX-01宿主/回调，2项ZPL宏solve，User散射和Kogelnik DLL。官方提供扩展机制，具体代码由DLL/宏/外部程序提供。 |
| Ansys跨产品接收端联动 | 2 | Speos实际导入LensSystem与Whitebox；需要Speos接收端。 |
| 接口可行性探查 | 6 | 5种solve的可用LDE单元格探查，以及独立MCE文件接口；原生支持范围仍待确定。 |
| 合计 | 115 | 按当前共同功能编号计数。 |

STAR和HPC归属官方能力。Speos归属Ansys产品联动。`EXT-`是本项目的工作包前缀，具体产品归属以上表为准。

11项扩展接入中，Kogelnik使用本机随安装提供的`us_hologram_kogelnik.dll`，来源记录见[DLL探查](evidence/CO-01/kogelnik-dll-p-projection-probe20261108.md)。其P投影定义仍待确认。三项衍射效率分析归入内建专题，其声明范围同时包含该DLL分支，相关验收依赖仍保留。BSDF、IS散射目录、GRD、TPD、ZBF及STAR输入属于资源条件；资源文件的外部来源与计算能力的产品归属分别记录。

官方说明参考：本机OpticStudio 2024 R2手册与DLL反射记录；Ansys《The STAR Tab》《ZOS-API.NET: An Overview》《Custom DLLs in OpticStudio》《The differences between ZOS-API, ZPL and DLL》及Speos导入说明。在线较新版本说明用于确认产品及扩展机制归属；本机支持范围沿用24.2探查证据。

## OpticStudio内建功能适配（61组）

| 编号 | 功能 | 接入与支持说明 |
| --- | --- | --- |
| `CO-01.DiffEfficiency2D` | 二维衍射效率完整范围 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CO-01.DiffEfficiencyAngular` | 角度衍射效率完整范围 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CO-01.DiffEfficiencyChromatic` | 波长衍射效率完整范围 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.ConfigurationMatrixSpot` | 配置矩阵光斑 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.FftSurfaceMtf` | FFT Surface MTF | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.FullFieldSpot` | 全视场光斑 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.ISOElementDrawing` | ISO元件图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.MatrixSpot` | 矩阵光斑 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.SeidelDiagram` | Seidel图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.SourceColorChart1931` | 1931色度图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-01.SourceColorChart1976` | 1976色度图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-02.BitmapFileViewer` | 位图查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-02.ExtendedDiffractionImageAnalysis` | 扩展衍射图像 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-02.LightSourceAnalysis` | 光源分析 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-02.PartiallyCoherentImageAnalysis` | 部分相干成像 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-02.PowerFieldMapSettings` | 屈光力随视场Map | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `CV-02.PowerPupilMapSettings` | 屈光力随瞳Map | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-01.Scattering` | 散射类型聚合范围 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-01.Scattering.BSDF` | BSDF散射 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-01.Scattering.ISScatterCatalog` | IS散射目录 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-02.MaterialModel.Material` | 临时材料模型 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-02.SolveExtensions018` | 扩展solve聚合范围 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-02.SurfacePickup.ChipZone` | ChipZone曲面拾取 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-02.SurfacePickup.MechanicalSemiDiameter` | 机械半口径拾取 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `ED-04.RayAimingWizard` | Ray Aiming完整生命周期 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `EXT-EXPORT.BlackBox` | 黑盒创建 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `EXT-EXPORT.CadMultipleConfigurations` | CAD多配置分层 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `EXT-EXPORT.CadSettings` | CAD实际格式与版本 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `EXT-EXPORT.EncryptedCoating` | 加密镀膜创建 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `EXT-EXPORT.LegacyLinework` | 旧线框导出 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `IM-01.GeometricBitmapImageAnalysis` | 几何位图图像分析 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MA-01.AthermalGlassMap` | 消热差玻璃图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MA-01.DispersionDiagram` | 色散图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MA-01.DispersionvsWavelength` | 色散随波长 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MA-01.GlassMap` | 玻璃图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MA-01.GradiumProfile` | Gradium完整剖面 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MF-01.SagTable` | SagTable完整制造范围 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MF-01.TestPlateList` | 样板目录 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `MF-01.ZemaxElementDrawing` | Zemax元件图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-01.Conversion` | 顺序转NSC混合组 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-02.PathAnalysis` | 路径分析未分类功率 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.DirectivityPlot` | 方向性图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.FluxvsWavelength` | 光通量随波长 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.PhotoluminscenceViewer` | 光致发光查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.RadiantSourceModelViewerSettings` | Radiant光源模型查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.RoadwayLighting` | 道路照明 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.ScatterFunctionViewer` | 散射函数查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.ScatterPolarPlotSettings` | 散射极坐标图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.SourceIlluminationMap` | 光源照明分布 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.SourcePolarViewer` | 光源极坐标查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-03.SourceSpectrumViewer` | 光源光谱查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-04.NSCObjectViewer` | NSC对象查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-04.PartViewer` | 零件查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-04.PrescriptionDataSettings` | 系统说明文本报告 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-04.PrescriptionGraphic` | 系统说明图 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `NS-04.SurfaceDataSettings` | 曲面数据报告 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `PO-01.PhaseAberration` | 相位像差 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `PO-01.PolarizationRayTrace` | 偏振光线专题 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `PO-01.Transmission` | 偏振透射专题 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `WP-01.BeamFileViewer` | 光束文件查看器 | 内建功能适配；具体设置、出口及验收缺口见台账。 |
| `WP-01.FiberCouplingSettings` | 光纤耦合专题 | 内建功能适配；具体设置、出口及验收缺口见台账。 |

## 官方STAR模块（30组）

| 编号 | 功能 | 接入与支持说明 |
| --- | --- | --- |
| `CV-01.STAR2DDefPlot` | STAR二维形变图 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `CV-01.STARAlignCheck` | STAR对准检查 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `CV-01.STARIndexVsTemp` | STAR折射率随温度 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `CV-01.STARInspectFEA` | STAR FEA检查 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `CV-01.STARPerfChange` | STAR性能变化 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `CV-01.STARSysViewer` | STAR系统查看器 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Components` | STAR组件管理 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Components.configure` | STAR配置组件 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Components.coordinate_breaks` | STAR组件坐标断点 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Components.define` | STAR定义组件 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Components.remove` | STAR删除组件 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Components.remove_rbms` | STAR移除组件刚体运动 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.CoordinateTransform` | STAR坐标变换 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.FitDeformation` | STAR拟合形变 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.FitDirectIndex` | STAR拟合直接折射率 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.FitTemperature` | STAR拟合温度 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.FittedSamples` | STAR拟合采样 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.ImportDeformation` | STAR导入形变 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.ImportDirectIndex` | STAR导入直接折射率 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.ImportTemperature` | STAR导入温度 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Materials.dndt` | STAR材料dn/dT | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Materials.refractive_index` | STAR材料折射率 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.Read` | STAR读取 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.RigidBody` | STAR刚体变换 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.ThermalControls` | STAR热控设置 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.UnloadDeformation` | STAR卸载形变 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.UnloadDirectIndex` | STAR卸载直接折射率 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.UnloadTemperature` | STAR卸载温度 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.UpdateMode` | STAR更新模式 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |
| `EXT-STAR.VolumeControls` | STAR体积控制 | 官方STAR；需相应许可及适用输入，本机执行验收待完成。 |

## 官方HPC能力（5组）

| 编号 | 功能 | 接入与支持说明 |
| --- | --- | --- |
| `EXT-HPC.GlobalOptimization` | HPC全局优化 | 官方HPC接口；配置/节点/许可及作业生命周期待验收。 |
| `EXT-HPC.HammerOptimization` | HPC Hammer优化 | 官方HPC接口；配置/节点/许可及作业生命周期待验收。 |
| `EXT-HPC.NSCTrace` | HPC非序列追迹 | 官方HPC接口；配置/节点/许可及作业生命周期待验收。 |
| `EXT-HPC.Settings` | HPC配置读取与采用 | 官方HPC接口；配置/节点/许可及作业生命周期待验收。 |
| `EXT-HPC.Tolerancing` | HPC公差任务 | 官方HPC接口；配置/节点/许可及作业生命周期待验收。 |

## 自定义代码或DLL扩展接入（11组）

| 编号 | 功能 | 接入与支持说明 |
| --- | --- | --- |
| `CO-01.KogelnikDLL.PProjection` | Kogelnik DLL P投影 | 随安装提供的用户面型DLL；P投影物理定义待确认。 |
| `ED-01.Scattering.User` | User散射 | 官方User散射机制；本机参数工厂异常，需兼容DLL及参数合同。 |
| `ED-02.ZPLMacro.ChipZone` | ChipZone宏solve | 官方ZPL宏solve机制；具体单元格的模式/宏名采用仍受阻。 |
| `ED-02.ZPLMacro.MechanicalSemiDiameter` | 机械半口径宏solve | 官方ZPL宏solve机制；具体单元格的模式/宏名采用仍受阻。 |
| `EX-01.CCallback` | C回调 | 用户程序/回调宿主接入；正式宿主、加载合同或受控执行结果仍待验收。 |
| `EX-01.NETCallback` | .NET回调加载 | 用户程序/回调宿主接入；正式宿主、加载合同或受控执行结果仍待验收。 |
| `EX-01.RegisterOperandCallback` | 操作数回调注册 | 用户程序/回调宿主接入；正式宿主、加载合同或受控执行结果仍待验收。 |
| `EX-01.StandaloneMacro` | 任意宏执行 | 用户程序/回调宿主接入；正式宿主、加载合同或受控执行结果仍待验收。 |
| `EX-01.UserAnalysisHost` | 用户分析宿主 | 用户程序/回调宿主接入；正式宿主、加载合同或受控执行结果仍待验收。 |
| `EX-01.UserDefinedCOM` | 用户COM扩展 | 用户程序/回调宿主接入；正式宿主、加载合同或受控执行结果仍待验收。 |
| `EX-01.UserOperandHost` | 用户操作数宿主 | 用户程序/回调宿主接入；正式宿主、加载合同或受控执行结果仍待验收。 |

## Ansys跨产品接收端联动（2组）

| 编号 | 功能 | 接入与支持说明 |
| --- | --- | --- |
| `EXT-SPEOS.Receiver.LensSystem` | Speos LensSystem接收端 | 官方Speos接收端联动；实际导入及单位/几何验收待完成。 |
| `EXT-SPEOS.Receiver.Whitebox` | Speos Whitebox接收端 | 官方Speos接收端联动；实际导入及单位/几何验收待完成。 |

## 接口可行性探查（6组）

| 编号 | 功能 | 接入与支持说明 |
| --- | --- | --- |
| `ED-02.CA_fill.LDEDiscovery` | CA_fill单元格 | 本机枚举存在，尚未取得可用LDE单元格；正式接口及适用范围待确认。 |
| `ED-02.DIA_fill.LDEDiscovery` | DIA_fill单元格 | 本机枚举存在，尚未取得可用LDE单元格；正式接口及适用范围待确认。 |
| `ED-02.DuplicateSag.LDEDiscovery` | DuplicateSag单元格 | 本机枚举存在，尚未取得可用LDE单元格；正式接口及适用范围待确认。 |
| `ED-02.InvertSag.LDEDiscovery` | InvertSag单元格 | 本机枚举存在，尚未取得可用LDE单元格；正式接口及适用范围待确认。 |
| `ED-02.MarginPercent.LDEDiscovery` | MarginPercent单元格 | 本机枚举存在，尚未取得可用LDE单元格；正式接口及适用范围待确认。 |
| `ED-03.MCE.independent_file` | 独立MCE文件接口 | 当前未发现独立MCE文件读写入口；现有系统文件可保存MCE。 |

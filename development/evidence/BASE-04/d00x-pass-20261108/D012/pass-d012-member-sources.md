# 最终成员来源表（STAR 专题 + 顺序散射）

- 唯一来源：`verification/development/BASE-01/probe/api-interfaces.json`（2026-11-06 采集的反射转储）。
- 版本：源码与发行基线 0.1.62；`development/evidence/CV-01`、`EXT-STAR/readiness193.json` 中的 STAR 状态均为 2026-11-06 历史，不作现时状态。
- 下表只列代码实际使用的成员；未使用项不列，避免"镜像转储"。

## 1. STAR 专题分析（AnalysisIDM）

| kind | 枚举成员 | 值 |
| --- | --- | --- |
| star_align_check | `AnalysisIDM.STARAlignCheck` | 155 |
| star_sys_viewer | `AnalysisIDM.STARSysViewer` | 156 |
| star_2d_def_plot | `AnalysisIDM.STAR2DDefPlot` | 157 |
| star_perf_change | `AnalysisIDM.STARPerfChange` | 158 |
| star_index_vs_temp | `AnalysisIDM.STARIndexVsTemp` | 159 |
| star_inspect_fea | `AnalysisIDM.STARInspectFEA` | 160 |

- 对应 `IAS_*Settings` 接口：转储**无**。仅记录"未文档化"，不推断不存在；创建走通用 `CreateNewAnalysis`，设置面运行时探测。
- 模块可用性：`IZOSAPI_Application.IsSTARModuleEnabled`（每次执行实时读取，`availability={enabled,source}`）。

## 2. 分析结果出口（ZOSAPI.Analysis.Data）

| 用途 | 成员 | 转储类型 |
| --- | --- | --- |
| 结果有效性 | `IAR_.IsValid` | `Boolean` |
| 标题 | `IAR_.HeaderData.Lines` | `String[]` |
| 消息数/取值 | `IAR_.NumberOfMessages` / `GetMessageAt(Int32)` | `Int32` / 方法 |
| 消息内容 | `IMessage.ErrorCode` / `IMessage.Text` | `ZOSAPI.Analysis.ErrorType` / `String` |
| 曲线数/取值 | `NumberOfDataSeries` / `GetDataSeries(Int32)` | `Int32` / 方法 |
| 曲线坐标 | `IAR_DataSeries.XData` / `YData`（`IMatrixData.Data`） | `IMatrixData` |
| 曲线标签 | `IAR_DataSeries.SeriesLabels` / `NumSeries` / `Description` / `XLabel` | `String[]` / `Int32` / `String` |
| 网格数/取值 | `NumberOfDataGrids` / `GetDataGrid(Int32)` | `Int32` / 方法 |
| 网格数值 | `IAR_DataGrid.Values` | `System.Double[,]` |
| 网格回退 | `IAR_DataGrid.ValueData` = `IMatrixData`（`Rows`/`Cols`/`Data`/`GetValueAt`/`ReadData`） | `ZOSAPI.Common.IMatrixData` |
| 网格轴 | `Nx`/`Ny`/`Dx`/`Dy`/`MinX`/`MinY`/`Description`/`XLabel`/`YLabel`/`ValueLabel` | `UInt32`/`Double`/`String` |
| 散点数/取值 | `NumberOfDataScatterPoints` / `GetDataScatterPoint(Int32)` | `Int32` / 方法 |
| 散点集合 | `IAR_DataScatterPoints.NumPoints` / `Points` / `GetPoint(Int32)` | `UInt32` / `IAR_ScatterPoint[]` / 方法 |
| 散点元素 | `IAR_ScatterPoint.X` / `Y` / `Value` | `Double` |
| 文本导出 | `IAR_.GetTextFile(String)` | 方法 → `Boolean` |

### ErrorType 严重性（`ZOSAPI.Analysis.ErrorType`，14 值）

仅 `Success=0` 非失败；其余 13 个均为具体失败码：`InvalidParameter=1`、`InvalidSettings=2`、`Failed=3`、`AnalysisUnavailableForProgramMode=4`、`NotYetImplemented=5`、`NoSolverLicenseAvailable=10000`、`ToolAlreadyOpen=10001`、`SequentialOnly=10002`、`NonSequentialOnly=10003`、`SingleNSCRayTraceSupported=10004`、`HPCNotAvailable=10005`、`FeatureNotSupported=10006`、`NotAvailableInLegacy=10007`。

## 3. 共享结果合同键（沿用既有）

| 键 | 结构 | 说明 |
| --- | --- | --- |
| `series` | `[{series,description,x_label,labels,x,y,point_count,...}]` | 曲线，沿用既有键 |
| `grids` | `[{grid,description,x_label,y_label,value_label,nx,ny,dx,dy,min_x,min_y,values,...}]` | `values[y][x]` 完整 Ny×Nx；区域分页由 `_page_task_result` 负责 |
| `scatter` | `[{scatter,native_scatter,description,x_label,y_label,value_label,count,points,invalid_count,points_source}]` | `points` 仅有限有效点，供 `plotting.export_image` |
| `rows` | `[{block,point,x,y,value,valid}]` | 散点扁平原始明细（含非法行），默认分页链路 |

不再设置独立散点键；`_page_task_result` 会把 `scatter[*].points` 剥离为 `point_count` 并置 `scatter_data_in_artifacts=True`。

## 4. 顺序散射能力（D007）

| 事实 | 成员 | 值 |
| --- | --- | --- |
| 八类设置接口 | `ISurfaceScatteringNone/Lambertian/Gaussian/ABg/ABgFile/BSDF/User/Catalog` | 类型专属设置对象 |
| ScatterFraction 宿主 | `Lambertian` / `Gaussian` / `BSDF` | 有 `ScatterFraction` |
| 无 ScatterFraction | `ABg` / `ABgFile` / `User` / `ISScatterCatalog` | 无该属性 |
| BSDF 资源 | `FileName` + `GetAvailableFileNames()` | 方法 |
| ABg/ABgFile 资源 | `ABgName`/`FileName` + `GetAvailableABgNames()`/`GetAvailableFileNames()` | 方法 |
| User 资源/参数 | `DLLName`/`NumberOfParameters`/`GetAvailableDLLNames()`/`GetParameterName`/`GetParameterValue`/`SetParameterValue` | 方法 |
| 目录 | `ISScatterCatalog`：`Angle`/`SampleSide`/`Sampling`/`GetFile()`/`SetFile()`/`GetAvailableFiles()` | 方法 |
| 浮动光阑 | `ISurfaceApertureFloating`：0 属性 0 方法 | 本构建非散射宿主 |
| 分析宿主开关 | 9 个分析设置 `ScatterRays`/`ScatterNSCRays` | 仅开关，非散射模型 |

占位值集合：`{'', '无', 'none'}`（来源见 `pass-d007-report.md` 第 2 节）；`n/a`/`null`/`-` 无依据，不纳入。

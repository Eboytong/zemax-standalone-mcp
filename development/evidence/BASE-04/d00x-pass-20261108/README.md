# D001—D013 本轮开发与审查汇总

日期：2026-11-08。权威源码位于 `C:/Users/tonge/Desktop/Zemax_MCP`。六个既有 DSH worker/session 已复用完成本轮 96 项审查。已发行 0.1.62 为 101 工具/118 分析；当前源码为 101 工具/130 分析，版本标识仍为 0.1.62。

本轮完整验收通过 3 项，为 D010 原生 Hologram1 的角度、波长和二维衍射效率。剩余 100 条源记录、95 个不同编号、93 组共同功能；集中检查累计 3/10。逐项部分实现和外部条件记录在 [清单](../../../tracking/d00x-pass-20261108.json) 及三份台账。

## 分组审查结果

| 开发组 | 本轮审查项 | 完整验收 | 部分交付 | 条件受阻/审计交付 |
| --- | ---: | ---: | ---: | ---: |
| D001 | 4 | 0 | 4 | 0 |
| D002 | 6 | 0 | 6 | 0 |
| D003 | 5 | 0 | 2 | 3 |
| D004 | 7 | 0 | 3 | 4 |
| D005 | 6 | 0 | 6 | 0 |
| D006 | 10 | 0 | 2 | 8 |
| D007 | 6 | 0 | 4 | 2 |
| D008 | 9 | 0 | 2 | 7 |
| D009 | 5 | 0 | 0 | 5 |
| D010 | 3 | 3 | 0 | 0 |
| D011 | 16 | 0 | 3 | 13 |
| D012 | 14 | 0 | 6 | 8 |
| D013 | 5 | 0 | 0 | 5 |

“部分交付”记录代码、解析、控制探针或参考改进；“条件受阻/审计交付”记录正式接口、历史实际结果和解除条件。完整功能计数按既有声明范围和数值门槛维护。

## 已集成成果

- D001：四个默认报告入口，真实留存文本重放、类型契约、分页和单位来源；正式选择与独立相位/Fresnel/耦合参考待验。
- D002：消热差图解析和独立热光参考、GlassMap 大小写身份匹配、MaterialModel 精确谱线控制、Gradium 资源身份及 637–639 复算。
- D003/D004：SurfacePickup 三路回读与联动探针、Power Map 四半径/非对称孔径控制和实际分页合同；原生零值、环有效性与拾取采用问题保持。
- D005：内部文件身份/键归属/报告解析与三份历史报告重放；N1/N2/N3 有界控制探针。LightSource/EXD/PCI 等专题完整输入和数值合同待验。
- D007：散射资源占位过滤、精确原生名称采用及写前拒绝。ScatterPolar 已有 181×90 网格，仍缺角度、单位和模型响应归属。User 异常作为历史产品诊断保留，已移出开发计划。
- D008：Prescription/Surface 默认原生文本报告入口、三份真实 UTF-16 样本与准备好的原生用例；选择范围和其余图纸/查看器出口仍待验。
- D010：三项 Hologram1 完整证据接受；S/P 各 4096 节点复算最大误差 5.753e-11/5.245e-11，门槛为 1e-6+1e-5×abs(reference)。
- D011：三类 STAR 卸载有类型请求、前后状态、源资源存在、取消和恢复路径；其余数据、材料与控制范围逐项审计。
- D012：六个 STAR kind-only 分析入口、实时模块状态、设置单次回读、完整网格与散点、原生致命消息、Backend 分页和 PNG 合同；原生许可、FEA 与专题数值待验。
- D006、D009、D013：逐项核对现有接口、原生出口/失败与原门槛，保留具体输入、格式、HPC 配置或作业解除条件。

## 实际检查

各次结果独立列示，重叠测试不相加。集成命令、源码文件、XML 和原生准备状态分别见：

| 范围 | 结果/入口 |
| --- | --- |
| D010 | 原生历史 384 检查；本轮独立全网格复算及主仓 122 定向普通检查，见 [D010](../../CO-01/hologram1-review-20261108/README.md) |
| D001 | 主仓 144；schema 45；既有消费者 56，见 [D001](../../PO-01/pass-d001-20261108.md) |
| D002 | 热光参考相关 77；材料模型相关 97；留存数值误差见 [材料图表审查](../../MA-01/pass-d002-reports-review-20261108.md) |
| D003/D004 | 支持审计 169；控制程序 53（9 拾取、17 Power 探针、27 PowerMap），见 [集成](D003-D004/model/integration-power-pickup-controls.md) |
| D005 | 94（53 解析/身份、41 控制），见 [集成](D005/integration-d005-controls.md) |
| D008 | 101项集合为100 passed/1 skip；132项集合为131 passed/1 skip；E1 产物补齐后该跳过项单独1 passed，见 [集成](D008-reports/integration-gradium-reports.md) |
| D009/D013 | CAD 63、HPC 34、关联广域 120，见 [审计](../pass-d009-d013-20261108.md) |
| D011 | 83（47 STAR、25 控制、11 材料，其中 21 卸载）；model_adaptation 另 16，见 [集成](D011/integration-star-unload.md) |
| D007/D012 | 以 [主仓集成报告](integration-star-analyses-scattering.md) 和对应 XML 为准；worker 最终定向 225，非主仓集中发行结果 |
| schema 与状态 | 本轮真实 stdio list_tools 和开发统计定向检查见 final-checks.json |

收尾检查：真实stdio导出101个工具schema并正常退出；六个STAR及两个文本报告示例通过实际请求模型。开发状态17项通过；STAR原生准备逻辑6项通过，1个原生用例仅收集、未执行。实际回执见[final-checks.json](final-checks.json)及[准备逻辑检查](star-native-probe-check.json)。

既有原生验收与本轮离线执行分别标注。worker 早期普通测试记录作为该工作区历史检查保留；本轮未启动一次集中发行验收。

## 原生执行与外部条件

runtime-recovery-01/02/05 均在 application_create 阶段 180 秒超时。自有子进程树已停止，未取得正常 CloseApplication 回执；不把进程退出写成正常 API 关闭。详见 [环境证据](../runtime-phase-environment-20261108.md)。其后仅执行普通测试、准备作业和留存数据复算。

STAR 的 IsSTARModuleEnabled=false 为 2026-11-06 历史实测；当前状态由新适配器执行时实时读取。完成其余验收需要可创建应用、实际启用的模块及受控 FEA。HPC 查询需要非空 IHPCSettings 与实际字段；is_configured=false 可满足配置读取范围，四类节点作业另需各自完整生命周期。

正式接口/出口缺口包括专题输入选择、空图形/数据出口、拾取未采用、BSDF 占位资源、ScatterPolar 角轴/单位、路径未分类功率、CAD 实际版本/配置层采用。资源缺口包括匹配 ISX、可核对的专题输入与独立 FEA。

数值缺口按原门槛保留：MaterialModel Abbe、消热差缺少的 5 条材料数据及解析色散导数 4 点、Gradium 10/11 阶与左端 capping、FFT Surface MTF 离轴投影与幅度支持域。FFT 留存控制在三种间距下的离轴最小最大差仍约 0.165461，大于 0.005。

## 下一步

本轮在全部 96 项审查和批准补丁集成后停止。先与用户讨论 application_create、STAR/HPC 和正式接口/资源条件；取得新条件后按 D001 起的最早可执行项恢复。各条目的具体命令和解除条件见台账及下表。后续继续复用六个原 worker/session。

## 逐项审查索引

| 开发组 | 共同功能 | 本轮结论 | 证据 |
| --- | --- | --- | --- |
| D001 | `PO-01.PhaseAberration` | reviewed_partial | [pass-d001-20261108.md](../../../../development/evidence/PO-01/pass-d001-20261108.md) |
| D001 | `PO-01.PolarizationRayTrace` | reviewed_partial | [pass-d001-20261108.md](../../../../development/evidence/PO-01/pass-d001-20261108.md) |
| D001 | `PO-01.Transmission` | reviewed_partial | [pass-d001-20261108.md](../../../../development/evidence/PO-01/pass-d001-20261108.md) |
| D001 | `WP-01.FiberCouplingSettings` | reviewed_partial | [pass-d001-20261108.md](../../../../development/evidence/PO-01/pass-d001-20261108.md) |
| D002 | `MA-01.GlassMap` | reviewed_partial | [pass-d002-reports-review-20261108.md](../../../../development/evidence/MA-01/pass-d002-reports-review-20261108.md) |
| D002 | `MA-01.AthermalGlassMap` | reviewed_partial | [pass-d002-reports-review-20261108.md](../../../../development/evidence/MA-01/pass-d002-reports-review-20261108.md) |
| D002 | `MA-01.DispersionDiagram` | reviewed_partial | [pass-d002-reports-review-20261108.md](../../../../development/evidence/MA-01/pass-d002-reports-review-20261108.md) |
| D002 | `MA-01.DispersionvsWavelength` | reviewed_partial | [pass-d002-reports-review-20261108.md](../../../../development/evidence/MA-01/pass-d002-reports-review-20261108.md) |
| D002 | `ED-02.MaterialModel.Material` | reviewed_partial | [integration-material-model.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D002-model/integration-material-model.md)；[material-model-repeat20261108.md](../../../../development/evidence/ED-02/material-model-repeat20261108.md) |
| D002 | `MA-01.GradiumProfile` | reviewed_partial | [integration-gradium-reports.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008-reports/integration-gradium-reports.md) |
| D003 | `ED-02.SurfacePickup.ChipZone` | reviewed_partial | [integration-power-pickup-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/model/integration-power-pickup-controls.md) |
| D003 | `ED-02.SurfacePickup.MechanicalSemiDiameter` | reviewed_partial | [integration-power-pickup-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/model/integration-power-pickup-controls.md) |
| D003 | `ED-04.RayAimingWizard` | reviewed_deferred | [pass-d003-d004-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/support/pass-d003-d004-report.md) |
| D003 | `NS-01.Conversion` | reviewed_deferred | [pass-d003-d004-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/support/pass-d003-d004-report.md) |
| D003 | `ED-02.SolveExtensions018` | reviewed_deferred | [pass-d003-d004-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/support/pass-d003-d004-report.md) |
| D004 | `CV-02.PowerFieldMapSettings` | reviewed_partial | [integration-power-pickup-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/model/integration-power-pickup-controls.md) |
| D004 | `CV-02.PowerPupilMapSettings` | reviewed_partial | [integration-power-pickup-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/model/integration-power-pickup-controls.md) |
| D004 | `CV-01.SeidelDiagram` | reviewed_deferred | [pass-d003-d004-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/support/pass-d003-d004-report.md) |
| D004 | `CV-01.FullFieldSpot` | reviewed_deferred | [pass-d003-d004-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/support/pass-d003-d004-report.md) |
| D004 | `CV-01.MatrixSpot` | reviewed_deferred | [pass-d003-d004-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/support/pass-d003-d004-report.md) |
| D004 | `CV-01.ConfigurationMatrixSpot` | reviewed_deferred | [pass-d003-d004-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D003-D004/support/pass-d003-d004-report.md) |
| D004 | `CV-01.FftSurfaceMtf` | reviewed_partial | [fft-surface-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D004-FFT/fft-surface-report.md) |
| D005 | `WP-01.BeamFileViewer` | reviewed_partial | [integration-d005-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D005/integration-d005-controls.md) |
| D005 | `CV-02.BitmapFileViewer` | reviewed_partial | [integration-d005-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D005/integration-d005-controls.md) |
| D005 | `IM-01.GeometricBitmapImageAnalysis` | reviewed_partial | [integration-d005-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D005/integration-d005-controls.md) |
| D005 | `CV-02.LightSourceAnalysis` | reviewed_partial | [integration-d005-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D005/integration-d005-controls.md) |
| D005 | `CV-02.ExtendedDiffractionImageAnalysis` | reviewed_partial | [integration-d005-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D005/integration-d005-controls.md) |
| D005 | `CV-02.PartiallyCoherentImageAnalysis` | reviewed_partial | [integration-d005-controls.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D005/integration-d005-controls.md) |
| D006 | `NS-03.SourceSpectrumViewer` | reviewed_partial | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `NS-03.FluxvsWavelength` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `NS-03.DirectivityPlot` | reviewed_partial | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `CV-01.SourceColorChart1931` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `CV-01.SourceColorChart1976` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `NS-03.SourcePolarViewer` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `NS-03.SourceIlluminationMap` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `NS-03.PhotoluminscenceViewer` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `NS-03.RadiantSourceModelViewerSettings` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D006 | `NS-03.RoadwayLighting` | reviewed_deferred | [pass-report-d006-d002.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-report-d006-d002.md)；[review.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/review.md)；[pass-d006-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D006/pass-d006-items.json) |
| D007 | `ED-01.Scattering.BSDF` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d007-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D007/pass-d007-report.md) |
| D007 | `ED-01.Scattering.ISScatterCatalog` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d007-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D007/pass-d007-report.md) |
| D007 | `NS-03.ScatterFunctionViewer` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d007-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D007/pass-d007-report.md) |
| D007 | `NS-03.ScatterPolarPlotSettings` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d007-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D007/pass-d007-report.md) |
| D007 | `NS-02.PathAnalysis` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d007-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D007/pass-d007-report.md) |
| D007 | `ED-01.Scattering` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d007-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D007/pass-d007-report.md) |
| D008 | `NS-04.PrescriptionDataSettings` | reviewed_partial | [integration-gradium-reports.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008-reports/integration-gradium-reports.md) |
| D008 | `NS-04.SurfaceDataSettings` | reviewed_partial | [integration-gradium-reports.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008-reports/integration-gradium-reports.md) |
| D008 | `MF-01.TestPlateList` | reviewed_deferred | [pass-d008-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-report.md)；[pass-d008-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-items.json) |
| D008 | `MF-01.SagTable` | reviewed_deferred | [pass-d008-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-report.md)；[pass-d008-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-items.json) |
| D008 | `CV-01.ISOElementDrawing` | reviewed_deferred | [pass-d008-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-report.md)；[pass-d008-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-items.json) |
| D008 | `MF-01.ZemaxElementDrawing` | reviewed_deferred | [pass-d008-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-report.md)；[pass-d008-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-items.json) |
| D008 | `NS-04.PrescriptionGraphic` | reviewed_deferred | [pass-d008-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-report.md)；[pass-d008-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-items.json) |
| D008 | `NS-04.NSCObjectViewer` | reviewed_deferred | [pass-d008-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-report.md)；[pass-d008-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-items.json) |
| D008 | `NS-04.PartViewer` | reviewed_deferred | [pass-d008-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-report.md)；[pass-d008-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D008/pass-d008-items.json) |
| D009 | `EXT-EXPORT.CadSettings` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D009 | `EXT-EXPORT.CadMultipleConfigurations` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D009 | `EXT-EXPORT.LegacyLinework` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D009 | `EXT-EXPORT.BlackBox` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D009 | `EXT-EXPORT.EncryptedCoating` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D010 | `CO-01.DiffEfficiencyAngular` | accepted | [README.md](../../../../development/evidence/CO-01/hologram1-review-20261108/README.md) |
| D010 | `CO-01.DiffEfficiencyChromatic` | accepted | [README.md](../../../../development/evidence/CO-01/hologram1-review-20261108/README.md) |
| D010 | `CO-01.DiffEfficiency2D` | accepted | [README.md](../../../../development/evidence/CO-01/hologram1-review-20261108/README.md) |
| D011 | `EXT-STAR.Read` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.UpdateMode` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.Materials.refractive_index` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.Materials.dndt` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.ThermalControls` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.VolumeControls` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.ImportDeformation` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.FitDeformation` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.ImportTemperature` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.FitTemperature` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.ImportDirectIndex` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.FitDirectIndex` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.FittedSamples` | reviewed_deferred | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.UnloadDeformation` | reviewed_partial | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.UnloadTemperature` | reviewed_partial | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D011 | `EXT-STAR.UnloadDirectIndex` | reviewed_partial | [integration-star-unload.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/integration-star-unload.md)；[pass-d011-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D011/pass-d011-items.json) |
| D012 | `EXT-STAR.Components.define` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `EXT-STAR.Components.configure` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `EXT-STAR.Components.coordinate_breaks` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `EXT-STAR.CoordinateTransform` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `EXT-STAR.RigidBody` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `EXT-STAR.Components.remove_rbms` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `CV-01.STARInspectFEA` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `CV-01.STARAlignCheck` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `CV-01.STAR2DDefPlot` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `CV-01.STARIndexVsTemp` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `CV-01.STARPerfChange` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `CV-01.STARSysViewer` | reviewed_partial | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `EXT-STAR.Components.remove` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D012 | `EXT-STAR.Components` | reviewed_deferred | [integration-star-analyses-scattering.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/integration-star-analyses-scattering.md)；[pass-d012-report.md](../../../../development/evidence/BASE-04/d00x-pass-20261108/D012/pass-d012-report.md) |
| D013 | `EXT-HPC.Settings` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D013 | `EXT-HPC.NSCTrace` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D013 | `EXT-HPC.Tolerancing` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D013 | `EXT-HPC.GlobalOptimization` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |
| D013 | `EXT-HPC.HammerOptimization` | reviewed_deferred | [pass-d009-d013-20261108.md](../../../../development/evidence/BASE-04/pass-d009-d013-20261108.md)；[pass-d009-d013-items.json](../../../../development/evidence/BASE-04/d00x-pass-20261108/D009-D013/pass-d009-d013-items.json) |

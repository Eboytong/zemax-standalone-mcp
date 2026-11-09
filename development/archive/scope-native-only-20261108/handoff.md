# 当前交接：0.1.62 已发行，B007 0/10

更新2026-11-08。源码及发行0.1.62，101工具/118分析。B006十项完成，集中检查通过；完整清单与证据见[evidence/BASE-04/release062.json](evidence/BASE-04/release062.json)。B007目标0.1.63，当前0/10。

- 全量普通2590通过、819跳过；集中原生23个不同用例最终通过。首次两项INVALID_LICENSE连接失败随后重测通过；FFT离散参考有效域修正及原始误差均保留。
- wheel构建、独立安装、真实stdio schema通过；安装包原生2项通过，覆盖结果、分页、图像、POP文件接收和报告。两个断开回执均native.closed=true、forced=false。
- 当前无已知运行中的原生测试会话。默认安装入口已切换0.1.62。
- FRU启动警告仍待诊断；56项恢复后的分析台账仍需按原声明范围逐项审计。TestPlateList等原生选择缺口保持。
- 未创建Git提交；现有工作区修改保留。

下一动作：按remaining-ranked.md第24项PO-01.PhaseAberration，先计划正式输入选择、相位单位/Jones基底和独立复场参考，再实施定向验收。新完成项计入B007；达到10项再集中检查。

## 历史交接（当前状态以上文为准）

# 当前交接：透射扇图选择与独立验收

更新：2026-11-08。源码/发行基线0.1.61；B006为9/10，目标0.1.62。此前5项加YNI，以及本轮已完成但漏记的Speos两种导出、Floating→None；归属核对见`evidence/BASE-04/b006-completion-reconciliation-20261108.md`。TestPlateList原生目录选择仍待完成，不计数。

- 对账：宏1行、STAR6行CSV错位已修复，状态读取严格校验及10项普通测试通过；恢复快照和逐项记录沿用BASE-01证据。
- 方向性图：77项普通、1项原生通过；37点独立IES参考符合5.1e-5。文件/扫描角选择未完成，保持implemented，见`evidence/NS-03/directivity-ies-audit-20261108.md`。
- 散射查看器：手册确认专题独立选择模型/文件，ABg忽略Fraction；已修正此前将对象面设置视作专题选择的解释。正式选择与输出出口仍blocked，沿用原生证据。
- 透射扇图：修复三波长硬编码、损坏数据处理和原生无效光线标记；新增可选择视场/波长、3..1001奇数采样及Jones输入的正式批量偏振追迹路径。普通180项通过。原生平板Fresnel、Jones、取消复用及重载已取得通过记录；最终整文件串行验收正在执行，未计第十项。
- 注意：run_analysis传输对该请求保留exclude_unset，避免默认参数被误判为显式选择。最终原生用例已加入默认报告computation_method断言。
- 启动FRU警告仍存在；不据任务通过认定其已解决。

唯一下一动作：等待当前透射扇图整文件原生测试终态，核对实际结果与关闭；完整通过后记录第十项并执行0.1.62集中验收。原生命令为`pytest tests/native/test_transmission_fan_live.py --run-zemax`，XML为`.local/evidence/development/PO-01/transmission-fan-complete-20261108.xml`；当前会话句柄见本轮工具记录。

## 历史交接（以下状态以顶部为准）

# 当前交接：台账恢复与完成范围审计

更新：2026-11-08。当前源码/发行基线0.1.61；B006记录6/10，批次归属尚在核对。维护步骤未启动原生实例；随后已完成下述消热差玻璃图原生重测。

- 已保存本机快照：`.local/state/ledger-recovery-20261108-095555/`。
- 已修复宏执行1行、STAR分析6行的CSV错位。STAR额外两列的验收文字保留在acceptance字段。
- 从排序表恢复56项分析的当前动作、状态及可识别证据引用；逐项变更见`evidence/BASE-01/ledger-recovery-20261108.json`。这些是状态恢复，尚未替代原始结果核对。
- 7项分析的历史完成标记待核对原范围，当前保持implemented。排序表同步保留验收缺口，B006未增计。
- 状态读取拒绝列数异常、未知状态及无效表头。定向测试10项通过；未运行全量回归或新增原生用例。
- STAR专题说明已注明：11月8日复核使用11月6日readiness193原生数据。其余STAR条目仍需逐项修正文案，区分接口已存在与许可受阻。

新增执行：消热差玻璃图恢复后审计，普通39项、原生stdio 1项通过；见`evidence/MA-01/athermal-glass-map-recovery-audit-20261108.md`。启动FRU警告再次出现；任务成功、close_attempted=true并断开。完整范围审计未收口，保持implemented。

新增色散独立参考审计：普通41项、最终原生1项通过；首次严格解析导数实验1项失败已保留。SCHOTT BK7G18的101点折射率最大差4.966e-8通过；解析导数四点超5.1e-8，最大5.919e-8。1e-4微米半步长中心差分全点在门槛内，原生算法定义待确认。完整证据见`evidence/MA-01/dispersion-independent-audit-20261108.md`。两个条目保持implemented。

新增玻璃图目录审计：普通39通过；原生最终1 xfailed。系统切换生效：OHARA410项均匹配AGF，SCHOTT346项中339匹配，7项缺少当前AGF参考；全部匹配项Nd/Vd通过，终态和断连通过。完整目录验收仍未完成，见`evidence/MA-01/glass-map-catalog-audit-20261108.md`。

新增YNI加固：非有限值/损坏行和面号顺序均严格拒绝，新增10项边界场景；普通46通过，Cooke原生1通过，分页、系统保持和关闭通过。证据`evidence/CV-01/yni-recovery-audit-20261108.md`。2024 R2手册明确YNIP与专题同一定义，为显式波长选择提供正式替代路径。

YNI完整条目完成：新增可选wavelength，以正式YNIP查询Surf/Wave，默认报告保留。普通58项及原生1项通过；Cooke六面、两波长、独立正负球面参考、分页及取消边界通过。B006增加至6/10，证据`evidence/CV-01/yni-explicit-wavelength-acceptance20261108.md`。

源光谱输入身份审计完成：两色样例与空NSC系统返回同样XYZ拟合报告，聚合源归属撤回；结果新增输入定义/未暴露光源绑定信息。坏行和非有限值处理已修复，普通66及原生1通过。完整功能保持implemented；见`evidence/NS-03/source-spectrum-input-identity-20261108.md`。

下一动作：方向性图输入文件身份审计；定位本机sample.ies，建立独立角度/光强/光通量参考，确认正式文件与扫描选择接口，继续其余批次归属审计。B006为6/10。




# 当前开发交接

## 2026-11-08 最新进展

- #100 `EX-01.StandaloneMacro` 已完成当前可执行的宿主复核：两次真实stdio受控启动均任务成功、退出码0、关闭完成，但宏输出文件和可归属执行结果均未生成；保持blocked。证据见 `development/evidence/EX-01/standalone-macro-host-followup-20261108.md`。解除条件为正式宏执行确认、输出/错误出口及取消协议。
- #101 `EXT-EXPORT.BlackBox` 已完成公开接口复核：908个公开类型中未发现ZBB创建工厂或设置/结果对象，`ISurfaceBlackBoxLens`仅消费已有ZBB；保持blocked。证据见 `development/evidence/EXT-EXPORT/blackbox-interface-followup-20261108.md`。下一项为 #102 `EXT-EXPORT.EncryptedCoating`，先复核ZEC创建接口、参数和输出协议。
- #102 `EXT-EXPORT.EncryptedCoating` 已完成公开接口与手册复核：GUI支持ZEC，但公开类型没有加密创建工厂、设置对象或输出协议；保持blocked。证据见 `development/evidence/EXT-EXPORT/encrypted-coating-interface-followup-20261108.md`。
- #103 `EXT-EXPORT.LegacyLinework` 已完成公开接口与手册复核：GUI支持2D/3D DXF及IGES Linework，但公开类型没有专用创建接口，实体CAD导出不能覆盖该范围；保持blocked。证据见 `development/evidence/EXT-EXPORT/legacy-linework-interface-followup-20261108.md`。下一项为 #104 `CV-01.STAR2DDefPlot`，先检查STAR模块状态及受控FEA输入。
- #104 `CV-01.STAR2DDefPlot`、#105 `CV-01.STARAlignCheck`、#106 `CV-01.STARIndexVsTemp` 已完成同一组 STAR 前置探查：Premium 许可有效但 `IsSTARModuleEnabled=false`，无受控 FEA 输入和独立专题工厂；三项保持blocked，证据见 `development/evidence/CV-01/star-analysis-readiness-20261108.md`。下一项为 #107 `CV-01.STARInspectFEA`。
- #107 `CV-01.STARInspectFEA` 及后续 STAR 分析/工作流条目沿用同一前置结论：当前模块未启用且没有受控 FEA 输入，先不创建请求或原生对象；解除条件与证据见 `development/evidence/CV-01/star-analysis-readiness-20261108.md`。队列继续从 #107 逐项登记。
- #108 `CV-01.STARPerfChange` 已完成独立前置复核：未发现专用工厂，`IsSTARModuleEnabled=false` 时适配器在修改前返回 `FEATURE_UNAVAILABLE`；保持blocked。下一项为 #109 `CV-01.STARSysViewer`。
- #109 `CV-01.STARSysViewer` 已完成反射与前置检查：仅有 `ISTARSubsystem`/`STARData`，没有专用查看器工厂或结果出口，且 STAR 模块未启用；保持blocked。下一项为 #110 `EXT-STAR.Components`。
- #110 `EXT-STAR.Components` 已完成组件控制接口探查：`ISTAR_ComponentRBMs` 成员和 typed adapter 已确认，但 `IsSTARModuleEnabled=false`，未执行原生写入；保持blocked。证据见 `development/evidence/EXT-STAR/components-readiness-20261108.md`。下一项为 #111 `EXT-STAR.Components.configure`。
- #111 `EXT-STAR.Components.configure` 已确认 `component_rbm` 显式参数和 `AdjustIndexDataWithComponentRBM` 回读路径；当前模块未启用，写入前拒绝且无部分修改，保持blocked。下一项为 #112 `EXT-STAR.Components.coordinate_breaks`。
- #112 `EXT-STAR.Components.coordinate_breaks` 已确认 `AddComponentRBMsAsCoordinateBreaks()` 与 `CRBMsAreInCoordinateBreaks`/拓扑回读；当前模块未启用，未调用原生方法，保持blocked。下一项为 #113 `EXT-STAR.Components.define`。
- #113 `EXT-STAR.Components.define` 已确认 `SetSurfacesInComponent`、范围检查、重叠保护和成员回读；当前模块未启用，定义调用未执行，保持blocked。下一项为 #114 `EXT-STAR.Components.remove`。
- #114 `EXT-STAR.Components.remove` 已确认原生首面约束、`RemoveComponent` 和组件清单回读；当前模块未启用，删除调用未执行，保持blocked。下一项为 #115 `EXT-STAR.Components.remove_rbms`。
- #115 `EXT-STAR.Components.remove_rbms` 已确认 `RemoveComponentRBMsFromFEADataSets()`、`ComponentRBMsAreRemoved` 回读和重复保护；当前模块未启用，未修改FEA数据，保持blocked。下一项为 #116 `EXT-STAR.CoordinateTransform`。
- #116 `EXT-STAR.CoordinateTransform` 已确认偏移/旋转矩阵/重置校验及原生 setter/readback；当前模块未启用，未修改坐标变换，保持blocked。证据见 `development/evidence/EXT-STAR/coordinate-transform-readiness-20261108.md`。下一项为 #117 `EXT-STAR.FitDeformation`。

- 本轮继续完成 #85 CAD 多配置分层复测与 #86 CAD 格式/版本复测。#85 五种 STEP 配置模式数值与模型保持通过；IGES 两种配置分层继续输出默认层65535，保持受阻。#86 CAD 普通63项、原生格式矩阵及SAT/SAB版本复用各1项通过；能力拒绝项和V30版本不采用均已记录。证据见 `development/evidence/EXT-EXPORT/cad-multiple-configurations-repeat20261108.md`、`cad-settings-repeat20261108.md`。
- #87 `ED-01.Aperture.FloatingToNone` 已完成：普通15项及加强后的原生三轮切换测试通过；None设置实际采用、周边曲面属性保持、会话关闭。证据见 `development/evidence/ED-01/floating-aperture-clear-acceptance20261108.md`。
- #88 `ED-01.Scattering.BSDF` 已完成接口探查及失败状态处理：本机虽有BSDF文件，原生列表仅返回占位“无”，直接设置后getter不采用；公开资源查询现明确返回UNSUPPORTED_SETTING。普通19项及stdio原生查询通过，探针/stdio均关闭成功。追迹和保存重载仍需有效选择器。证据见 `development/evidence/ED-01/bsdf-resource-selector-probe20261108.md`。
- #89 `ED-01.Scattering.User` 已完成本机原生接口复探：5个DLL文件存在；User工厂在GetParamData抛SerializationException，活动`_S_User`为空，公共资源查询返回UNSUPPORTED_SETTING。普通19项、stdio属性页1项通过，原生实例关闭成功。证据见 `development/evidence/ED-01/user-scatter-factory-probe20261108.md`。
- #90 `ED-02.SurfacePickup.ChipZone` 已完成当前环境复测：普通124项、原生stdio最小复现1项通过；原生SetSolveData返回成功但实际模式回退Automatic，适配器检测并报告失败，检查点恢复通过，原生关闭成功。证据见 `development/evidence/ED-02/chip-zone-surface-pickup-repeat20261108.md`。
- #91 `ED-02.SurfacePickup.MechanicalSemiDiameter` 已完成独立复测：普通124项、stdio最小用例通过；原生实际模式回退Fixed，MCP检测失败并返回检查点，恢复及关闭通过。证据见 `development/evidence/ED-02/mechanical-semi-diameter-pickup-repeat20261108.md`。
- #92 `ED-02.ZPLMacro.ChipZone` 已完成复测：普通124项、stdio原生测试通过；自有宏被列出，类型采用但宏名回读为空，MCP返回SETTING_REJECTED/PARTIAL_UPDATE，宏未运行；检查点恢复、临时文件删除和关闭通过。证据见 `development/evidence/ED-02/chip-zone-zpl-macro-repeat20261108.md`。
- #93 `ED-02.ZPLMacro.MechanicalSemiDiameter` 已完成独立复测：普通124项、stdio原生用例通过；自有宏可发现，原生模式回退Fixed，MCP检测失败并返回检查点；宏清理、恢复和关闭通过。证据见 `development/evidence/ED-02/mechanical-semi-diameter-zpl-macro-repeat20261108.md`。
- #94 `ED-02.CA_fill.LDEDiscovery` 已完成接口探查并保持受阻：枚举值32存在，`ISolveData`无CA_fill设置对象，Standard八类单元格均不支持，创建设置返回null；81面型扫描亦无可用单元格。普通82项通过，原生会话正常关闭。证据：`development/evidence/ED-02/ca-fill-lde-discovery-20261108.md`。
- 下一项为 #95 `ED-02.DIA_fill.LDEDiscovery`。按相同路径检查枚举反射、正式设置对象、Standard单元格支持情况和创建设置结果，运行solve定向测试并确认原生关闭；若没有官方入口则记录具体阻塞后继续队列。
- #95 `ED-02.DIA_fill.LDEDiscovery` 已完成接口探查并保持受阻：枚举值33存在，`ISolveData`无DIA_fill设置对象，Standard八类单元格均不支持，创建设置返回null；81面型扫描亦无可用单元格。普通82项通过，原生会话正常关闭。证据：`development/evidence/ED-02/dia-fill-lde-discovery-20261108.md`。
- #96 `ED-02.DuplicateSag.LDEDiscovery` 已完成接口与单元格复核并保持受阻：枚举34及`_S_DuplicateSag.Surface`存在，当前八类Standard单元格均不支持，81面型扫描无支持入口；创建设置返回null。普通82项及原生关闭通过。证据：`development/evidence/ED-02/duplicate-sag-lde-discovery-20261108.md`。
- #97 `ED-02.InvertSag.LDEDiscovery` 已完成接口与单元格复核并保持受阻：枚举35及`_S_InvertSag.Surface`存在，当前八类Standard单元格均不支持，81面型扫描无支持入口；创建设置返回null。普通82项及原生关闭通过。证据：`development/evidence/ED-02/invert-sag-lde-discovery-20261108.md`。
- #98 `ED-02.MarginPercent.LDEDiscovery` 已完成接口探查并保持受阻：枚举31存在但`ISolveData`无对应设置对象，Standard八类单元格均不支持，创建设置返回null；81面型扫描无入口。普通82项及原生关闭通过。证据：`development/evidence/ED-02/margin-percent-lde-discovery-20261108.md`。
- #99 `ED-03.MCE.independent_file` 已完成接口复核并保持受阻：接口、继承IEditor和运行时MCE对象均无独立文件读写方法；整系统LoadFile/SaveAs保留可用。MCE相关普通23项通过，原生反射探针关闭成功。证据：`development/evidence/ED-03/mce-independent-file-interface-20261108.md`。
- 下一项为 #100 `EX-01.StandaloneMacro`。先检查现有宿主工厂、ZPL solve入口、接口/委托反射证据与测试；再确认公开 API 是否提供独立宏执行、输入/输出和取消/关闭契约。仅在找到正式入口时设计请求并实现，否则记录原生探查与解除条件。当前B006 5/10。
- 原生会话已结束；本轮未运行全量回归、wheel构建或发行检查，B006仍5/10。

- `CO-01.DiffEfficiencyAngular` 与 `CO-01.DiffEfficiencyChromatic` 已复测原生 Hologram1 和 Kogelnik DLL：普通24项、原生2场景通过。Hologram1的S/P独立参考、结果分页/图像、持久性、失败/取消关闭和stdio断开通过；DLL P投影约定仍无正式定义，两个分析保持implemented。详见`evidence/CO-01/diff-efficiency-angular-repeat20261108.md`及`diff-efficiency-chromatic-repeat20261108.md`。
- `CO-01.KogelnikDLL.PProjection` 探查确认安装DLL（2024-03-22）无版本资源、源码或Jones基说明；投影平方诊断与P数据吻合，但不能确定这是预期功率定义。下一项依赖该条目，先索取源码/供应方定义/修正版DLL；并行队列下一可执行项为`BASE-04`生命周期诊断。证据：`evidence/CO-01/kogelnik-dll-p-projection-probe20261108.md`。
- `BASE-04`：普通生命周期、启动、连接探针与双stdio历史测试42项通过；真实stdio单会话连续取消优化/配置评估/NSC追迹1项通过，配置评估恢复检查点，NSC任务关闭，断连后无原生/Python残留。原`FRU__delta_init`本次未复现，历史`CreateNewApplication`超时仍待解释；下一条按排序表为受阻的`ED-01.Scattering.ISScatterCatalog`资源核查。证据：`evidence/BASE-04/lifecycle-repeat20261108.md`。
- `EXT-HPC.GlobalOptimization`与`EXT-HPC.HammerOptimization`：共享HPC普通34项通过；两个原生入口均在配置预检收到`HPC_SETTINGS_UNAVAILABLE`、修订号0且未创建任务，显式断开成功。下一项`EXT-HPC.NSCTrace`。证据：`evidence/EXT-HPC/global-optimization-preflight20261108.md`、`hammer-optimization-preflight20261108.md`。
- `EXT-HPC.NSCTrace`与`EXT-HPC.Tolerancing`：两个专属原生入口同样在偏好设置预检返回`HPC_SETTINGS_UNAVAILABLE`，修订号0、未创建作业，断开成功；解除条件为有效配置、节点和许可。`EXT-SPEOS.Receiver.LensSystem/Whitebox`：两个导出包存在且源端关闭通过，本机无Speos接收端；接收端导入保持受阻。`NS-01.Conversion`混合组复测仍原生启动失败，检查点恢复187项通过。当前下一条：`ED-04.RayAimingWizard`。证据分别见`evidence/EXT-HPC/`、`evidence/EXT-SPEOS/*-receiver-preflight20261108.md`及`evidence/NS-01/conversion-group-repeat20261108.md`。
- `ED-04.RayAimingWizard`：普通39项、原生只读选项/关闭/模型保持1项通过；推荐运行的历史原生探查仍10秒TimedOut、取消后IsRunning、Close=false。当前下一条按排序表为`EXT-EXPORT.CadMultipleConfigurations`。证据：`evidence/ED-04/ray-aiming-lifecycle-repeat20261108.md`。

- `EXT-HPC.Settings`：原生测试1项通过，但`GetHPCSettingsFromPrefs`返回null并报`HPC_SETTINGS_UNAVAILABLE`；解除条件是配置有效HPC偏好，见`evidence/EXT-HPC/settings-preferences-20261108.md`。
- `EXT-SPEOS.LensSystem`与`EXT-SPEOS.Whitebox`：本轮Cartesian LensSystem与Whitebox原生测试均通过，设置/原生输出、源模型保持、工具及副本关闭、stdio断开有证据；接收端导入仍独立受阻，见`evidence/EXT-SPEOS/`。
- `NS-04.PrescriptionDataSettings`：默认报告原生任务成功并导出文本；没有正式章节选择和回读，维持受阻，见`evidence/NS-04/prescription-data-settings-20261108.md`。
- 当前执行顺序以`development/remaining-ranked.md`为准；`BASE-04`本轮新增生命周期证据见上方。

更新：2026-11-08。当前执行到 `NS-03.FluxvsWavelength`；B006仍5/10。源码工作区支持114种分析，发行版0.1.61支持110种。

本轮先为 `MA-01.DispersionDiagram` 增加有类型请求和原生文本曲线解析。OpticStudio 24.2.0 Build 240529 返回BK7G18的101点曲线，20 C、1 atm；普通定向65项、原生stdio 1项通过，任务分页、系统状态保持和断开通过。材料/环境选择在SettingsFirst/GetSettings中不可用，条目按完整声明范围保留blocked。证据：[验收记录](evidence/MA-01/dispersion-diagram-acceptance20261107.md)，最新调用`.local/runs/runs/dispersion_diagram_native_1d02f582d7/calls.json`。

`MA-01.DispersionvsWavelength` 已增加有类型请求和原生导数曲线解析。101个BK7G18点、20 C、1 atm，单位1/µm；与折射率曲线的99点中心差分最大误差3.49e-5，低于5e-5。普通定向70项、原生stdio 1项通过，任务分页、系统状态保持和断开通过。材料/环境选择仍缺正式设置，按完整范围保留blocked。证据：[验收记录](evidence/MA-01/dispersion-vs-wavelength-acceptance20261107.md)，原生探查`.local/evidence/development/MA-01/dispersion-vs-wavelength-20261107/summary.json`，stdio调用`.local/runs/runs/dispersion_vs_wavelength_native_a25e0a1765/calls.json`。

`MA-01.GlassMap` 已完成当前加载目录图表范围：原生报告提供346个SCHOTT玻璃的Nd/Vd点，N-BK7与本机SCHOTT.AGF一致；行分页、原生散点、X轴反向绘图、PNG导出、系统保持和断开通过。AS_Default实际设置IsValid=true、IsActiveWindow=true。普通定向51项、原生stdio 1项通过。证据：[验收记录](evidence/MA-01/glass-map-acceptance20261107.md)，最新调用`.local/runs/runs/glass_map_native_b74f4f5eda/calls.json`。

本轮已将 `CV-01.SourceColorChart1931` 与 `CV-01.SourceColorChart1976` 完成原生结果出口探查并登记为blocked：两者AS_Default、AR_Default有效，但消息/曲线/网格/散点均为0，GetTextFile返回false；两个对象关闭且会话断开通过。恢复条件为取得正式源图选择与图表数据/图像出口，或建立可对照原生语义的替代计算。证据：`development/evidence/CV-01/source-color-charts-acceptance20261108.md`。

`CV-01.YNIContributions` 已实现并原生验收：新增kind-only类型请求，解析YNI原生文本为可分页逐面rows和series。Cooke样例在0.55000 µm、毫米单位下6个曲面值与文本逐项一致；普通5项、原生stdio 1项通过，分析关闭和断连通过。证据：`development/evidence/CV-01/yni-contributions-acceptance20261108.md`。

`NS-03.FluxvsWavelength` 已在两波长色度NSC样例中原生执行。AS_Default/AR_Default有效，所有结构结果计数为0，GetTextFile虽返回true但文件仅2字节BOM；对象关闭、会话断开通过。条目登记blocked。证据：`development/evidence/NS-03/flux-wavelength-acceptance20261108.md`。

`NS-03.SourceSpectrumViewer` 已实现并验收：新增kind-only请求，在NSC两色混合样例中解析20点原生波长/相对权重以及XYZ拟合、CRI、CCT；单位与峰值归一化清晰标识，stdio、对象关闭和断连通过。原生接口无逐光源选择。证据：`development/evidence/NS-03/source-spectrum-acceptance20261108.md`。

`NS-03.DirectivityPlot` 已实现并验收：NSC两色混合样例返回IES身份、峰值强度、总通量及37点原生方向曲线；角度节点、单位、stdio和生命周期检查通过。证据：`development/evidence/NS-03/directivity-acceptance20261108.md`。

`NS-03.ScatterFunctionViewer` 已在本机ABg散射样例执行原生探查：设置/结果有效但结果集合为空、GetTextFile失败；分析关闭和断连通过。条目标记blocked，恢复条件为获得正式曲线/网格或图像出口。证据：`development/evidence/NS-03/scatter-function-acceptance20261108.md`。

`NS-03.ScatterPolarPlotSettings` 已完成ABg样例及Lambertian单变量对照。两者均返回轴标签None、181×90且每格严格为1/π的相同网格，文本导出失败；分析对象和会话关闭通过。结果无法表征输入散射分布，登记blocked。证据：`development/evidence/NS-03/scatter-polar-acceptance20261108.md`。

`NS-03.PhotoluminscenceViewer` 已探查两个本机荧光样例。Premium许可允许执行，但原生报告均为“输入无效数据/设置”；含PhotoluminescenceModel对象的样例仍无数据。对象关闭和断连通过，条目标记blocked。证据：`development/evidence/NS-03/photoluminescence-acceptance20261108.md`。

`NS-03.RadiantSourceModelViewerSettings` 已在NSC样例执行。PremiumEdition返回本机原生消息“只有 OpticStudio 旗舰版支持所需功能”，无数据/文本出口；关闭与断连通过。样例树无专用Radiant输入，条目标记blocked。恢复条件为旗舰版许可和匹配Radiant资源。证据：`development/evidence/NS-03/radiant-source-viewer-acceptance20261108.md`。

`NS-03.RoadwayLighting` 已在本机可用NSC样例执行：默认报告包含道路指标，但AS_Default没有专题设置，输入模型也非道路照明系统，故未作为有效验收。对象关闭和断连通过。证据：`development/evidence/NS-03/roadway-lighting-acceptance20261108.md`。

`NS-03.SourceIlluminationMap` 已在NSC两色源样例探查，AS_Default/AR_Default有效但数值集合为空、文本导出失败；对象关闭与断连通过。登记blocked，等待正式输入选择和图像/网格出口。证据：`development/evidence/NS-03/source-illumination-acceptance20261108.md`。

`NS-03.SourcePolarViewer` 已在NSC两色源样例返回19×19原生网格，范围0–18，但所有轴/值标签为None且文本导出失败；关闭和断连通过。保留完整矩阵，待正式轴定义与归一化语义后继续。证据：`development/evidence/NS-03/source-polar-acceptance20261108.md`。

`PO-01.PhaseAberration` 已在Cooke样例得到原生文本出口：报告含0.55µm、中心视场、Jones分量及201点弧矢/子午相位曲线；AS_Default无专属可写设置，报告未给相位单位。分析关闭与断连通过。证据：`development/evidence/PO-01/phase-aberration-probe20261108.md`。

`PO-01.PolarizationRayTrace` 已在Cooke样例执行原生探查。文本输出包含坐标/方向余弦、Jones场、膜层反射/透射系数、复振幅和相位延迟及度数；AS_Default无射线选择，当前只对应默认中心光线。对象关闭与断连通过。证据：`development/evidence/PO-01/polarization-ray-trace-probe20261108.md`。

`PO-01.Transmission` 已在Cooke样例得到32×32瞳网格条件的原生默认报告，包含3视场×3波长总透射和逐面主光线透射；条件为非偏振，AS_Default无专题选择。对象关闭与断连通过。证据：`development/evidence/PO-01/transmission-probe20261108.md`。

`PO-01.TransmissionFan` 已接入 `polarization_transmission_fan` 类型请求和原生文本解析，输出rows/series。9项普通测试与1项Cooke原生stdio测试通过；验证波长、弧矢/子午方向、视场、归一化强度和资源关闭。文档、schema与能力清单已更新。条目保持in_progress，后续补设置选择和独立数值参考。证据：`development/evidence/PO-01/transmission-fan-acceptance20261108.md`。

旧交接时记录的 `WP-01.FiberCouplingSettings` 顺序已过期；当前逐项顺序以 `development/remaining-ranked.md` 为准。本轮最近完成 NS-04 默认报告探查，下一项为 `NS-04.SurfaceDataSettings`。

源码当前100工具/113分析；0.1.61发行版为100工具/110分析。剩余台账统计见 `development/generated/status.json`。

## 历史交接快照

发行与源码0.1.61，100工具/110分析；B005已完成10/10并发行。B006仍5/10，目标0.1.62。剩余130条源记录、122个不同编号、120组共同功能；38条历史范围另列。

637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。

640普通45项、641正负原生2项通过；新增1001节点径向加权斜率摘要。继续制造偏移符号/基准、面型拟合适用性及反向制造摘要，保持implemented。

最新证据：`.local/evidence/development/MA-01/progress641-monomials.json`、`.local/evidence/development/MF-01/progress641-slope-summary.json`。637–639均断连且删除自有GRD；641测试通过，关闭和模型保持详见原始记录。本次整理未启动原生会话。

下一动作：先读取上述汇总及原始输入；按固定B006队列选择取得新正式依据的条目。SagTable需制造偏移合同；Gradium需高阶求值、左cap和选择接口。条件未变时继续其余可执行项。

下一命令：`Get-Content .local/evidence/development/MA-01/progress641-monomials.json; Get-Content .local/evidence/development/MF-01/progress641-slope-summary.json`。

历史过程及恢复方法见[归档索引](archive/README.md)。

维护检查：状态汇总定向2项通过；清理后3265项测试收集成功。归档清单58426项，含641原始输出同时保留在线；删除缓存/构建残留1306项。恢复位置见归档索引。下一条优先读取Gradium637–639原始单项式证据，确认高阶求值正式定义；缺少新依据时按B006固定候补继续。

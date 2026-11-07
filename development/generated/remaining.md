# 未完成项汇总

代码基线 0.1.61；汇总日期 2026-11-07。按三份执行台账生成，逐项证据和后续动作保留在 JSON 报告中。

| 台账 | 总数 | 状态 |
| --- | ---: | --- |
| 工作包 | 34 | done 8 / implemented 10 / in_progress 15 / blocked 1 |
| 操作条目 | 172 | done 99 / implemented 17 / blocked 51 / in_progress 1 / pending 4 |
| 分析条目 | 164 | done 69 / baseline 36 / documented 2 / implemented 15 / in_progress 26 / blocked 15 / pending 1 |

待处理源记录 130 项；历史 baseline/documented 范围 38 项另列。

| 未完成工作包 | 工作包状态 | 操作条目 | 分析条目 |
| --- | --- | --- | --- |
| BASE-02 | implemented | — | — |
| BASE-04 | in_progress | done 1 | — |
| BASE-05 | implemented | — | — |
| ED-01 | implemented | done 6 / implemented 1 / blocked 4 | done 1 |
| ED-02 | implemented | done 36 / implemented 1 / blocked 9 | implemented 1 |
| ED-03 | implemented | done 14 / blocked 1 | — |
| ED-04 | implemented | done 8 / blocked 1 | — |
| IM-01 | in_progress | — | blocked 1 / done 2 |
| PO-01 | in_progress | — | blocked 4 / done 1 |
| CO-01 | in_progress | done 4 / implemented 3 / blocked 1 | done 13 / implemented 3 |
| MA-01 | in_progress | done 2 / blocked 4 / in_progress 1 / implemented 1 | blocked 4 / done 1 |
| NS-01 | implemented | implemented 1 | — |
| NS-02 | in_progress | implemented 1 / done 2 | done 3 / implemented 1 |
| NS-03 | in_progress | done 1 | in_progress 10 / done 1 |
| NS-04 | in_progress | done 3 | done 2 / in_progress 5 |
| WP-01 | in_progress | — | implemented 2 / done 2 |
| TO-01 | in_progress | — | done 4 |
| MF-01 | in_progress | — | implemented 2 / blocked 1 |
| CV-01 | in_progress | — | implemented 4 / done 15 / in_progress 10 / blocked 1 |
| CV-02 | in_progress | — | done 7 / blocked 4 / in_progress 1 / implemented 2 |
| EX-01 | in_progress | done 2 / pending 3 / blocked 3 | done 2 / pending 1 |
| RL-01 | in_progress | done 6 | — |
| EXT-STAR | blocked | blocked 24 | — |
| EXT-HPC | implemented | implemented 5 | — |
| EXT-SPEOS | implemented | implemented 2 / pending 1 / blocked 1 | — |
| EXT-EXPORT | implemented | done 1 / blocked 3 / implemented 2 | — |

按相同 item_id 去重后为 122 项；跨清单同名条目同步更新状态和证据。

当前执行动作：

- BASE-02：按本条声明范围确认正式设置、输入身份和结果出口，再完成定向原生及关闭验收。新增条目可调用；既有入口可用；共用调整有相关回归
- BASE-04：Startup and serial stdio recovered after reboot; continue FRU__delta_init warning diagnosis and remaining native lifecycle cases.
- BASE-05：0.1.61/B005 gate passed; six representative workflows accepted. Continue B006 to ten new canonical completions, then build/install/stdio-check 0.1.62.
- ED-01：推进ED-02；原生User/BSDF/Floating清除及ISX输入分别保留阻塞
  当前缺口：User序列化、BSDF选择器混用、Floating清除及ISX输入见逐项清单
- ED-02：598复用正式DLL反射：Solve仅Nd/Abbe/dPgF及Vary，目录拟合系数属于目录材料；所查接口无临时模型系数出口。保留527精确线Vd误差及原门槛，取得正式模型色散定义后继续。
  当前缺口：MaterialModel fit: rounded Abbe 59.99988524798844 vs 60; original tolerance 1e-5 + 1e-7*reference retained. Offset is accepted under documented model-difference definition.
- ED-03：14 editor operations accepted over real stdio including generic TDE insert and MFE/MCE/TDE save-reload; independent MCE file API remains blocked.
  当前缺口：Independent MCE file interface absent from public and inherited API.
- ED-04：FindBestAsphere independent Conic candidate optimum accepted; remaining RayAiming completion/cancellation and model preservation.
  当前缺口：RayAiming recorded timeouts remain under diagnosis.
- IM-01：Geometric image scenes executed; investigate ImageSimulation output contract and GeometricBitmap AS_Default/CFG path; preserve original failed records.
  当前缺口：Current ImageSimulation result outlet empty; GeometricBitmap native settings lack typed accessors.
- PO-01：PolarizationPupilMap 当前配置已完成；继续 PolarizationRayTrace、Transmission、PhaseAberration、TransmissionFan 正式配置及受控参考。
  当前缺口：其余四项无专属设置 getter；分别探查正式 CFG 键、加载采用和结果契约。
- CO-01：NSC object/face scans complete; retain independent Kogelnik DLL P-projection diagnostic; continue remaining work packages.
- MA-01：637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。
  当前缺口：Remaining per-item runtime settings and controlled references need execution.
- NS-01：纯NSC关闭光阑孔径转换后执行、保存重载及追迹通过；继续等价光线和混合组启动失败定位
- NS-02：关键光线和单光线已完成；继续PathAnalysis未分类结果、RayDatabaseViewer及NSC MTF
- NS-03：NSCGeometricMtf565正式逐点路径已完成；继续本工作包其他未完成专题的正式设置/输入及有效结果接口。
- NS-04：FileComparator及对象面片、区域、Sag完成；继续其余viewer/prescription专题
- WP-01：ParaxialGaussianBeam/SkewGaussianBeam native operands accepted362; continue BeamFileViewer and FiberCouplingSettings dedicated formal settings/output contract; existing POP/file-reader evidence retained.
- TO-01：QuickYield574已验收；继续本工作包剩余公差/补偿专题的正式输入、结果与状态条件。原生近似的高阶精度范围见acceptance574-reference.json。
- MF-01：640普通45项、641正负原生2项通过；新增1001节点径向加权斜率摘要。继续制造偏移符号/基准、面型拟合适用性及反向制造摘要，保持implemented。
- CV-01：FFT Surface610相位身份与相干OTF跨出口诊断已补齐，独立复瞳映射仍缺；FullFieldSpot591出口为空。继续固定候补有新正式依据的条目。
- CV-02：637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。 PowerMap沿用636单位验收，继续环节点/零EFL定义。
- EX-01：Universal1D/2D accepted; complete B003 release gate, then continue remaining callback/host/resource entries.
  当前缺口：Controlled .NET LoadNETCallback returns null; C export ABI unavailable; other formal host contracts remain per-item blockers.
- RL-01：Six same-session workflows accepted (four in B005, POP/delivery in B006). Keep package in progress for B006 release gate and remaining global delivery conditions.
- EXT-STAR：Enable native STAR module, then execute controlled FEA/read/control/unload cases; material utility also needs finite positive results before numerical acceptance.
  当前缺口：Premium v242 native STAR flagFalse; API license valid. Material utility returns index0 for confirmed resources; controls gated before mutation.
- EXT-HPC：读取实际 HPC 配置、许可和节点；执行最小自有任务的提交、状态、取消与结果回收，逐项记录可执行条件。
- EXT-SPEOS：按本条声明范围确认正式设置、输入身份和结果出口，再完成定向原生及关闭验收。导出成功且接收端可导入
- EXT-EXPORT：PointCloud complete; CAD NSC options/geometry accepted. Retain ACIS actual-version mismatch and IGES native layer discrepancy.
  当前缺口：ZBB/ZEC/legacy linework creation factories not found in installed public API; remaining acceptance is recorded per item.

共同功能去重后为 120 组。

源码能力：100 工具、110 种分析；发行能力见对应发行记录。

当前批次 B006：5/10；下一条：B006 remaining gaps after evidence637–641 synchronization

最近发行证据：

当前版本发行记录：.local/evidence/development/BASE-04/release061.json。
- 普通检查通过：2381 项。

以上检查数量属于对应发行记录；本轮新增执行另存证据，历史执行与当前执行分别记录。

历史 baseline/documented 沿用各自记录范围。条目完成需要实际设置、可用结果、相关数值或输出检查、关闭及文档证据。

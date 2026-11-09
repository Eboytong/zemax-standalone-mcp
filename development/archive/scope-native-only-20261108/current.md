# 当前执行：B007，目标0.1.63

更新2026-11-08。源码及发行0.1.62，101工具/118分析；B006十项及集中发行检查已完成，B007为0/10。发行证据见[evidence/BASE-04/release062.json](evidence/BASE-04/release062.json)。

按remaining-ranked.md顺序处理依赖已满足的未完成项。下一项PO-01.PhaseAberration：先读取既有设置与结果证据，明确单位及正式参数选择，再建立独立复场参考。每项先说明计划、执行定向检查、更新证据及台账；许可/资源/正式接口不足时记录具体解除条件并继续。

十项集中检查继续沿用plan.md第7节及批次门槛。历史测试和失败记录保留；当前会话无已知原生运行进程。

## 历史执行方案（当前顺序以上文为准）

# 当前开发计划：B006 与 0.1.62

更新日期：2026-11-07。长期执行规范和第7节证据要求见 development-plan.md；当前状态来自三份CSV、development-batches.json 和 development-remaining.md。原计划保存在 development-history-b005.md。

## 1. 基线与批次

发行0.1.61：100个工具、110种分析。B005完成10/10并通过集中验收：普通2381通过、741跳过，串行原生12通过，wheel独立安装和真实stdio通过。证据：`.local/evidence/development/BASE-04/release061.json`。源码基于0.1.61，包含B006尚未发行的Power Map切线采样、MCE回读精度及结果元数据增量。

B006目标0.1.62，现为9/10。已完成POP、制造交付、FFT线边扩散、NSC MTF、QuickYield、YNI、Speos LensSystem/Whitebox导出及Floating口径清除九项；建模、顺序、成像及NSC工作流已计入B005。完成数按共同功能首次完成计，别名和历史证据整理沿用各自归属。

## 2. 文件职责与执行入口

| 记录 | 职责 |
| --- | --- |
| development-plan.md | 长期规范、依赖、状态、第7节证据、十项检查节奏 |
| next-development-plan.md | 本文件：当前队列、门槛和候补顺序 |
| development-handoff.md | 最近执行、下一动作、会话和阻塞条件 |
| development-tasks.csv | 工作包状态 |
| development-items.csv | 编辑操作与工具条目 |
| development-backlog.csv | 分析条目 |
| development-remaining.md / development-queue.json | 从台账生成的源记录、不同编号、共同功能及执行动作 |
| development-batches.json / BASE-04批次记录 | 首次完成数、发行门槛和证据 |

统计入口：`.venv/Scripts/python.exe scripts/development/status.py --output .local/evidence/development/BASE-01/remaining-audit641.json --markdown development/generated/remaining.md --queue development/generated/queue.json`。统计报告的源码能力与已发行wheel能力分别记录。别名共享实际范围、状态和证据。

## 3. B006当前执行顺序

逐项处理下表。已知条件未变的失败保留证据，依序继续可执行候补；取得新接口或实验依据时再回到对应条目。

| 顺序 | 条目 | 本批完成门槛与当前缺口 |
| --- | --- | --- |
| 已完成 | RL-01.pop.Workflow | 高斯束→ZBF→文件接收→耦合/报告；束宽相对5e-4、功率/重叠绝对5e-4。native483通过 |
| 已完成 | RL-01.delivery.Workflow | 灵敏度/MonteCarlo/逆公差适用终态、两个样本、STEP/网格/图像/PDF与重载。native484通过 |
| 已完成 | NS-03.NSCGeometricMtf | 565正式频率终点查询通过；单点/非对称及累积/ZRD64项DFT最大差2.701e-8，沿用1e-7+1e-7相对门槛。默认原生显示曲线误差仍保留；精确查询、设置回读及关闭验收完成 |
| 2 | CV-01.FftSurfaceMtf | 轴上/离轴瞳自相关、投影、窗口和插值分离；绝对0.005。509轴上独立复瞳差0.00243362通过；离轴0.18795452，511双方向F数0.12186263、512主波长0.21795740仍超限，保留implemented |
| 已完成 | CV-01.FftPsfLineEdgeSpread | 547独立准确拉伸瞳节点、PSF边缘积分、复振幅/相位及生命周期验收通过；最大相干强度差0.000810981，保留历史失败 |
| 已完成 | TO-01.QuickYield | 574匹配所选波长的主波长相关solve求值后，Cooke动态/固定控制最大差6.627e-7waves；3/6度折射去活塞/倾斜参考及有限扰动、生命周期通过。Standard高阶近似限制保留 |
| 候补1 | MF-01.SagTable | 622新增RMS正式DSAG原始半径/Z偏移与SSAG一致性，617两例通过；621已知piston及同形Zernike暴露符号/顶点基准与拟合适用差异，仍需制造偏移等价契约 |
| 候补2 | EXT-EXPORT.CadMultipleConfigurations | STEP配置体积通过；585实体/曲面×两配置模式四组层号均65535，未采用10/11；待实际分层正式出口 |
| 候补3 | EXT-EXPORT.CadSettings | SAT/SAB的V25–V30实际头500；521的ASAT/ASAB正式Run拒绝。需实际格式/版本采用的新正式路径，原拒绝/产物保留 |
| 候补4 | ED-02.MaterialModel.Material | Nd通过；Abbe59.99988525对目标60超出原1e-5+1e-7×参考值。598已审计Solve/目录正式接口，无新临时模型系数出口；需正式模型色散定义 |
| 候补5 | CV-01.FullFieldSpot | 591三组八类正式出口全0、SpotData空、文本false且均关闭；需有效正式出口或共享参考/放大映射 |
| 候补6 | B005未完成专题 | 按下节原顺序继续有新证据/条件的条目 |

每个数值疑难先提出可区分假设，再运行单变量实验。保留原结果、容差、失败原因和解除条件。整个声明范围通过后才计入完成数。

## 4. B005遗留专题的原顺序与范围

B005的发行门槛已完成；以下专题按实际状态保留，后续完成可计入B006。IMA/BIM和ZRD正式替代路径已完成，专题窗口的接口缺口继续单独记录。

| 顺序 | 条目 | 剩余范围/条件 |
| --- | --- | --- |
| 1 | MA-01.GradiumProfile | 633同GSF常量Gradient5对照通过，但Gradium实际Snell折射与GetIndex均保留3.345e-8参考误差；右cap通过，左cap2/3四组报错。需原生剖面求值及左cap正式解释、专题选择；MA/CV别名同步 |
| 2 | CV-02.IMABIMFileViewer | 已完成正式SourceBitmap替代路径，保留专属窗口选择缺口；文件/通道/方向/归一化/零输入/异常与生命周期证据沿用 |
| 3 | CV-02.PowerFieldMapSettings | POWF正式查询已实现；球面、双轴72项主方向、切线采样61项及生命周期通过；补离轴独立参考、单位和零/无穷状态；周边环节点/状态无正式出口 |
| 4 | CV-02.PowerPupilMapSettings | POWP正式查询已实现；同上，另保留归一化瞳坐标与圆外掩码；零原值保持原始身份 |
| 5 | NS-02.RayDatabaseViewer | 已完成正式ZRD读取替代路径；沿用自有光线/段、筛选、分页及关闭证据，专题选择缺口单列 |
| 6 | CV-02.LightSourceAnalysis | 受控DAT/SDF、有限共轭、目标面/波长/像素/单位；全光线/随机偏振关闭，位置/通量、遮挡/旋转/参考及W/lm；设置身份缺口见progress471 |
| 7 | CV-02.ExtendedDiffractionImageAnalysis | 输入尺度/范围、OTF采样、相干/畸变/照度；点源/双点、PSF或复场参考、ZBF出口；正式选择缺口见progress471 |
| 8 | CV-02.PartiallyCoherentImageAnalysis | IMA/BIM强度与ZBF复场身份、相干/非相干极限、Gamma/Alpha/Fraction、截面/填充/重采样；正式设置缺口见progress471 |

Power Map以屈光力diopters或EFL镜头单位输出，保留values[y][x]、坐标、掩码、原始查询、计算来源及设置；专题窗口和替代查询范围分别记录。切线采样按tan(angle)均匀，保留实际角度。未公开周边环状态时明确中心参考光线的检查范围。

TestPlateList保留435/436实际探查；437取得手册材料，尚未执行新原生用例。其与SagTable、Gradium的多个台账入口同步范围与证据。

## 5. 逐项检查与集中发行

逐项完成原生接口探查、有类型请求、最终设置回读、执行、结果读取、单位/坐标/输入身份、分页/适用图像、预定数值参考、任务终态及资源关闭；覆盖成功/失败/取消/复用、适用恢复和保存重载。改动共用模块时补受影响消费者定向回归。原生实例串行，前一会话结束再启动下一会话。

每项按development-plan.md第7节记录条目/范围、源码和安装包版本、原生版本、输入来源、请求、实际设置、命令、结果、参考/容差/误差、终态、关闭、结论和下一步。全部未完成项保留具体next_action；外部阻塞附探查结果和解除条件。

B006达到10/10时执行一次全量普通测试、本批及受影响模块串行原生回归、0.1.62 wheel、独立安装和真实stdio的schema/连接/分析/结果/分页/导出/关闭。失败保留批次，修复后复测失败项及影响范围。完成条件仍适用的历史证据继续沿用。

## 6. 当前动作

发行与源码0.1.61，100工具/110分析；B005已完成10/10并发行。B006仍5/10，目标0.1.62。剩余130条源记录、122个不同编号、120组共同功能；38条历史范围另列。

637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。

640普通45项、641正负原生2项通过；新增1001节点径向加权斜率摘要。继续制造偏移符号/基准、面型拟合适用性及反向制造摘要，保持implemented。

见development-handoff.md和remaining-audit641.json。

2026-11-08：YNI新增显式波长YNIP路径及独立近轴参考验收，计入B006第6项。下一项源光谱输入身份审计；此前历史5/10记录沿用其日期。

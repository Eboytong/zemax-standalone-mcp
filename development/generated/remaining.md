# 未完成项汇总

代码基线 1.0.0；汇总日期 2026-11-09。按三份执行台账生成，逐项证据和后续动作保留在 JSON 报告中。
当前计划范围：OpticStudio内建功能、官方STAR及HPC。范围定义见tracking/scope.json；移出条目的原始状态和证据保存在开发归档。


| 台账 | 总数 | 状态 |
| --- | ---: | --- |
| 工作包 | 32 | done 8 / implemented 9 / in_progress 14 / blocked 1 |
| 操作条目 | 154 | done 107 / implemented 11 / blocked 35 / in_progress 1 |
| 分析条目 | 163 | done 78 / baseline 36 / documented 2 / implemented 21 / blocked 19 / in_progress 7 |

待处理源记录 94 项；历史 baseline/documented 范围 38 项另列。

| 未完成工作包 | 工作包状态 | 操作条目 | 分析条目 |
| --- | --- | --- | --- |
| BASE-02 | implemented | — | — |
| BASE-04 | in_progress | done 1 | — |
| BASE-05 | implemented | — | — |
| ED-01 | implemented | done 7 / implemented 1 / blocked 2 | done 1 |
| ED-02 | implemented | done 36 / implemented 1 / blocked 2 | implemented 1 |
| ED-03 | implemented | done 14 | — |
| ED-04 | implemented | done 8 / blocked 1 | — |
| IM-01 | in_progress | — | implemented 1 / done 2 |
| PO-01 | in_progress | — | in_progress 2 / done 3 |
| CO-01 | in_progress | done 7 | done 16 |
| MA-01 | in_progress | done 4 / blocked 2 / in_progress 1 / implemented 1 | implemented 2 / done 3 |
| NS-01 | implemented | implemented 1 | — |
| NS-02 | in_progress | implemented 1 / done 2 | done 3 / implemented 1 |
| NS-03 | in_progress | done 1 | implemented 2 / blocked 8 / done 1 |
| NS-04 | in_progress | done 3 | done 2 / in_progress 3 / implemented 2 |
| WP-01 | in_progress | — | implemented 2 / done 2 |
| TO-01 | in_progress | — | done 4 |
| MF-01 | in_progress | — | implemented 2 / blocked 1 |
| CV-01 | in_progress | — | implemented 4 / done 17 / blocked 8 / in_progress 1 |
| CV-02 | in_progress | — | done 7 / blocked 2 / implemented 4 / in_progress 1 |
| RL-01 | in_progress | done 6 | — |
| EXT-STAR | blocked | blocked 24 | — |
| EXT-HPC | implemented | implemented 5 | — |
| EXT-EXPORT | implemented | done 1 / blocked 4 / implemented 1 | — |

原生开发与验收排期冻结：89组共同功能。实际实现状态和证据沿用台账，解冻条件见[当前计划](../current.md)及[冻结记录](../tracking/native-freeze.json)。

按相同 item_id 去重后为 91 项；跨清单同名条目同步更新状态和证据。

解冻后的保留动作：

- BASE-02：按本条声明范围确认正式设置、输入身份和结果出口，再完成定向原生及关闭验收。新增条目可调用；既有入口可用；共用调整有相关回归
- BASE-04：Standalone已恢复，按D00x继续定向原生；FRU警告和既有任务历史写入问题分别诊断。
  当前缺口：当前连接和关闭通过，专项条件按子项。
- BASE-05：发行0.1.62沿用历史证据；D001—D013本轮96项已审查，首次完整验收3/10。累计十项后检查并构建/独立安装/stdio验收0.1.63。
- ED-01：内建属性证据沿用；散射资源过滤/精确名修复已合入。补BSDF正式文件选择、匹配ISX输入、追迹和重载；User诊断保留历史归属。
  当前缺口：BSDF文件选择未采用；ISScatterCatalog缺匹配ISX输入。Floating清除已完成。
- ED-02：材料八组和两种拾取已执行，取得新依据后继续Nd/Vd及实际拾取采用/联动。
  当前缺口：材料Nd/Vd超限，两种拾取未实际采用。
- ED-03：核对原生编辑器行操作、元数据、MFE/TDE文件及整系统保存重载证据，完成工作包收口。
- ED-04：FindBestAsphere原证据沿用；RayAiming须取得可靠执行、取消终态与关闭，再验preview/Apply及保存重载。
  当前缺口：RayAiming recorded timeouts remain under diagnosis.
- IM-01：GBM/RGB适配及stdio通过，继续独立成像、归一化和生命周期；ImageSimulation出口缺口保留。
  当前缺口：位图设置/结果出口已有；独立数值和生命周期待验。
- PO-01：四默认报告及N1/N2/N3有界探针已合入；从PhaseAberration正式选择/相位参考继续，再验偏振光线、透射与光纤专题独立参考。
  当前缺口：其余四项无专属设置 getter；分别探查正式 CFG 键、加载采用和结果契约。
- CO-01：三项原生Hologram1已完成，包内原生子项均已done；复核既有膜层/薄膜证据及包级优化衔接声明后完成工作包收口。
  当前缺口：原生子项已完成；工作包总声明的证据收口待审。
- MA-01：GlassMap身份346/346已匹配，消热差359/364参考通过；补5项材料数据、色散导数定义和专题选择。继续Gradium10/11阶、左端capping及波长归属。
  当前缺口：Remaining per-item runtime settings and controlled references need execution.
- NS-01：保留纯NSC转换历史379项参考和光线误差；取得混合组可执行正式路径后验设置、光线、保存重载、取消恢复和关闭。
- NS-02：已完成关键/单光线、ZRD读取及NSC几何MTF沿用；继续PathAnalysis阈值筛除后未分类功率的正式出口/定义及聚合证据。
- NS-03：已完NSC几何MTF沿用；本轮光源/光谱/照明/散射专题逐项审计完成。补正式输入、有效出口、角度/单位及数值和生命周期。
- NS-04：处方导出章节选择、分页/失败复用/重载已验；继续原生章节与面号选择，以及图纸/对象查看器有效出口。
  当前缺口：默认文本可用；正式选择及图形出口待取得。
- WP-01：既有高斯束/POP与文件读取证据沿用；光纤默认报告已合入。补光纤专题正式设置/复场参考及BeamFileViewer正式选择、显示和关闭。
- TO-01：QuickYield574已验收；继续本工作包剩余公差/补偿专题的正式输入、结果与状态条件。原生近似的高阶精度范围见acceptance574-reference.json。
- MF-01：TestPlate目录选择；SagTable面型拟合差异、制造偏移与反向摘要；图纸有效出口。
  当前缺口：目录选择及图纸出口仍缺；Zernike半径差3.8385445e-5mm>5e-6mm。
- CV-01：本轮图表/矩阵/全视场、FFT与STAR专题均已逐项审查；FFT留存复瞳复算仍超0.005。依各条正式出口、坐标定义、许可与独立参考恢复验收。
- CV-02：Power Map控制及图像内部合同已交付；继续零EFL/内部采样环、LightSource/EXD/PCI输入身份和独立数值参考，Gradium别名同步MA-01。
- RL-01：历史六工作流证据沿用；本轮D001—D013审查已完成，按剩余93组实际状态和每十项检查节奏安排下一轮及包级收口。
- EXT-STAR：模块启用后验证受控FEA、材料、拟合、组件、坐标和专题全生命周期。
  当前缺口：2026-11-09 IsSTARModuleEnabled=false，读取FEATURE_UNAVAILABLE；各专项参考缺口保留。
- EXT-HPC：取得正式非空IHPCSettings后验实际配置；节点条件满足后分别验四类作业。
  当前缺口：2026-11-09 preferences/custom均null，底层原因未区分。
- EXT-EXPORT：取得ASAT/ASAB、显式版本、配置层采用或线框/ZBB/ZEC正式创建路径后续验。
  当前缺口：2026-11-09 ASAT/ASAB拒绝、V30实际500、IGES四组合65535；创建工厂未找到。

共同功能去重后为 89 组。

源码能力：101 工具、132 种分析；发行能力见对应发行记录。

集中检查：每完成10组共同功能执行一次；距下次检查还需3项。

开发与进度按D00x及组内条目统计；独立任务的并行准备见[并行安排](../parallel-development.md)。每十项集中检查的节奏单独记录。

| 开发组 | 关联功能 | 初始项数 | 已完成 | 剩余 |
| --- | --- | ---: | ---: | ---: |
| D001 | 偏振、透射与光纤耦合 | 4 | 1 | 3 |
| D002 | 材料、色散与GRIN模型 | 6 | 2 | 4 |
| D003 | 顺序建模、拾取与模式转换 | 5 | 0 | 5 |
| D004 | 像质、光斑与屈光力分布 | 7 | 1 | 6 |
| D005 | 图像分析与输入文件查看 | 6 | 0 | 6 |
| D006 | 光源、光谱、色度与照明 | 10 | 0 | 10 |
| D007 | 散射模型与杂散光路径 | 6 | 0 | 6 |
| D008 | 制造、图纸、查看器与模型报告 | 9 | 0 | 9 |
| D009 | CAD与受保护格式交付 | 5 | 0 | 5 |
| D010 | 原生全息衍射效率 | 3 | 3 | 0 |
| D011 | STAR数据、材料、拟合与控制 | 16 | 0 | 16 |
| D012 | STAR组件、坐标与性能分析 | 14 | 0 | 14 |
| D013 | HPC配置与分布式任务 | 5 | 0 | 5 |

当前开发组：原生排期冻结；逐项顺序和动作见[remaining-ranked.md](../remaining-ranked.md)。

最近发行证据：

当前版本发行记录：development/evidence/BASE-04/release100.json。

以上检查数量属于对应发行记录；本轮新增执行另存证据，历史执行与当前执行分别记录。

历史 baseline/documented 沿用各自记录范围。条目完成需要实际设置、可用结果、相关数值或输出检查、关闭及文档证据。

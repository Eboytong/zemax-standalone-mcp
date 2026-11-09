# Zemax Standalone MCP 能力说明

1.0.0 正式版提供 101 个 MCP 工具和 132 种分析请求类型，面向本机 Windows x64、Python 3.14 与 OpticStudio 2024 R2。工具及请求 schema 与 1.0.0 wheel 同步。各专题的完成状态、限制和本机条件见专题页及接口矩阵。

历史原生计划包含 96 组共同功能，其中 7 组完成过完整验收，89 组保留原状态并冻结为后续工作。该历史计数不表示所有 132 种请求均已完成完整原生验收。项目当前进入维护阶段；发行验证和已知限制见 [1.0.0 发行记录](../development/evidence/BASE-04/release100.md)。

系统与文件、顺序建模、编辑器与配置、设计优化、光斑/MTF/波前/RMS、成像/偏振/镀膜/材料、非序列、POP、公差、几何与交付能力见[工具清单](reference/tools.md)、[请求模型](reference/tool-schemas.json)及[专题索引](reference/capabilities.md)。

任务支持查询、取消、分页、文件与报告；修改沿用工作副本、检查点及修订机制。

1.0.0包含偏振专题默认报告、系统/曲面文本报告及STAR专题入口与数据卸载能力；各项成熟度以专题文档、能力矩阵和发行证据为准。

历史B006验收包括POP/制造交付工作流、FFT线边扩散、NSC几何MTF、QuickYield、YNI、Speos两种导出、Floating口径清除及透射扇图；专题条件和数值证据见开发记录。

Gradium 637–639记录显示0–9阶为浮点精度，10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致；高阶正式求值、左端capping及专题选择仍未完成，见原生分析矩阵。

SagTable 640普通45项、641正负曲面原生2项通过，并有1001节点径向加权斜率摘要；制造偏移基准、面型拟合适用性及反向制造摘要仍未完成。

历史开发范围为内建61组、官方STAR30组及HPC5组，定义见[范围清单](../development/tracking/scope.json)。移出条目及原计划见[历史归档](../development/archive/scope-native-only-20261108/README.md)。

D001—D013及其余功能条目保留为历史计划和未来重新立项依据，当前不作为开发队列。项目处于维护阶段；发行限制和验证状态见[1.0.0发行记录](../development/evidence/BASE-04/release100.md)。


文档分区：guides为调用指南，reference为接口参考，topics为业务专题。开发入口为[development/README](../development/README.md)。

原D001—D013审查记录见[历史汇总](../development/evidence/BASE-04/d00x-pass-20261108/README.md)。

2026-11-08 parallel-02记录见[历史报告](../development/evidence/BASE-04/dsh-parallel-02-20261108.md)；该报告中的执行状态由后续1.0.0发行收口状态取代。


1.0.0包含[扩展衍射/部分相干图像入口](topics/imaging/scene-images.md)；专题限制与验收状态按对应文档记录。

1.0.0包含[NCE光源模式有类型请求及活动字段回读](topics/nonsequential/source-spectrum-viewer.md)；光谱专题的输入选择状态见专题文档。

# Zemax MCP Agent 开发任务书

更新日期：2026-11-07。已验收发行基线及安装包0.1.61（100工具/110种分析）；B005 10/10通过，当前执行B006，目标发行0.1.62。

目标：尽量完整覆盖本机 OpticStudio 2024 R2 通过公开接口和可复现路径实现的功能。执行按功能价值与依赖关系推进，以可调用、可验收的功能增量作为交付单位。

当前状态：发行与源码为0.1.61、100工具/110分析；B005集中验收通过，B006已完成5/10。当前行动、最近证据及下一条命令见 development-handoff.md；执行顺序见 [后续方案](next-development-plan.md)，历史计划见 development-history-pre438.md。

## 1. Agent 的入口与执行顺序

接手开发时，先读取以下文件：

| 文件 | 用途 |
| --- | --- |
| development-plan.md | 任务执行方式、优先级、交付和验收要求 |
| development-tasks.csv | 全部工作包、前置依赖、代码入口和当前状态 |
| development-backlog.csv | 原生分析逐项清单、唯一条目编号和执行状态 |
| ../能力说明.md | 已实现能力、已知差距和具体条件 |
| ../验证记录.md | 既有执行记录和测试范围 |
| ../README.md、usage.md、tools.md | 启动、安装、调用约定和工具入口 |
| ../src/zemax_mcp/ | 实际实现；开始修改前阅读本任务相关模块和测试 |

任务分三层组织：

1. 里程碑 M0–M7：用于汇总功能进展和安排发布。
2. 工作包：例如 AN-01、ED-02，定义一组相关能力。
3. 执行条目：例如 AN-01.RelativeIllumination，定义一次可以独立实现和验收的功能。

development-tasks.csv 是工作包索引；development-backlog.csv 是原生分析条目的执行清单。全部剩余工作包汇总见 development-remaining.md；逐项状态、后续动作和最新证据快照见 development-handoff.md。编辑器、系统工具等工作包在开始执行时拆成具体操作条目，并写入 development/ledgers/operations.csv，字段沿用第 5 节的条目结构。

共同功能归属见 development-functional-groups.json：SagTable统一由MF-01实现，GradiumProfile统一由MA-01实现；别名共享状态和证据，批次按canonical_item_id计一次。剩余源记录、不同条目编号和共同功能分别统计。

优先选择前置依赖满足、优先级最高的条目。同一工作包包含多个分析或原生工具时，逐项实现并验收。一个条目完成后更新记录，继续执行本轮范围内的下一个条目。

## 2. 当前基线

| 项目 | 已有情况 | 后续动作 |
| --- | --- | --- |
| MCP 工具 | 100 个工具，`run_analysis` 源码及0.1.61发行wheel均有110种请求；源码继续B006增量 | 在现有工具体系中扩展参数、分析和业务能力 |
| 通用分析 | `run_analysis` 通过通用与专题适配器提供曲线、网格、文本、图像及分页 | 每个新增分析记录原生设置来源、结果形态与任务关闭证据 |
| 原生分析矩阵 | 164 项：逐项入口与适配/验收状态见 native-analysis-matrix.csv 和 development-backlog.csv | 逐项清单记录当前实现、验收和阻塞条件 |
| 顺序建模 | 曲面参数、口径、偏心倾斜等已适配；顺序 solve 请求支持 9 种模式 | 按属性页、原生单元格及具体 solve 扩展 |
| 生命周期 | 已有任务查询、取消、工作副本、检查点、结果落盘和关闭回执 | 补任务追溯、历史结果发现和连续运行诊断 |
| 测试记录 | 0.1.61/B005：普通2381通过、741跳过；批次原生12项通过；wheel独立安装及schema/stdio通过 | 发行记录 BASE-04/release061.json；B006定向证据单独记录 |
| 已知诊断 | 重启后连接、许可和原生执行恢复；成功会话仍有 FRU__delta_init stderr 警告；旧启动超时及代理日志保留历史归属 | 继续剩余原生设置、结果、关闭验收及警告定位 |

源码事实以接手时的实现为准，历史数字和功能声明保留其记录来源。每次执行新增原生结果后，更新对应条目和证据路径。

## 3. 优先级与依赖

| 优先级 | 目标 | 工作包 |
| --- | --- | --- |
| P0 | 建立可执行的能力条目和进度基线 | BASE-01 |
| P1 | 尽快补齐高频分析、编辑器、solve 和设计工具 | BASE-02/04/05、AN-01～04、ED-01～05 |
| P2 | 扩展成像、偏振、镀膜、材料、NSC、传播、公差和制造交付 | BASE-03、IM/PO/CO/MA、NS、WP/TO/GE/MF |
| P3 | 完成剩余专门分析、扩展管理和发行收口 | CV-01/02、EX-01、RL-01 |
| 条件性专题 | 接入依赖许可、外部数据和接收环境的能力 | EXT-STAR/HPC/SPEOS/EXPORT |

里程碑之间按具体任务依赖衔接。M0 的台账和必要共用结构就绪后，即可开发高频功能；历史任务管理、发布流程和专题排查按各自依赖继续推进。

主要依赖关系：

- BASE-01 → 高频分析、编辑器与多数业务工作包。
- ED-01 → 镀膜属性、顺序/NSC 转换和部分制造输出。
- ED-03 → 扩展优化向导和公差专题。
- BASE-03 → HPC 任务管理。
- BASE-05 → RL-01 发布收口。
- 其余原生分析按逐项清单选择；共享的设置/结果结构随实际业务需求抽取。

原生 API 对同一系统中的 SystemTool 有单工具生命周期要求。原生执行和原生测试通过现有工作进程串行组织；任务中的设置、运行、轮询、取消及关闭由同一原生所有者完成。[原生工具接口](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_tools_1_1_i_optical_system_tools.xhtml)

## 4. 工作包目录

### M0：开发基础

| 编号 | 实施内容 | 代码入口 | 完成条件 |
| --- | --- | --- | --- |
| BASE-01 | 导入现有分析矩阵，建立全域能力台账骨架；登记 Analysis、SystemData、LDE/MFE/MCE/TDE/NCE、Tools、Files、STAR 等功能族；补首批条目元数据 | docs/、resources/、native.py | 原生分析均有唯一条目编号；各功能族有现状和工作包；首批条目可直接执行 |
| BASE-02 | 整理新增分析的登记、请求模型、设置和结果适配方式，接通工具文档及 schema 更新 | analysis_models.py、analyses.py、models.py、server.py | 首批分析可沿既有结构新增；共用调整覆盖当前条目所需结构，现有接口保持可用 |
| BASE-03 | 请求编号追溯、历史任务发现、结果 schema 版本、长结果读取 | bridge.py、backend.py、config.py | 按请求编号追溯执行记录；重启后读取已落盘结果；历史状态与当前活动任务清晰区分 |
| BASE-04 | 复现 FRU__delta_init；定位连续运行、异常释放和工具关闭的原生行为 | native.py、backend.py、原生生命周期测试 | 记录复现输入、步骤、结果和定位结论；已定位问题有修复及相关回归；未复现时记录实际探查范围 |
| BASE-05 | 记录源码版本基线，整理开发安装、wheel、启动和 stdio 发布流程 | pyproject.toml、install.ps1、start.ps1、verification/ | 本机独立安装可列工具、连接、执行分析并关闭；形成可重复运行的发布步骤 |

BASE-01 的台账随功能开发持续补充。BASE-02 在首批分析中完成所需共用调整，后续条目沿用并扩展。

### M1：高频分析

| 编号 | 执行条目 | 验收结果 |
| --- | --- | --- |
| AN-01 | RelativeIllumination、VignettingDiagramSettings、FootprintSettings | 设置实际采用；视场/波长、采样和渐晕条件完整；Footprint 保留曲面、坐标及有效光线信息 |
| AN-02 | FftMtfvsField、GeometricMtfvsField、HuygensMtfvsField、FftMtfMap、GeometricMtfMap | 频率、视场坐标、弧矢/子午标签、单位和采样明确；与同条件单视场结果对应 |
| AN-03 | GridDistortion、SeidelCoefficients、CardinalPoints、RayTrace | 保留原生量定义；用简单近轴/对称模型核对一阶量、像差项或光线坐标 |
| AN-04 | ThroughFocusSpot、RMSField、RMSFocus | 焦移、参考点、单位和视场归属明确；与既有光斑和离焦分析在相同条件下对应 |

现有 vignetting_action 已能计算和清除系统渐晕因子，AN-01 增加专题分析输出。相对照度和 FFT MTF 随视场已有公开设置接口，可作为首批适配条目。[相对照度](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_analysis_1_1_settings_1_1_extended_scene_1_1_i_a_s___relative_illumination.xhtml)、[MTF 随视场](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_analysis_1_1_settings_1_1_mtf_1_1_i_a_s___fft_mtfvs_field.xhtml)

### M2：建模、编辑器和设计工具

| 编号 | 拆分与实施顺序 | 验收结果 |
| --- | --- | --- |
| ED-01 | 依属性页拆分 SystemData/LDE；依次补口径、散射、Composite Surface、逐面 POP、绘图和其他公开属性 | 受支持字段可发现、读取和修改；活动性、可写性、实际采用及依赖关系明确 |
| ED-02 | 按 SolveType 和原生单元格支持情况拆分，每个 solve 独立定义参数 | 补现有九类之外的可用 solve；记录适用单元格、原生采用和持久状态 |
| ED-03 | 先补 TDE 的按行 update/delete/insert，再逐编辑器补缺失操作和文件入口 | 原生列类型、编号及插删后关系处理正确；失败返回已完成项和当前状态 |
| ED-04 | 每个优化向导或原生设计工具独立成条目：顺序/NSC/位图/照明向导、Scale、Quick Adjust、Find Best Asphere、非球面转换、Ray Aiming Wizard | 返回实际设置及模型修改摘要；可衔接现有优化、追迹和评估流程 |
| ED-05 | 镜头目录查询 → 候选筛选 → 加载/插入 → 材料替换与候选评价 | 目录来源和规格完整；候选使用各自基线工作副本，在相同条件下比较 |

主要入口：models.py、modeling.py、configurations.py、tolerancing.py、nonsequential.py，以及按任务需要增加的设计辅助适配模块。原生写入沿用现有检查点、修订号和部分失败处理。

### M3：图像、偏振、镀膜与材料

| 编号 | 执行范围 | 验收结果 |
| --- | --- | --- |
| IM-01 | Image Simulation、几何图像/位图分析、线/边扩散、扩展源包围能量 | 输入图像、物方尺寸、采样、色彩/波长、畸变和归一化条件完整；点源、条纹和边缘样例有可解释输出 |
| PO-01 | 偏振光线专题、偏振瞳图、Transmission、Phase Aberration、Transmission Fan | 电场坐标基底、振幅/功率、相位单位和光线有效性明确；简单界面与 Fresnel 参考对应 |
| CO-01 | 镀膜层读取 → 层编辑 → 角度/波长方向 R/T/A 与偏振性能 → 变量和评价函数衔接 | 层材料与厚度实际采用；简单膜系与独立薄膜计算对应 |
| MA-01 | 色散、Glass Map、Athermal Glass Map、内部透过率、材料属性与替换 | 材料目录、波长、厚度、温度和单位完整；折射率和透过率有可追溯参考 |

主要入口：analysis_models.py、analyses.py、modeling.py、files.py、evaluation.py、plotting.py、reports.py。[图像仿真接口](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_analysis_1_1_settings_1_1_extended_scene_1_1_i_a_s___image_simulation.xhtml)、[镀膜属性接口](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_editors_1_1_l_d_e_1_1_i_l_d_e_coating_data.xhtml)

### M4：非序列完整工作流

| 编号 | 执行范围 | 验收结果 |
| --- | --- | --- |
| NS-01 | 顺序转 NSC Group、关键光线生成/追迹、混合模式衔接 | 面号/对象映射、材料和坐标可追溯；代表性光线的转换前后位置、方向和功率对应 |
| NS-02 | Path Analysis、光线数据库、NSC 单光线、路径贡献排序、鬼像/杂散光流程 | 路径序列、分裂/散射和筛选条件完整；受控多界面模型中的主要路径及功率有参考 |
| NS-03 | 光源指向性/光谱/颜色、散射函数、波长通量、照明图、道路照明、NSC MTF | 统计量和光度定义明确；随机追迹采用预先确定的采样条件及统计容差 |
| NS-04 | NCE 属性、对象查看/表面数据、探测器变体、大网格/体素读取、原生数据文件 | 按对象和数据类型返回坐标、追迹条件和分块结果；现有探测器来源记录保持完整 |

主要入口：nsc_models.py、nonsequential.py、detector_readers.py、detectors.py、zrd_replay.py。荧光转换后波长细分差异作为具体问题条目记录探查条件、原生观测和可靠数据出口。[Path Analysis 接口](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_analysis_1_1_ray_tracing_1_1_i_a_s___path_analysis.xhtml)

### M5：传播、公差与制造交付

| 编号 | 执行范围 | 验收结果 |
| --- | --- | --- |
| WP-01 | 逐面 POP、输入/接收模式、近轴/偏轴高斯束、光纤耦合、Beam File Viewer | 束宽、相位、功率与耦合定义明确；解析高斯束和复场重叠积分提供参考 |
| TO-01 | Quick Sensitivity、Quick Yield、Tolerance Yield/Histogram、公差文件/脚本公开入口和补偿设置 | 分布、补偿、失败样本和良率分母完整；单参数模型核对灵敏度与统计量 |
| GE-01 | 实体来源、表示精度、介质区域、壁厚、间隙、接触关系 | 已知基本体及受控实体有数值参考；复杂实体问题可定位到具体对象与原因 |
| MF-01 | Design Lockdown、ISO/元件图、Sag Table、Prescription Graphic、测试板与制造数据 | 图纸尺寸、公差、材料与模型对应；生成可查看的交付文件 |

主要入口：pop_models.py、physical_optics.py、tolerancing.py、geometry_backend.py、geometry_kernel.py、exports.py、reports.py。[ISO 元件图接口](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_analysis_1_1_tolerancing_1_1_i_a_s___i_s_o_element_drawing.xhtml)

### M6：剩余公开能力与发布收口

| 编号 | 执行范围 | 验收结果 |
| --- | --- | --- |
| CV-01 | 剩余顺序分析：Pupil Aberration、矩阵/全视场光斑、RMS Map、全视场像差、Zernike 随视场、Surface Slope/Phase Slope、Foucault、Interferogram、Universal Plot 等 | 按逐项清单完成设置、执行、结果、模型范围和证据 |
| CV-02 | 部分相干/扩展衍射成像、双目、GRIN/Gradium、衍射效率、资源查看器和专门报表 | 逐项确认公开设置和结果出口，提供原生数值、文本或图像结果 |
| EX-01 | 用户分析、操作数、DLL 的资源登记/参数/生命周期，宏及加密导出的正式入口探查 | 各扩展类型有实际入口、依赖、参数及错误来源；可实现项形成独立条目 |
| RL-01 | 项目/归档/依赖管理、剩余导出、工作流例子、能力清单与 wheel 发行 | 已完成条目纳入版本；代表性工作流和发行记录完整 |

曲线、网格、RGB、散点、矢量和专门结果类型按实际接口适配，输出中记录结果来源和层级。[分析结果接口](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_analysis_1_1_data_1_1_i_a_r__.xhtml)

### M7：条件性专题

| 编号 | 前置条件 | 探查后交付 |
| --- | --- | --- |
| EXT-STAR | 实际 STAR 许可、FEA 文件和坐标/单位信息 | 载入、刚体位移/变形/折射率拟合、参考模型与 STAR 专题分析 |
| EXT-HPC | HPC 许可、节点和可用计算环境 | 最小任务、提交、状态、取消、结果回收，再覆盖 NSC/公差/全局/Hammer |
| EXT-SPEOS | 接收端环境和交换数据要求 | LensSystem/Whitebox 导出及接收端导入样例 |
| EXT-EXPORT | 本机正式出口、相应许可和样例 | 特殊格式、黑盒/加密导出中实际可运行的条目 |

每个专题先完成本机接口和依赖探查，记录实际条件，再拆分实现条目。官方文档使用 2024 R2 SP02；既有执行记录为 24.2.0/build240529，实际成员与行为以本机为准。[官方接口总表](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/annotated.xhtml)

## 5. 单个执行条目的任务契约

开始一个条目时，至少确定以下内容：

| 字段 | 要求 |
| --- | --- |
| item_id | 唯一编号；分析条目使用“工作包.原生枚举”，例如 AN-01.RelativeIllumination |
| work_package | 所属工作包 |
| priority / milestone | 开发顺序和汇总阶段 |
| depends_on | 本条目实际依赖的工作包或执行条目；分号分隔 |
| scope | 具体分析、设置集合或编辑操作 |
| entry_points | 需要阅读和修改的业务模块 |
| inputs | 原生样例/可构建模型、请求、外部资源与许可条件 |
| outputs | 可调用入口、请求模型、结果、例子、文档和必要测试 |
| acceptance | 设置采用、计算结果、生命周期及数值参考的具体完成条件 |
| execution_state | pending / in_progress / implemented / done / blocked |
| next_action | 下一项可直接执行的动作 |
| evidence | 运行命令、输出目录、结果文件和结论记录的位置 |
| blocked_reason | 具体外部缺项或经探查确认的接口问题及解除条件 |

编辑器、系统设置和工具条目的示例编号为 ED-03.TDE.update、ED-02.FNumber.<cell>、ED-04.Scale。条目粒度以“一次可独立调用并验收的功能增量”为准；一个条目涉及多组独立设置时，继续拆分子条目。

## 6. Agent 执行流程

1. **恢复上下文**：读取任务文档、索引和上一次交接；检查相关实现、测试、已落盘证据及当前任务状态。
2. **选择条目**：在本轮范围内，按优先级选择依赖满足的条目，写明本次实现的设置集合和验收目标。
3. **探查原生接口**：确认本机实际成员、枚举、系统模式、许可、设置可写性和结果出口；优先复用项目内已有适配。
4. **实现调用链路**：定义请求，写入并回读设置，启动原生执行，接通任务状态、结果读取和资源关闭。原生操作沿用现有修订号和失败处理。
5. **实现结果**：保留单位、坐标、配置、模型修订、实际设置和数据来源；按数据形态接通分页、文件和报告。
6. **执行相关检查**：运行与改动有关的普通测试和原生用例；数值功能使用提前确定的参考和容差。记录实际运行情况。
7. **完成交付**：更新工具/schema/示例、能力台账、条目状态和证据路径；修复本次相关失败。
8. **继续任务**：推进本轮清单中的下一条可执行条目，直到本轮范围完成或所余条目均有具体阻塞记录。

探查发现公开设置不完整时，先记录该条目的实际设置和输出能力，再评估原生配置文件或正式数据出口。暂缺许可、外部文件或接收端的条目写入具体解除条件，同时继续其他依赖满足的条目。

### 每十项集中验收（2026-11-05起）

基线为0.1.56，从0/10开始累计；批次记录见development-batches.json。逐项执行相关普通测试、原生设置回读/计算/结果/关闭，以及适用的数值、恢复和保存重载检查，更新schema、示例、台账及证据。共用模块变动补相关消费者定向回归。

每十个去重功能条目首次完成后，集中执行一次全量普通回归、批次跨模块原生回归、wheel构建、独立安装和真实stdio冒烟；首批通过后发布0.1.57。逐项不再构建和安装wheel。implemented转done计入；阻塞探查、重复记录、测试数量、修改次数、历史证据整理不计入。同一功能跨清单只计一次，不拆项凑数。批次失败先修复同一批，通过才重置计数。最终不足十项在整体收口时集中检查。原生实例串行，适用时复用stdio会话，各数值用例从独立模型基线开始。

当前发行与批次以 development-batches.json 和 development-handoff.md 为准。固定顺序、补位条目和逐项门槛见 next-development-plan.md。条件未变的已知阻塞保留探查结果和解除条件；有新接口或资源依据时再运行对应实验。

## 7. 完成状态与证据

| 状态 | 含义 |
| --- | --- |
| pending | 待执行；依赖满足后可领取 |
| in_progress | 正在探查或实现，next_action 指向当前具体步骤 |
| implemented | 调用链路已实现，仍有验收项待完成 |
| done | 本条目的声明范围已完成实现、相关检查和文档交付 |
| blocked | 有具体阻塞原因、已做探查和解除条件 |

逐项分析清单中的 baseline 表示已有适配基线，documented 表示已有产品移除或占位记录；其实际支持设置和验证范围沿用现有记录。新增条目的初始状态为 pending。

每个完成条目至少交付：

- 可通过实际 MCP 入口调用的实现及一个请求例子。
- 请求单位、编号、采样和结果定义。
- 相关普通检查和代表性原生执行记录。
- 数值功能的参考来源、容差和实际误差；文本/图像条目的可用输出。
- 原生关闭和任务终态记录。
- 更新后的文档、schema、条目状态及证据路径。

原生验收尚缺执行条件时，状态保留 implemented 或 blocked，并记录已完成部分及剩余动作。既有测试结果和本轮执行结果分别标明来源。

建议按条目将记录存入 .local/evidence/development/<item_id>/。每份记录包含请求、实际设置、版本/许可、模型条件、运行命令、结果、数值比较和关闭情况。

## 8. 当前执行清单

1. 已验收发行基线为0.1.61，B005 10/10；发行记录见BASE-04/release061.json。
2. 当前B006 5/10，POP、制造交付工作流、FFT线边扩散、NSC MTF和QuickYield已完成。其余四条工作流计入B005，原完成范围与证据沿用。
3. 按next-development-plan.md的B006固定队列及候补继续数值诊断和功能收口；同一条目保留声明范围、原始误差与容差。
4. 达到十个首次完成的共同功能后执行0.1.62集中验收；候选条件不足时保留实际计数及具体解除条件。

原 AN-01～04 首批功能已交付，其实现与历史记录继续保留在对应台账和专题文档。

## 9. 可直接交给 Agent 的执行指令

> 请在此项目中按照 development/plan.md、development/ledgers/packages.csv 和 development/ledgers/analyses.csv 继续开发。
>
> 本轮范围：B006，按next-development-plan.md与当前交接继续固定队列及候补，完成十个首次完成的共同功能后执行0.1.62集中验收。先读取最新探查结果，按仍缺的声明范围设计新实验。
>
> 每项功能完成原生接口探查、有类型请求、设置回读、执行、结果读取、资源关闭、相关检查及文档更新。按第 7 节记录实际状态和证据，完成一个条目后继续本轮下一条。
>
> 遇到缺少许可、输入资源或正式接口的问题，记录具体探查结果和解除条件，继续本轮其余可执行条目。结束时汇报本轮完成项、检查结果、剩余条目和下一步。

后续批次只需替换“本轮范围”为相应工作包或 item_id 清单。交接文档统一记录当前条目、修改入口、已执行命令及结果、原生实例/任务状态、剩余动作和具体阻塞，可保存在 development/handoff.md。

## 10. 全面覆盖的收口标准

覆盖进度分别统计：分析、编辑器、系统设置、原生工具、文件/导出和外部集成。每类记录已实现、已原生采用、已有数值参考和已完成工作流的条目数量。

每个里程碑以实际完成的条目形成发布批次。RL-01 汇总功能、检查和发行记录，并检查全域台账中的剩余能力：具备实现条件的条目继续进入任务队列；依赖外部条件或存在版本边界的条目保留具体依据和解除条件。

六个代表性工作流用于集成收口：顺序镜头优化与全视场评价、非球面/偏心系统建模、图像与偏振/镀膜分析、NSC 照明及路径分析、POP 耦合、公差与制造交付。


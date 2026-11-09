# Zemax MCP Agent 开发任务书

当前调度以[恢复状态](tracking/native-freeze.json)及[当前计划](current.md)为准。2026-11-08外部运行时在普通用户Medium下通过最小Standalone和独立真实stdio，启动统一冻结已解除。原生作业使用已验证的外部Python与Medium执行通道，DSH及自动执行安排另行登记。台账保留各项实际状态和条件。

维护状态（2026-11-09）：项目已停止新增功能开发并发行1.0.0。下文的逐项开发规范保留为历史证据口径和未来重新立项时的参考；1.0.0发行范围、限制和验证结果见[evidence/BASE-04/release100.md](evidence/BASE-04/release100.md)。

历史目标：补齐本机OpticStudio 2024 R2内建功能及官方STAR、HPC能力。范围定义见[scope.json](tracking/scope.json)。原96组共同功能按业务关联编排为D001—D013；当前状态以1.0.0发行记录和冻结台账为准。

当前状态：1.0.0发行包与源码以101个工具、132种分析请求为接口基线。历史96组计划中，发行前记录为7组完整验收、89组未完成；未完成项保留原状态并冻结。当前处理范围为已发行能力的维护性问题。

## 1. Agent 的入口与执行顺序

接手开发时，先读取以下文件：

| 文件 | 用途 |
| --- | --- |
| plan.md | 任务执行方式、优先级、交付和验收要求 |
| ledgers/packages.csv | 全部工作包、前置依赖、代码入口和当前状态 |
| ledgers/analyses.csv | 原生分析逐项清单、唯一条目编号和执行状态 |
| current.md、tracking/development-groups.json | D001—D013业务分组、组内顺序、实施计划及实际前置条件 |
| ../docs/README.md | 已实现能力、已知差距和具体条件 |
| ../development/evidence/verification-log.md | 既有执行记录和测试范围 |
| ../README.md、../docs/guides/usage.md、../docs/reference/tools.md | 启动、安装、调用约定和工具入口 |
| ../src/zemax_mcp/ | 实际实现；开始修改前阅读本任务相关模块和测试 |

任务分三层组织：

1. 里程碑 M0–M7：用于汇总功能进展和安排发布。
2. 工作包：例如 AN-01、ED-02，定义一组相关能力。
3. 执行条目：例如 AN-01.RelativeIllumination，定义一次可以独立实现和验收的功能。

ledgers/packages.csv 是工作包索引；ledgers/analyses.csv 是原生分析条目的执行清单。全部剩余工作包汇总见 generated/remaining.md；逐项状态、后续动作和最新证据快照见 handoff.md。编辑器、系统工具等工作包在开始执行时拆成具体操作条目，并写入 development/ledgers/operations.csv，字段沿用第 5 节的条目结构。

共同功能归属见 tracking/functional-groups.json：SagTable统一由MF-01实现，GradiumProfile统一由MA-01实现；别名共享状态和证据，批次按canonical_item_id计一次。剩余源记录、不同条目编号和共同功能分别统计。

执行优先顺序由tracking/development-groups.json维护：按D001—D013及组内顺序选择前置依赖满足的条目。每项先发布具体实施计划；完成后更新台账与证据，并继续下一可执行项。受阻时保存已做探查与解除条件，条件变化后回到最早可执行项。用户分派多个Agent时，按[并行安排](parallel-development.md)提前推进已划分归属的独立任务；共享入口统一集成，本机原生作业串行。D00x统一组织开发和进度统计，原有工作包保留责任范围；集中检查节奏见tracking/verification-cycle.json。

## 2. 当前基线

| 项目 | 已有情况 | 后续动作 |
| --- | --- | --- |
| MCP 工具 | 101 个工具，源码130种分析入口、0.1.62发行wheel为118种 | 在现有工具体系中扩展参数、分析和业务能力 |
| 通用分析 | `run_analysis` 通过通用与专题适配器提供曲线、网格、文本、图像及分页 | 每个新增分析记录原生设置来源、结果形态与任务关闭证据 |
| 原生分析矩阵 | 原生目录保留已知产品能力；当前计划分析台账163条记录，见 ../docs/reference/native-analysis-matrix.csv 和 ledgers/analyses.csv | 逐项清单记录当前实现、验收和阻塞条件 |
| 顺序建模 | 曲面参数、口径、偏心倾斜等已适配；顺序 solve 请求支持 9 种模式 | 按属性页、原生单元格及具体 solve 扩展 |
| 生命周期 | 已有任务查询、取消、工作副本、检查点、结果落盘和关闭回执 | 补任务追溯、历史结果发现和连续运行诊断 |
| 测试记录 | 0.1.62/B006：普通2590通过、819跳过；23项原生及2项独立安装原生通过 | 发行记录 evidence/BASE-04/release062.json；后续定向证据单列 |
| 已知诊断 | 2026-11-08外部运行时Medium最小Standalone及独立真实stdio均通过；此前Low上下文超时与FRU__delta_init警告沿各自记录保留 | 继续剩余原生设置、结果、关闭验收及警告定位 |

源码事实以接手时的实现为准，历史数字和功能声明保留其记录来源。每次执行新增原生结果后，更新对应条目和证据路径。

## 3. 优先级与依赖

| 优先级 | 目标 | 工作包 |
| --- | --- | --- |
| P0 | 建立可执行的能力条目和进度基线 | BASE-01 |
| P1 | 尽快补齐高频分析、编辑器、solve 和设计工具 | BASE-02/04/05、AN-01～04、ED-01～05 |
| P2 | 扩展成像、偏振、镀膜、材料、NSC、传播、公差和制造交付 | BASE-03、IM/PO/CO/MA、NS、WP/TO/GE/MF |
| P3 | 完成剩余专门分析、扩展管理和发行收口 | CV-01/02、RL-01 |
| 条件性专题 | 接入依赖许可及受控输入的官方模块 | EXT-STAR/HPC/EXPORT |

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
| RL-01 | 项目/归档/依赖管理、剩余导出、工作流例子、能力清单与 wheel 发行 | 已完成条目纳入版本；代表性工作流和发行记录完整 |

曲线、网格、RGB、散点、矢量和专门结果类型按实际接口适配，输出中记录结果来源和层级。[分析结果接口](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_analysis_1_1_data_1_1_i_a_r__.xhtml)

### M7：条件性专题

| 编号 | 前置条件 | 探查后交付 |
| --- | --- | --- |
| EXT-STAR | 实际 STAR 许可、FEA 文件和坐标/单位信息 | 载入、刚体位移/变形/折射率拟合、参考模型与 STAR 专题分析 |
| EXT-HPC | HPC 许可、节点和可用计算环境 | 最小任务、提交、状态、取消、结果回收，再覆盖 NSC/公差/全局/Hammer |
| EXT-EXPORT | 本机正式出口、相应许可和样例 | 特殊格式、黑盒/加密导出中实际可运行的条目 |

每个专题先完成本机接口和依赖探查，记录实际条件，再拆分实现条目。官方文档使用 2024 R2 SP02；既有执行记录为 24.2.0/build240529，实际成员与行为以本机为准。[官方接口总表](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/annotated.xhtml)

## 5. 单个执行条目的任务契约

开始一个条目时，至少确定以下内容：

| 字段 | 要求 |
| --- | --- |
| item_id | 唯一编号；分析条目使用“工作包.原生枚举”，例如 AN-01.RelativeIllumination |
| work_package | 所属工作包 |
| priority / milestone | 原始优先级和汇总阶段；当前开发顺序由D00x计划维护 |
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
2. **选择条目**：按D00x与组内顺序选择依赖满足的条目，先发布本次探查、实现、定向检查和完成条件。
3. **探查原生接口**：确认本机实际成员、枚举、系统模式、许可、设置可写性和结果出口；优先复用项目内已有适配。
4. **实现调用链路**：定义请求，写入并回读设置，启动原生执行，接通任务状态、结果读取和资源关闭。原生操作沿用现有修订号和失败处理。
5. **实现结果**：保留单位、坐标、配置、模型修订、实际设置和数据来源；按数据形态接通分页、文件和报告。
6. **执行相关检查**：运行与改动有关的普通测试和原生用例；数值功能使用提前确定的参考和容差。记录实际运行情况。
7. **完成交付**：更新工具/schema/示例、能力台账、条目状态和证据路径；修复本次相关失败。
8. **继续任务**：推进本轮清单中的下一条可执行条目，直到本轮范围完成或所余条目均有具体阻塞记录。

探查发现公开设置不完整时，先记录该条目的实际设置和输出能力，再评估原生配置文件或正式数据出口。暂缺许可或原生输入文件的条目写入具体解除条件，同时继续其他依赖满足的条目。

### 每十项集中验收（2026-11-05起）

检查节奏见tracking/verification-cycle.json，完成数从D00x条目及对应台账生成。逐项执行相关普通测试、原生设置回读/计算/结果/关闭，以及适用的数值、恢复和保存重载检查，更新schema、示例、台账及证据。共用模块变动补相关消费者定向回归。

每十个去重功能条目首次完成后，集中执行一次全量普通回归、受影响跨模块原生回归、wheel构建、独立安装和真实stdio冒烟。逐项不再构建和安装wheel。implemented转done计入；阻塞探查、重复记录、测试数量、修改次数、历史证据整理不计入。同一功能跨清单只计一次，不拆项凑数。集中检查失败先修复对应范围，通过后记录已检查的条目集合。最终不足十项在整体收口时集中检查。原生实例串行，适用时复用stdio会话，各数值用例从独立模型基线开始。

当前发行与检查节奏以tracking/verification-cycle.json和handoff.md为准。开发顺序、组内进度和逐项门槛统一按D00x，见current.md及tracking/development-groups.json。条件未变的已知阻塞保留探查结果和解除条件；有新接口或资源依据时再运行对应实验。

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

## 8. 历史执行清单

1. 0.1.62发行与B006集中验收记录见evidence/BASE-04/release062.json。
2. D001—D013范围、队列和逐项证据保留于current.md、handoff.md及台账。
3. 1.0.0维护状态、接口基线和当前验证门槛见evidence/BASE-04/release100.md。

## 9. 维护期入口

维护已发行接口时，先查[当前交接](handoff.md)和1.0.0发行证据；仅对发行范围内的问题提交修改、定向测试和必要原生复验。D00x未完成条目不在当前开发队列。
# 维护状态

2026-11-09：项目按 1.0.0 正式版进入维护阶段，D001—D013 后续功能开发已停止。本文以下开发流程为历史执行规范，保留用于追溯已完成工作的证据口径；重新启动功能开发需另行确定范围和计划。


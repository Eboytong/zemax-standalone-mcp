# D00x开发顺序与剩余工作

更新2026-11-09。当前94条待处理源记录、91个不同编号、89组共同功能；源码/发行1.0.0。当前开发组：原生排期冻结。

**原生开发与验收排期冻结。** 下表保留实际实现状态及解冻后的动作。冻结范围、可独立开展的离线工作和解冻条件见[当前计划](current.md)与[冻结记录](tracking/native-freeze.json)。

以D001→D013及组内编号作为调度优先级；独立任务的并行准备见[并行安排](parallel-development.md)，原难度作为估计信息保留。归属和顺序由[development-groups.json](tracking/development-groups.json)维护，实际状态、动作和证据来自三份台账。每十项集中检查见[verification-cycle.json](tracking/verification-cycle.json)。多个来源状态并列显示，原始逐行记录见[queue.json](generated/queue.json)。

每项先说明实施计划，依[长期规范第7节](plan.md#7-完成状态与证据)交付证据。依赖或许可受阻时记录具体条件，顺序处理下一可执行条目；条件变化后回到最早可执行项。实施说明见[当前计划](current.md)，运行前置问题见[交接](handoff.md)。

| 开发组 | 功能类别 | 初始项数 | 已完成 | 剩余 |
| --- | --- | ---: | ---: | ---: |
| [D001](#d001) | 偏振、透射与光纤耦合 | 4 | 1 | 3 |
| [D002](#d002) | 材料、色散与GRIN模型 | 6 | 2 | 4 |
| [D003](#d003) | 顺序建模、拾取与模式转换 | 5 | 0 | 5 |
| [D004](#d004) | 像质、光斑与屈光力分布 | 7 | 1 | 6 |
| [D005](#d005) | 图像分析与输入文件查看 | 6 | 0 | 6 |
| [D006](#d006) | 光源、光谱、色度与照明 | 10 | 0 | 10 |
| [D007](#d007) | 散射模型与杂散光路径 | 6 | 0 | 6 |
| [D008](#d008) | 制造、图纸、查看器与模型报告 | 9 | 0 | 9 |
| [D009](#d009) | CAD与受保护格式交付 | 5 | 0 | 5 |
| [D010](#d010) | 原生全息衍射效率 | 3 | 3 | 0 |
| [D011](#d011) | STAR数据、材料、拟合与控制 | 16 | 0 | 16 |
| [D012](#d012) | STAR组件、坐标与性能分析 | 14 | 0 | 14 |
| [D013](#d013) | HPC配置与分布式任务 | 5 | 0 | 5 |
| 合计 | 13个开发组 | 96 | 7 | 89 |

## D001

偏振、透射与光纤耦合。统一Jones基底、相位、透射功率和接收场归属，先延续当前相位像差工作。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 相位像差（`PO-01.PhaseAberration`） | 中 | 进行中 | 冻结 | 公开副本选择已交付179普通/1真实stdio；核对非主波长瞳映射，再补有限共轭、变换、镜面及实际取消。 条件：主波长切换后离轴光线差5.154093204594312e-5；设置拒绝并关闭副本。当前主波长选择/分页/PNG/重载通过；取消请求实际终态succeeded。 |
| 2 | 偏振光线专题（`PO-01.PolarizationRayTrace`） | 中 | 进行中 | 冻结 | 已核对正式Full单/批光线逐参数输出及GetGlobalMatrix；其几何/复场不含中间吸收、传播相位和偏振基底。复用29种CODA与默认专题，取得完整正式选择或中间量路径后继续，当前推进相位副本选择。 条件：默认逐面报告和选定面29种CODA量均可用；完整专题选择/全局坐标出口仍缺。相位、椭圆及偏振/非偏振功率原门槛已验。 |
| 4 | 光纤耦合专题（`WP-01.FiberCouplingSettings`） | 中 | 已实现待验收 | 冻结 | FICL选择路径已实现；快速解析参考27组全通过(最大4.7954e-4)。补Huygens同定义复场参考及椭圆NA/去心/倾斜/对准正式路径。 条件：Huygens与标量近轴解析参考最高采样仍差约0.02913，积分/传播定义未匹配；完整范围还缺椭圆NA、接收器位姿/对准选择及对应正式覆盖。 |

## D002

材料、色散与GRIN模型。共用材料目录、波长、温度和折射率定义，集中核对已有实现的数值与输入身份。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 玻璃图（`MA-01.GlassMap`） | 中 | 受阻 / 已实现待验收 | 冻结 | 公共导出成员补查未取得图表模板/ReferenceGlass设置，仅发现材料ExcludeSubstitution；沿用既有目录与数值证据，取得正式图表设置或模板条件后补完整边界筛选与生命周期。 条件：系统目录身份已验；AS_Default仍无图边界/替代模板设置，d线固定，无专题波长选择要求。 |
| 2 | 消热差玻璃图（`MA-01.AthermalGlassMap`） | 中 | 受阻 / 已实现待验收 | 冻结 | 公共导出成员补查未取得图表模板/ReferenceGlass设置，仅发现材料ExcludeSubstitution；沿用既有目录与数值证据，取得正式图表设置或模板条件后补完整边界筛选与生命周期。 条件：当前数值缺口已解释；AS_Default仍无专题功率边界、替代模板及参考玻璃设置。F2HTi原AGF占位保留，当前参考使用正式实际系数。 |
| 5 | 临时材料模型（`ED-02.MaterialModel.Material`） | 高 | 已实现待验收 | 冻结 | 8个环境/重载用例排除缓存；模型玻璃对应固定20°C空气修正，N-BK7独立环境参考12点最大4.44e-16。继续正式模型色散/温度定义、Nd/Vd原超限、dPgF及失败恢复。 条件：Nd/Vd仍超原门槛；完整模型色散算法和温度处理依据未取得。UpdateStatus及保存重载不改变10/30°C模型结果，非本轮缓存问题。 |
| 6 | Gradium完整剖面（`MA-01.GradiumProfile`） | 高 | 进行中 | 冻结 | 双波长GrinProfile实际选择/101点归属已验；继续10/11阶求值、负profile/capping传播和专题选择，复用既有同条件证据。；2026-11-09四种写入顺序最终采用相同；负profile段传播error2，起点z=.21/profile=.01成功。取得正式负坐标扩展依据或最小修复后复验；继续10/11阶求值及专题选择。 条件：写入顺序已排除；负profile/capping段传播失败原因、高阶求值偏差及专题选择入口仍未解决。 |

## D003

顺序建模、拾取与模式转换。集中处理原生修改实际采用、solve联动、任务终态及顺序/NSC模型转换。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | ChipZone曲面拾取（`ED-02.SurfacePickup.ChipZone`） | 受阻待定 | 受阻 | 冻结 | 取得实际可采用并持久化SurfacePickup的正式路径后重跑已修复helper；更新/光线/两次重载/源值扰动均Automatic，已有部分失败恢复和正常关闭证据。 条件：2026-11-09完整原生流程error=null，目标仍Automatic、无时刻采用SurfacePickup、联动失败；代表光线/预检查/检查点恢复/两次重载/关闭已执行。 |
| 2 | 机械半口径拾取（`ED-02.SurfacePickup.MechanicalSemiDiameter`） | 受阻待定 | 受阻 | 冻结 | 取得实际可采用并持久化SurfacePickup的正式路径后重跑helper；受控净口径已小于机械尺寸，目标仍Fixed，联动失败，已有恢复/重载/关闭证据。 条件：2026-11-09排除初始净口径钳制后完整原生流程error=null，目标仍Fixed、联动失败；代表光线/预检查/检查点恢复/两次重载/关闭已执行。 |
| 3 | Ray Aiming完整生命周期（`ED-04.RayAimingWizard`） | 受阻待定 | 受阻 | 冻结 | 取得可到终态且可关闭的原生执行路径；再验preview/Apply、保存重载与RayAiming状态。保留TimedOut及Close=false原始记录。 条件：受控模型正式 RunAndWaitWithTimeout(10) 返回 TimedOut；Cancel=true 后 WaitWithTimeout(10) 仍 TimedOut 且 IsRunning=true；Close=false。Ray Aiming 设置相同，完整模型保持未完成；应用断连成功。 |
| 4 | 顺序转NSC混合组（`NS-01.Conversion`） | 受阻待定 | 已实现待验收 | 冻结 | 保留纯NSC转换379项历史参考；取得可靠混合组转换路径后核对设置、光线、取消、检查点恢复、保存重载与关闭。 条件：混合组在dummy边界、关闭光阑孔径转换下仍TASK_START_FAILED / An unknown error occurred；失败工具关闭和检查点恢复已通过。父项保留implemented及纯NSC已验收范围。 |
| 5 | 扩展solve聚合范围（`ED-02.SolveExtensions018`） | 受阻待定 | 已实现待验收 | 冻结 | 保留27类solve审计表；先完成MaterialModel及两种SurfacePickup的原门槛，再验聚合声明范围。 条件：依赖当前范围内的MaterialModel及SurfacePickup子项。 前置：ED-02.MaterialModel.Material、ED-02.SurfacePickup.ChipZone、ED-02.SurfacePickup.MechanicalSemiDiameter。 |

## D004

像质、光斑与屈光力分布。共用视场、瞳坐标、参考点和采样，处理网格有效性及像质结果出口。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 屈光力随视场Map（`CV-02.PowerFieldMapSettings`） | 高 | 已实现待验收 | 冻结 | 2026-11-09 E2四半径/16任务、E3四孔径控制及真实stdio分页/重载已执行；小至3.407e-7D仍有限非零，截光改变但查询差仅浮点量级。继续内部微分环有效性和零EFL正式语义。 条件：中央参考光线、分页和重载已验；原生内部微分采样环状态及平面raw-zero/EFL定义尚缺正式依据。旧启动超时已解除。 |
| 2 | 屈光力随瞳Map（`CV-02.PowerPupilMapSettings`） | 高 | 已实现待验收 | 冻结 | 2026-11-09 E2四半径/16任务、E3四孔径控制及真实stdio分页/重载已执行；小至3.407e-7D仍有限非零，截光改变但查询差仅浮点量级。继续内部微分环有效性和零EFL正式语义。 条件：中央参考光线、分页和重载已验；原生内部微分采样环状态及平面raw-zero/EFL定义尚缺正式依据。旧启动超时已解除。 |
| 4 | 全视场光斑（`CV-01.FullFieldSpot`） | 高 | 已实现待验收 | 冻结 | 复用2026-11-09公开采样合同：取得有效逐光线/图形出口或覆盖采样、权重、apodization、scatter及参考点的正式等价路径后验收；同条件空出口不重跑。 |
| 5 | 矩阵光斑（`CV-01.MatrixSpot`） | 高 | 已实现待验收 | 冻结 | 复用2026-11-09公开采样合同：取得有效逐光线/图形出口或覆盖采样、权重、apodization、scatter及参考点的正式等价路径后验收；同条件空出口不重跑。 条件：Standard SpotData duplicates selected aggregate across wavelength slots and has no per-ray dimension; matrix outlets remain empty. Current selector1/configuration metadata separated and stdio regression passed. |
| 6 | 配置矩阵光斑（`CV-01.ConfigurationMatrixSpot`） | 高 | 已实现待验收 | 冻结 | 复用2026-11-09公开采样合同：取得有效逐光线/图形出口或覆盖采样、权重、apodization、scatter及参考点的正式等价路径后验收；同条件空出口不重跑。 条件：Standard SpotData duplicates selected aggregate across wavelength slots and has no per-ray dimension; matrix outlets remain empty. Current selector1/configuration metadata separated and stdio regression passed. |
| 7 | FFT Surface MTF（`CV-01.FftSurfaceMtf`） | 很高 | 已实现待验收 | 冻结 | 2026-11-09格点面积权重控制离轴仍0.075425/0.122374>0.005；保留原门槛，取得正式复瞳相位/支持域依据或可区分参考球相位控制后继续。 条件：方向坐标及面积Jacobian权重均未解除独立离轴残差；正式复瞳参考球相位/支持域尚未对应。 |

## D005

图像分析与输入文件查看。统一受控文件选择、输入身份、像素或复场坐标以及归一化。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 光束文件查看器（`WP-01.BeamFileViewer`） | 高 | 已实现待验收 | 冻结 | 2026-11-09公共ToFile/showSettings及parent字典探查未取得额外选择器；2026-11-09原生一网格/文本，但报告未定义文件；取得正式ZBF选择并核对图像身份后执行独立复场及坐标参考。 条件：AS_Default无正式文件选择；默认非空网格未绑定实际输入文件，启动条件已恢复。 |
| 2 | 位图查看器（`CV-02.BitmapFileViewer`） | 高 | 受阻 | 冻结 | 2026-11-09公共ToFile/showSettings及parent字典探查未取得额外选择器；2026-11-09原生AS_Default，八类集合0、文本导出false；取得正式文件选择及图像出口后验受控非对称输入。 条件：文件选择和正式图像出口仍缺；实例创建与正常关闭已执行。 |
| 3 | 几何位图图像分析（`IM-01.GeometricBitmapImageAnalysis`） | 高 | 已实现待验收 | 冻结 | 2026-11-09公共ToFile/showSettings及parent字典探查未取得额外选择器；Off-axis six source sizes and two aperture-area references passed; obtain formal symmetric-efficiency semantics/fix and complete Parity/Source/Normalize/Wavelength/Reference settings plus physical origin. 条件：Native reported efficiency depends on source parity and field symmetry: 4x4 axial400%, Y-only200%, X-nonzero100%. Complete setting selectors/physical origin remain unconfirmed. |
| 4 | 光源分析（`CV-02.LightSourceAnalysis`） | 高 | 受阻 | 冻结 | 2026-11-09公共ToFile/showSettings及parent字典探查未取得额外选择器；复用200/100/200mm有限共轭模型与RGB/XYZ解析；取得DAT/SDF正式文件选择后确认实际身份、波长、W/lm与独立通量参考。 条件：有限共轭要求已满足；源名为空、探测器零尺寸/零功率，DAT/SDF正式选择仍缺。完整文本出口已确认。 |
| 5 | 扩展衍射图像（`CV-02.ExtendedDiffractionImageAnalysis`） | 高 | 已实现待验收 | 冻结 | 2026-11-09公共ToFile/showSettings及parent字典探查未取得额外选择器；四键CFG/报告采用、256x256网格、分页/PNG及关闭已通过；继续输入文件/相干/OTF设置、独立衍射参考及物理坐标。 条件：输入文件身份和完整衍射设置/独立参考未完成，已确认设置及结果适配已交付。 |
| 6 | 部分相干成像（`CV-02.PartiallyCoherentImageAnalysis`） | 很高 | 已实现待验收 | 冻结 | 2026-11-09公共ToFile/showSettings及parent字典探查未取得额外选择器；视场/波长CFG采用和13x13结果适配、9x7重采样探查及分页/PNG/关闭通过；继续文件/复场身份、相干参数和积分参考。 条件：文件选择、Gamma/Alpha/Fraction、完整部分相干积分和物理坐标定义仍待确认。 |

## D006

光源、光谱、色度与照明。按光谱身份、角分布、色度和照明结果衔接，集中处理光度单位及通量归一化。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 光源光谱查看器（`NS-03.SourceSpectrumViewer`） | 中 | 已实现待验收 | 冻结 | 四组NCE黑体/XYZ已采用且Fit变化，但独立查看器20行恒定；十模式有类型请求/活动字段回读已修复。取得专题正式模式、数值/文件选择并回读后，按原门槛验光谱和色度。 条件：正式专题输入选择仍缺；NCE四源设置变化与独立查看器结果不联动，不能据此替代专题输入。 |
| 2 | 光通量随波长（`NS-03.FluxvsWavelength`） | 中 | 受阻 | 冻结 | 手册1024—1025页确认输入为指定ZRD/SDF及命中对象，含光线范围/Filter/Bins和两bin平滑；取得正式数据库/对象/分箱选择及回读后，以已知谱线段功率建立参考。 条件：AS_Default缺数据库、对象和分箱正式选择；当前探测器累积数据不足以绑定专题；SDF选择及两bin端点/权重尚待正式依据。 |
| 3 | 方向性图（`NS-03.DirectivityPlot`） | 中 | 已实现待验收 | 冻结 | 正式IES文件与扫描角选择确认后，使用新自有asymmetric-cosine.ies及解析参考验采用、角度和归一化。 条件：已准备非对称IES；原生仍选择默认sample.ies，正式文件/扫描角选择及回读缺失。 |
| 4 | 1931色度图（`CV-01.SourceColorChart1931`） | 中 | 受阻 | 冻结 | 取得色度图坐标/图像正式出口与输入选择，再建立CIE1931受控数值/图形参考。 条件：原生图表数据/图像出口仍缺；当前任务成功状态未提供图表内容。 |
| 5 | 1976色度图（`CV-01.SourceColorChart1976`） | 中 | 受阻 | 冻结 | 取得色度图坐标/图像正式出口与输入选择，再建立CIE1976受控数值/图形参考。 条件：原生图表数据/图像出口仍缺；当前任务成功状态未提供图表内容。 |
| 6 | 光源极坐标查看器（`NS-03.SourcePolarViewer`） | 中 | 受阻 | 冻结 | 使用已准备非对称IES确认正式选择，核对水平角节点/像素范围定义、单位及方向；再接入请求和网格。 条件：专题文件选择和角度轴合同未确认；默认对称sample.ies无法区分水平选择，360/19与文件20度节点差仍需正式定义。 |
| 7 | 光源照明分布（`NS-03.SourceIlluminationMap`） | 中 | 受阻 | 冻结 | 取得正式源/照明输入选择和有效网格或图像出口后，以探测器对照坐标及通量。 条件：正式照明输入及有效结果出口缺失；当前默认任务无输出。 |
| 8 | 光致发光查看器（`NS-03.PhotoluminscenceViewer`） | 中 | 受阻 | 冻结 | 取得正式有效模型/数据条件及选择方式后，用受控光致发光输入重验。 条件：原生报告输入无效数据/设置；有效输入合同仍缺，消息Success枚举未作为功能成功依据。 |
| 9 | Radiant光源模型查看器（`NS-03.RadiantSourceModelViewerSettings`） | 中 | 受阻 | 冻结 | 取得所需旗舰版许可及匹配Radiant输入后，验证正式选择、非空图像/数据与关闭。 条件：本轮原生明确提示仅OpticStudio旗舰版支持；同时需匹配Radiant源模型资源。 |
| 10 | 道路照明（`NS-03.RoadwayLighting`） | 中 | 受阻 | 冻结 | 构造道路专用受控模型并取得正式设置选择/回读；利用新文本出口核对八项指标与NSC照度参考。 条件：已有默认零指标文本；道路专用输入、正式设置采用及受控指标参考待确认。 |

## D007

散射模型与杂散光路径。共用BSDF/IS资源、散射角和功率定义，衔接散射设置、图表及路径统计。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | BSDF散射（`ED-01.Scattering.BSDF`） | 受阻待定 | 受阻 | 冻结 | 取得LDE正式BSDF选择器枚举并采用真实文件的路径或厂商修复后，验参数、追迹和重载；NCE已有17文件及basename采用新对照。 条件：实际ScatterDir已有17个BSDF；Application/System刷新及显式ISurfaceScatteringBSDF均未解除LDE仅“无”。NCE同资源basename可采用，顺序范围仍未通过。 |
| 2 | IS散射目录（`ED-01.Scattering.ISScatterCatalog`） | 受阻待定 | 受阻 | 冻结 | 取得有来源且匹配原生目录的ISX，执行精确名称选择、参数、追迹和重载。 条件：2026-11-09安装ZemaxData及用户Documents/Zemax搜索均无ISX；其他位置未作结论。 |
| 3 | 散射函数查看器（`NS-03.ScatterFunctionViewer`） | 中 | 受阻 | 冻结 | 取得正式输入和有效曲线/网格/文本/图形出口后，以受控散射模型验方向、单位和归一化。 条件：2026-11-09本机AS_Default任务成功，但八类集合0、文本false；设置/曲面保持及关闭已通过。 |
| 4 | 散射极坐标图（`NS-03.ScatterPolarPlotSettings`） | 中 | 受阻 | 冻结 | 确认正式输入绑定及角度定义后，验证模型变化、积分、分页和关闭。 条件：2026-11-09原生181x90常数1/pi网格，Dx1.011235955、Dy1.988950276；正式输入和角度定义未确认，正常关闭。 |
| 5 | 路径分析未分类功率（`NS-02.PathAnalysis`） | 高 | 已实现待验收 | 冻结 | PAF非默认阈值/范围静默忽略已修复并真实stdio验收；取得ZRD阈值排除后未分类有效出口或正式修复依据，按原功率门槛复验。 条件：同次追迹单/多路径对照：PAF阈值及首末范围回读成功但未生效，公共请求已拒绝；ZRD筛除路径后GetPathUncategorized仍称无路径。默认功率、分页、重载、关闭通过。 |
| 6 | 散射类型聚合范围（`ED-01.Scattering`） | 受阻待定 | 已实现待验收 | 冻结 | 已验内建类型沿用；待BSDF选择和ISScatterCatalog资源条件解除后补齐原生参数、追迹和持久性。User历史异常留在诊断记录。 条件：内建散射聚合剩余为BSDF正式文件选择及匹配ISX输入、追迹和重载。 前置：ED-01.Scattering.BSDF、ED-01.Scattering.ISScatterCatalog。 |

## D008

制造、图纸、查看器与模型报告。集中处理章节、曲面、目录或对象的正式选择，以及可查看的文本/图纸/几何结果出口。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 系统说明文本报告（`NS-04.PrescriptionDataSettings`） | 中 | 已实现待验收 | 冻结 | 导出章节筛选已验收；等待原生章节开关正式选择/回读证据。 条件：AS_Default无章节设置字段；sections仅筛选原生导出文本并明确native_settings_modified=false。 |
| 2 | 曲面数据报告（`NS-04.SurfaceDataSettings`） | 中 | 已实现待验收 | 冻结 | 等待正式面号选择与采用回读接口/设置键证据；默认多面报告已有原生解析。 条件：SurfaceDataSettings为AS_Default；已检查公开成员、配置及报告，没有面号选择字段。默认报告标题为表面1。 |
| 3 | 样板目录（`MF-01.TestPlateList`） | 高 | 已实现待验收 | 冻结 | 正式CFG LoadFrom与活动Applied目录真实stdio重放通过；仍需取得并重放第二个实际选择目录CFG，目录选择新证据后续验。 条件：Atoptical请求加载TPL.CFG后原生报告仍为Applied.tpd；身份核对正确拒绝。AS_Default无有类型目录成员；GUI保存的配置未采用第二目录。 |
| 4 | SagTable完整制造范围（`MF-01.SagTable`） | 高 | 已实现待验收 | 冻结 | 取得面型相关BFS算法/精度或正式修复依据后按原门槛复验；等价基底40/80/Infinity及33—513网格均未解除Zernike差异。继续制造偏移基准和反向摘要。；材料侧制造方向和光阑包围孔径副本修复已验：108普通、5串行原生，148项参考最大5.76e-16；继续RMS制造偏移、反向摘要和Zernike半径3.84e-5mm超限的正式定义/修复依据，保持原5e-6mm门槛。 条件：102个解析矢高通过；EvenAspheric半径差约5.5e-9mm，Zernike仍3.84e-5mm>5e-6mm；等价基底及五档DSAG采样均未解除，保存既有制造偏移/反向摘要缺口。 条件：四材料侧证明BFSD与DSAG制造合同不同，不能直接互填偏移；RMS物理偏移/反向制造摘要及Zernike面型拟合误差仍待解决。 |
| 5 | ISO元件图（`CV-01.ISOElementDrawing`） | 高 | 受阻 | 冻结 | 取得正式选择及有效图纸/对象图形出口后验身份、内容和生命周期。 条件：2026-11-09适用Cooke或Boolean Lens Mount副本上任务成功但八类集合0、文本false；模型保持和关闭通过。 |
| 6 | Zemax元件图（`MF-01.ZemaxElementDrawing`） | 高 | 受阻 | 冻结 | 取得正式选择及有效图纸/对象图形出口后验身份、内容和生命周期。 条件：2026-11-09适用Cooke或Boolean Lens Mount副本上任务成功但八类集合0、文本false；模型保持和关闭通过。 |
| 7 | 系统说明图（`NS-04.PrescriptionGraphic`） | 高 | 进行中 | 冻结 | 取得正式选择及有效图纸/对象图形出口后验身份、内容和生命周期。 条件：2026-11-09适用Cooke或Boolean Lens Mount副本上任务成功但八类集合0、文本false；模型保持和关闭通过。 |
| 8 | NSC对象查看器（`NS-04.NSCObjectViewer`） | 高 | 进行中 | 冻结 | 取得正式选择及有效图纸/对象图形出口后验身份、内容和生命周期。 条件：2026-11-09适用Cooke或Boolean Lens Mount副本上任务成功但八类集合0、文本false；模型保持和关闭通过。 |
| 9 | 零件查看器（`NS-04.PartViewer`） | 高 | 进行中 | 冻结 | 取得正式选择及有效图纸/对象图形出口后验身份、内容和生命周期。 条件：2026-11-09适用Cooke或Boolean Lens Mount副本上任务成功但八类集合0、文本false；模型保持和关闭通过。 |

## D009

CAD与受保护格式交付。统一导出设置、实际文件格式与版本、配置分层和正式创建协议。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | CAD实际格式与版本（`EXT-EXPORT.CadSettings`） | 受阻待定 | 已实现待验收 | 冻结 | 取得实际支持ASAT/ASAB及显式版本的正式路径后重验；当前原生拒绝和版本头诊断保留。 条件：2026-11-09 ASAT/ASAB仍Unsupported export format；SAT/SAB的V30实际头500，拒绝/复用和关闭通过。 |
| 2 | CAD多配置分层（`EXT-EXPORT.CadMultipleConfigurations`） | 受阻待定 | 受阻 | 冻结 | 显式顺序IGES无光线的输出层号拒绝与STEP复用已验；取得能实际输出请求配置层号的正式路径后重验完整分层。 条件：2026-11-09双配置STEP五模式几何/保持通过；IGES仍65535，现明确返回SETTING_REJECTED并保留文件。普通121、拒绝/复用原生1通过；完整分层仍待原生采用。 |
| 3 | 旧线框导出（`EXT-EXPORT.LegacyLinework`） | 受阻待定 | 受阻 | 冻结 | 取得本机支持的旧线框正式创建协议/工厂、参数和输出/关闭依据后实现。 条件：2026-11-09公开程序集908类型及Tools接口扫描未取得旧线框创建工厂；仍需正式协议。 |
| 4 | 黑盒创建（`EXT-EXPORT.BlackBox`） | 受阻待定 | 受阻 | 冻结 | 取得本机支持的ZBB正式创建协议/工厂、参数和输出/关闭依据后实现。 条件：2026-11-09公开程序集908类型及Tools接口扫描未取得ZBB创建工厂；仍需正式协议。 |
| 5 | 加密镀膜创建（`EXT-EXPORT.EncryptedCoating`） | 受阻待定 | 受阻 | 冻结 | 取得本机支持的ZEC正式创建协议/工厂、参数和输出/关闭依据后实现。 条件：2026-11-09公开程序集908类型及Tools接口扫描未取得ZEC创建工厂；仍需正式协议。 |

## D011

STAR数据、材料、拟合与控制。建立受控FEA数据的读取、导入、拟合、材料计算、控制及卸载链路。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | STAR读取（`EXT-STAR.Read`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：Application reports IsSTARModuleEnabled=True with a controlled FEA model；verify value readback, paging, save/reload, recovery and close with original tolerances 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; no controlled FEA instance；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 2 | STAR更新模式（`EXT-STAR.UpdateMode`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module；verify enum adoption, DoManualUpdate effect, save/reload and mode restore on cancel 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 3 | STAR材料折射率（`EXT-STAR.Materials.refractive_index`） | 受阻待定 | 受阻 | 冻结 | 取得返回有限正折射率的正式材料查询；核对目录、环境/材料温压与绝对/相对折射率定义，沿用原门槛并检查目录关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；N-BK7/N-F2、三种目录、六组条件历史均返回0，native190为0通过/1失败；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 4 | STAR材料dn/dT（`EXT-STAR.Materials.dndt`） | 受阻待定 | 受阻 | 冻结 | 对确认材料/目录及显式环境条件，以固定环境下折射率中心温差建立dn/dT参考；核对原生参数、零/负合法值、目录关闭及原门槛。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；历史GetDNDT返回0；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 5 | STAR热控设置（`EXT-STAR.ThermalControls`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module；verify fit_type/wavelength adoption readback, save/reload, restore 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; fit_type integer semantics unconfirmed；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 6 | STAR体积控制（`EXT-STAR.VolumeControls`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module；verify both GRINStep members adopted and final combination readback, save/reload 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; physical step convention unconfirmed；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 7 | STAR导入形变（`EXT-STAR.ImportDeformation`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module + controlled deformation file matching lens units；verify import readback, independent deformation/normal reference, save/reload, recovery 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; no controlled deformation FEA input；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 8 | STAR拟合形变（`EXT-STAR.FitDeformation`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module + imported deformation；verify fit settings adoption, apply/enable state, numeric fit reference (1e-8 lens-unit + 1e-6 x ref), save/reload, restore 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; requires imported deformation data；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportDeformation。 |
| 9 | STAR导入温度（`EXT-STAR.ImportTemperature`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module + controlled temperature file；verify import readback, thermal reference (1e-6 degC + 1e-6 x ref), save/reload 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; no controlled temperature FEA input；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 10 | STAR拟合温度（`EXT-STAR.FitTemperature`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module + imported temperature；verify fit adoption, thermal numeric reference, save/reload 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; requires imported temperature data；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportTemperature。 |
| 11 | STAR导入直接折射率（`EXT-STAR.ImportDirectIndex`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module + controlled index file；verify import readback, index reference (1e-8 + 1e-7 x ref), save/reload 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; no controlled index FEA input；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 12 | STAR拟合直接折射率（`EXT-STAR.FitDirectIndex`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module + imported index；verify fit adoption, index numeric reference, save/reload 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; requires imported index data；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportDirectIndex。 |
| 13 | STAR拟合采样（`EXT-STAR.FittedSamples`） | 受阻待定 | 受阻 | 冻结 | STAR模块启用且受控FEA输入可用后，完成本条正式设置采用、数值、保存重载、取消/恢复与关闭；具体步骤：enable module + imported data；verify fitted sample values against independent reference 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；IsSTARModuleEnabled=false; requires imported data for sampling；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.FitDeformation、EXT-STAR.FitTemperature、EXT-STAR.FitDirectIndex。 |
| 14 | STAR卸载形变（`EXT-STAR.UnloadDeformation`） | 受阻待定 | 受阻 | 冻结 | 主仓StarUnload三种请求已合入；STAR启用并有自有FEA副本后，分别验证导入标志清除、源文件存在、检查点恢复、取消、保存重载及正常关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportDeformation。 |
| 15 | STAR卸载温度（`EXT-STAR.UnloadTemperature`） | 受阻待定 | 受阻 | 冻结 | 主仓StarUnload三种请求已合入；STAR启用并有自有FEA副本后，分别验证导入标志清除、源文件存在、检查点恢复、取消、保存重载及正常关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportTemperature。 |
| 16 | STAR卸载直接折射率（`EXT-STAR.UnloadDirectIndex`） | 受阻待定 | 受阻 | 冻结 | 主仓StarUnload三种请求已合入；STAR启用并有自有FEA副本后，分别验证导入标志清除、源文件存在、检查点恢复、取消、保存重载及正常关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportDirectIndex。 |

## D012

STAR组件、坐标与性能分析。复用受控拟合数据，完成组件生命周期、刚体坐标及六项STAR专题结果。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | STAR定义组件（`EXT-STAR.Components.define`） | 受阻待定 | 受阻 | 冻结 | 模块启用及受控FEA可用后，逐项核对组件清单、实际采用、坐标/刚体数值、保存重载、失败恢复与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 2 | STAR配置组件（`EXT-STAR.Components.configure`） | 受阻待定 | 受阻 | 冻结 | 模块启用及受控FEA可用后，逐项核对组件清单、实际采用、坐标/刚体数值、保存重载、失败恢复与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.Components.define。 |
| 3 | STAR组件坐标断点（`EXT-STAR.Components.coordinate_breaks`） | 受阻待定 | 受阻 | 冻结 | 模块启用及受控FEA可用后，逐项核对组件清单、实际采用、坐标/刚体数值、保存重载、失败恢复与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.Components.define。 |
| 4 | STAR坐标变换（`EXT-STAR.CoordinateTransform`） | 受阻待定 | 受阻 | 冻结 | 模块启用及受控FEA可用后，逐项核对组件清单、实际采用、坐标/刚体数值、保存重载、失败恢复与关闭。先用单轴旋转控制确认RotationAngles/RotationValues及旋转顺序。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 5 | STAR刚体变换（`EXT-STAR.RigidBody`） | 受阻待定 | 受阻 | 冻结 | 模块启用及受控FEA可用后，逐项核对组件清单、实际采用、坐标/刚体数值、保存重载、失败恢复与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 |
| 6 | STAR移除组件刚体运动（`EXT-STAR.Components.remove_rbms`） | 受阻待定 | 受阻 | 冻结 | 模块启用及受控FEA可用后，逐项核对组件清单、实际采用、坐标/刚体数值、保存重载、失败恢复与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.Components.define、EXT-STAR.RigidBody。 |
| 7 | STAR FEA检查（`CV-01.STARInspectFEA`） | 受阻待定 | 进行中 | 冻结 | STAR实时模块启用、受控FEA与应用实例可用后，执行对应六专题准备用例；核对设置面、输入归属、有效曲线/网格/散点或图像、数值、保存重载、取消与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；六kind默认入口及独立采集器已实现，当前实例创建超时；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportDeformation。 |
| 8 | STAR对准检查（`CV-01.STARAlignCheck`） | 受阻待定 | 受阻 | 冻结 | STAR实时模块启用、受控FEA与应用实例可用后，执行对应六专题准备用例；核对设置面、输入归属、有效曲线/网格/散点或图像、数值、保存重载、取消与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；六kind默认入口及独立采集器已实现，当前实例创建超时；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.Components.define、EXT-STAR.RigidBody。 |
| 9 | STAR二维形变图（`CV-01.STAR2DDefPlot`） | 受阻待定 | 受阻 | 冻结 | STAR实时模块启用、受控FEA与应用实例可用后，执行对应六专题准备用例；核对设置面、输入归属、有效曲线/网格/散点或图像、数值、保存重载、取消与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；六kind默认入口及独立采集器已实现，当前实例创建超时；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.FitDeformation。 |
| 10 | STAR折射率随温度（`CV-01.STARIndexVsTemp`） | 受阻待定 | 受阻 | 冻结 | STAR实时模块启用、受控FEA与应用实例可用后，执行对应六专题准备用例；核对设置面、输入归属、有效曲线/网格/散点或图像、数值、保存重载、取消与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；六kind默认入口及独立采集器已实现，当前实例创建超时；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.ImportTemperature、EXT-STAR.FitTemperature。 |
| 11 | STAR性能变化（`CV-01.STARPerfChange`） | 受阻待定 | 受阻 | 冻结 | STAR实时模块启用、受控FEA与应用实例可用后，执行对应六专题准备用例；核对设置面、输入归属、有效曲线/网格/散点或图像、数值、保存重载、取消与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；六kind默认入口及独立采集器已实现，当前实例创建超时；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.FitDeformation。 |
| 12 | STAR系统查看器（`CV-01.STARSysViewer`） | 受阻待定 | 受阻 | 冻结 | STAR实时模块启用、受控FEA与应用实例可用后，执行对应六专题准备用例；核对设置面、输入归属、有效曲线/网格/散点或图像、数值、保存重载、取消与关闭。系统查看器另需正式原生图像出口。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；六kind默认入口及独立采集器已实现，当前实例创建超时；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.Components.define。 |
| 13 | STAR删除组件（`EXT-STAR.Components.remove`） | 受阻待定 | 受阻 | 冻结 | 模块启用及受控FEA可用后，逐项核对组件清单、实际采用、坐标/刚体数值、保存重载、失败恢复与关闭。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.Components.define。 |
| 14 | STAR组件管理（`EXT-STAR.Components`） | 受阻待定 | 受阻 | 冻结 | define/configure/coordinate_breaks/remove等子项完成后，验组件完整生命周期、清单不变量、拓扑和恢复，再收口聚合范围。 条件：2026-11-09当前IsSTARModuleEnabled=false，正式读取返回FEATURE_UNAVAILABLE；受控FEA及专项设置、数值和生命周期尚待验收；正式许可依据：2024 R2手册p.1708要求Enterprise级许可；先确认可用许可并读取新实例IsSTARModuleEnabled。 前置：EXT-STAR.Components.define、EXT-STAR.Components.configure、EXT-STAR.Components.coordinate_breaks、EXT-STAR.Components.remove_rbms、EXT-STAR.Components.remove。 |

## D013

HPC配置与分布式任务。先取得可用偏好配置，再完成四类节点作业的完整生命周期与结果回收。

| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |
| ---: | --- | --- | --- | --- | --- |
| 1 | HPC配置读取与采用（`EXT-HPC.Settings`） | 低 | 已实现待验收 | 冻结 | 取得正式非空IHPCSettings后验六项字段、来源和关闭；is_configured=false可作为有效读取。 条件：2026-11-09 preferences及custom(1,Default)均返回null；配置/许可/服务/版本原因尚未区分。四类作业另需节点及各自终态证据。 |
| 2 | HPC非序列追迹（`EXT-HPC.NSCTrace`） | 受阻待定 | 已实现待验收 | 冻结 | Formal query returns a non-null IHPCSettings plus node/license availability AND this item's own job terminal-state evidence (submit/status/cancel/result/close) against the local reference; then run the item-specific native job test. 条件：2026-11-09 preferences及custom(1,Default)均返回null；配置/许可/服务/版本原因尚未区分。四类作业另需节点及各自终态证据。 前置：EXT-HPC.Settings。 |
| 3 | HPC公差任务（`EXT-HPC.Tolerancing`） | 受阻待定 | 已实现待验收 | 冻结 | Formal query returns a non-null IHPCSettings plus node/license availability AND this item's own job terminal-state evidence (submit/status/cancel/result/close) against the local reference; then run the item-specific native job test. 条件：2026-11-09 preferences及custom(1,Default)均返回null；配置/许可/服务/版本原因尚未区分。四类作业另需节点及各自终态证据。 前置：EXT-HPC.Settings。 |
| 4 | HPC全局优化（`EXT-HPC.GlobalOptimization`） | 受阻待定 | 已实现待验收 | 冻结 | Formal query returns a non-null IHPCSettings plus node/license availability AND this item's own job terminal-state evidence (submit/status/cancel/result/close) against the local reference; then run the item-specific native job test. 条件：2026-11-09 preferences及custom(1,Default)均返回null；配置/许可/服务/版本原因尚未区分。四类作业另需节点及各自终态证据。 前置：EXT-HPC.Settings。 |
| 5 | HPC Hammer优化（`EXT-HPC.HammerOptimization`） | 受阻待定 | 已实现待验收 | 冻结 | Formal query returns a non-null IHPCSettings plus node/license availability AND this item's own job terminal-state evidence (submit/status/cancel/result/close) against the local reference; then run the item-specific native job test. 条件：2026-11-09 preferences及custom(1,Default)均返回null；配置/许可/服务/版本原因尚未区分。四类作业另需节点及各自终态证据。 前置：EXT-HPC.Settings。 |

## 工作包收口

另有24个未完成工作包汇总；随相关D00x子项完成后核对，采用原有证据要求和状态。

| 工作包 | 状态 | 当前原生范围与收口动作 |
| --- | --- | --- |
| `BASE-02` | 已实现待验收 | 按本条声明范围确认正式设置、输入身份和结果出口，再完成定向原生及关闭验收。新增条目可调用；既有入口可用；共用调整有相关回归 |
| `BASE-04` | 进行中 | Standalone已恢复，按D00x继续定向原生；FRU警告和既有任务历史写入问题分别诊断。 条件：当前连接和关闭通过，专项条件按子项。 |
| `BASE-05` | 已实现待验收 | 发行0.1.62沿用历史证据；D001—D013本轮96项已审查，首次完整验收3/10。累计十项后检查并构建/独立安装/stdio验收0.1.63。 |
| `ED-01` | 已实现待验收 | 内建属性证据沿用；散射资源过滤/精确名修复已合入。补BSDF正式文件选择、匹配ISX输入、追迹和重载；User诊断保留历史归属。 条件：BSDF文件选择未采用；ISScatterCatalog缺匹配ISX输入。Floating清除已完成。 |
| `ED-02` | 已实现待验收 | 材料八组和两种拾取已执行，取得新依据后继续Nd/Vd及实际拾取采用/联动。 条件：材料Nd/Vd超限，两种拾取未实际采用。 |
| `ED-03` | 已实现待验收 | 核对原生编辑器行操作、元数据、MFE/TDE文件及整系统保存重载证据，完成工作包收口。 |
| `ED-04` | 已实现待验收 | FindBestAsphere原证据沿用；RayAiming须取得可靠执行、取消终态与关闭，再验preview/Apply及保存重载。 条件：RayAiming recorded timeouts remain under diagnosis. |
| `IM-01` | 进行中 | GBM/RGB适配及stdio通过，继续独立成像、归一化和生命周期；ImageSimulation出口缺口保留。 条件：位图设置/结果出口已有；独立数值和生命周期待验。 |
| `PO-01` | 进行中 | 四默认报告及N1/N2/N3有界探针已合入；从PhaseAberration正式选择/相位参考继续，再验偏振光线、透射与光纤专题独立参考。 条件：其余四项无专属设置 getter；分别探查正式 CFG 键、加载采用和结果契约。 |
| `CO-01` | 进行中 | 三项原生Hologram1已完成，包内原生子项均已done；复核既有膜层/薄膜证据及包级优化衔接声明后完成工作包收口。 条件：原生子项已完成；工作包总声明的证据收口待审。 |
| `MA-01` | 进行中 | GlassMap身份346/346已匹配，消热差359/364参考通过；补5项材料数据、色散导数定义和专题选择。继续Gradium10/11阶、左端capping及波长归属。 条件：Remaining per-item runtime settings and controlled references need execution. |
| `NS-01` | 已实现待验收 | 保留纯NSC转换历史379项参考和光线误差；取得混合组可执行正式路径后验设置、光线、保存重载、取消恢复和关闭。 |
| `NS-02` | 进行中 | 已完成关键/单光线、ZRD读取及NSC几何MTF沿用；继续PathAnalysis阈值筛除后未分类功率的正式出口/定义及聚合证据。 |
| `NS-03` | 进行中 | 已完NSC几何MTF沿用；本轮光源/光谱/照明/散射专题逐项审计完成。补正式输入、有效出口、角度/单位及数值和生命周期。 |
| `NS-04` | 进行中 | 处方导出章节选择、分页/失败复用/重载已验；继续原生章节与面号选择，以及图纸/对象查看器有效出口。 条件：默认文本可用；正式选择及图形出口待取得。 |
| `WP-01` | 进行中 | 既有高斯束/POP与文件读取证据沿用；光纤默认报告已合入。补光纤专题正式设置/复场参考及BeamFileViewer正式选择、显示和关闭。 |
| `TO-01` | 进行中 | QuickYield574已验收；继续本工作包剩余公差/补偿专题的正式输入、结果与状态条件。原生近似的高阶精度范围见acceptance574-reference.json。 |
| `MF-01` | 进行中 | TestPlate目录选择；SagTable面型拟合差异、制造偏移与反向摘要；图纸有效出口。 条件：目录选择及图纸出口仍缺；Zernike半径差3.8385445e-5mm>5e-6mm。 |
| `CV-01` | 进行中 | 本轮图表/矩阵/全视场、FFT与STAR专题均已逐项审查；FFT留存复瞳复算仍超0.005。依各条正式出口、坐标定义、许可与独立参考恢复验收。 |
| `CV-02` | 进行中 | Power Map控制及图像内部合同已交付；继续零EFL/内部采样环、LightSource/EXD/PCI输入身份和独立数值参考，Gradium别名同步MA-01。 |
| `RL-01` | 进行中 | 历史六工作流证据沿用；本轮D001—D013审查已完成，按剩余93组实际状态和每十项检查节奏安排下一轮及包级收口。 |
| `EXT-STAR` | 受阻 | 模块启用后验证受控FEA、材料、拟合、组件、坐标和专题全生命周期。 条件：2026-11-09 IsSTARModuleEnabled=false，读取FEATURE_UNAVAILABLE；各专项参考缺口保留。 |
| `EXT-HPC` | 已实现待验收 | 取得正式非空IHPCSettings后验实际配置；节点条件满足后分别验四类作业。 条件：2026-11-09 preferences/custom均null，底层原因未区分。 |
| `EXT-EXPORT` | 已实现待验收 | 取得ASAT/ASAB、显式版本、配置层采用或线框/ZBB/ZEC正式创建路径后续验。 条件：2026-11-09 ASAT/ASAB拒绝、V30实际500、IGES四组合65535；创建工厂未找到。 |

来源：[操作台账](ledgers/operations.csv)、[分析台账](ledgers/analyses.csv)、[工作包台账](ledgers/packages.csv)。原生归属见[产品能力分类](remaining-origin-classification.md)，范围变更见[历史索引](archive/scope-native-only-20261108/index.json)。

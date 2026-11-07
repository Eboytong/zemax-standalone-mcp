# 分析、工况与专项工具

本机 Windows、OpticStudio 2024 R2。以下 JSON 是 MCP 工具参数；以 `request` 包装的接口保留该层。先连接并加载或新建相应模式的系统。计算接口返回任务编号，等待终止后读取结果。

## 文件与项目

| 工具 | 请求及行为 |
| --- | --- |
| copy_system | `{"request":{"path":"绝对路径.zos"}}`，保存独立副本，保留当前设计 |
| create_archive | `{"request":{"path":"绝对路径.zar","compression":true}}`，返回归档任务 |
| load_archive | `{"request":{"path":"归档绝对路径.zar","output_directory":"尚不存在的绝对目录"}}`，加载到该目录并保留项目依赖位置 |
| get_project_settings | 无参数；读取项目状态及当前设计路径 |
| update_project_settings | `{"request":{"operation":"convert","directory":"新项目绝对目录"}}`；关闭项目模式使用 `operation=disable` 并省略目录 |
| get_external_dependencies | `{"request":{"start":0,"count":200}}`，返回原生引用、候选位置及 found/unresolved |
| load_merit_function | `{"request":{"path":"绝对路径.mf"}}`，检查点后替换当前评价函数 |
| save_merit_function | `{"request":{"path":"绝对路径.mf"}}`，保存原生评价函数 |

另存及归档默认禁止覆盖，显式 `overwrite=true` 才允许替换输出。归档解包目录必须是新目录。归档恢复任务开始时清空当前探测器追迹历史并标记为未知；恢复后须明确清空并重新追迹，才能建立当前模型的完整来源记录。项目设置作用于当前设计。依赖查询依据原生文件管理器和文件可访问性；unresolved 表示候选位置尚未解析成功。

## 统一成像分析

调用 `run_analysis`：

```json
{"request":{"kind":"huygens_mtf","field":1,"wavelength":1,"sampling":"S_64x64","image_sampling":"S_64x64","maximum_frequency":50,"use_polarization":false}}
```

| kind | 主要设置 |
| --- | --- |
| huygens_mtf、geometric_mtf | sampling、maximum_frequency、use_polarization；Huygens 另有 image_sampling/image_delta；几何 MTF 可 multiply_by_diffraction_limit |
| fft_through_focus_mtf、huygens_through_focus_mtf、geometric_through_focus_mtf | sampling、frequency、delta_focus、number_of_steps；几何模式另有 multiply_by_diffraction_limit |
| fft_psf、fft_psf_cross、huygens_psf、huygens_psf_cross | sampling、normalize、use_polarization；适用模式另有 image_sampling/image_delta |
| diffraction_encircled_energy、geometric_encircled_energy | sampling、reference、maximum_radius；几何模式另有 multiply_by_diffraction_limit |
| wavefront | sampling、remove_tilt、use_exit_pupil |
| zernike_standard、zernike_fringe、zernike_annular | sampling、maximum_terms；Standard/Annular 可 obscuration；Fringe 最多 37 项 |
| ray_fan、opd_fan | number_of_rays、check_apertures、vignetted_pupil |
| field_curvature_distortion | wavelength、ignore_vignette |
| longitudinal_aberration、lateral_color、focal_shift | 原生色差分析；实际设置随任务返回 |
| surface_sag、surface_curvature、surface_phase | surface、sampling（S_33x33 等奇数网格） |
| surface_sag_cross、surface_curvature_cross、surface_phase_cross | surface、sampling、angle |

离焦 MTF 的 number_of_steps 是实际计算焦平面数。原生曲线可返回由这些焦平面插值的 101 个平滑样本（手册 §3.2.5.12），不能把曲线行数解释为独立计算次数。

各类型的参数由 MCP 输入模型区分。默认单视场/单波长分析使用编号 1；支持全选的参数可用 0，原生选择回读不一致时拒绝。成像分析适配有焦顺序系统，Huygens 分析使用当前单个配置。

结果包含实际原生设置、系列或网格、原生消息和 UTF-16 文本文件。`native_preamble` 保留原文中的单位、参考坐标、采样和说明。未适配的文本格式保持原文。非有限网格和曲线值返回 null 与 invalid_count，不能视为零。

几何离焦 MTF 和几何圈入能量的 `multiply_by_diffraction_limit` 缺省为开启；显式 false 得到纯几何响应。后者对应本机原生字段 ShowDiffractionLimit，实际效果为乘以圆瞳衍射近似；该近似的适用条件见手册 §3.2.7.2。常规 geometric_mtf 的同名选项缺省为 false，结果中的 requested/native 同时保留实际选择。垂轴色差输出可能包括 Airy 正负半径参考线，应按系列标签选择色差指标。

PSF 截面在本机连续三列文本格式下转换为系列，位置单位 μm、纵轴为相对辐照度；精度受原生文本位数限制。无法识别的格式保留原生文本。

Zernike 的 rows 来自本机已核对的 `Z 编号—系数` 文本格式，单位 waves，精度受原生文本限制。格式不识别时返回空系数表及原文位置。比较 ZERN 操作数时须统一拟合项数；本机 Fringe 操作数按 37 项拟合，不能直接与较少项数的拟合结果等同。

`get_task_result` 默认只返回网格摘要。区域读取示例：

```json
{"task_id":"任务编号","grid":0,"x_start":0,"y_start":0,"width":32,"height":32}
```

返回 next_x/next_y。完整矩阵位于任务 JSON；逐行表默认 200 行，最多 1000 行。曲线超过内联规模限制时从完整 JSON/CSV 读取。矩阵保持原生顺序；已核对的曲面网格按 `values[y][x]` 解释。不同结果的空白区域和物理孔径须结合原生说明使用。

## 追迹模式

`run_batch_ray_trace` 保留归一化非偏振用法。直接追迹示例：

```json
{"request":{"input_mode":"Direct","start_surface":1,"target_surface":2,"ray_type":"Real","rays":[{"x":0,"y":0,"z":0,"l":0,"m":0,"n":1,"wavelength":1}],"polarization":{"jx":1,"jy":0,"x_phase":0,"y_phase":0}}}
```

输入方向必须归一化。直接输入采用起始面的局部坐标，输出交点和方向采用目标面局部坐标。长度为镜头单位，偏振相位为度。

| 模式 | 渐晕 | OPD | 电场/强度 |
| --- | --- | --- | --- |
| NormUnpol，Real/Paraxial | 原生渐晕码 | Real 至像面、显式开启，CurrentAndChief | 非偏振强度不含完整损耗 |
| DirectUnpol，Real/Paraxial | 原生渐晕码 | 不开放 | 非偏振强度 |
| NormPol，Real | 接口不提供，返回 null | 不开放 | 复电场及偏振强度 |
| DirectPol，Real | 原生渐晕码 | 不开放 | 复电场及偏振强度 |

各结果的 summary 说明可用字段及损耗范围；null 渐晕状态表示接口未提供，不能解释为未渐晕。单次最多 10000 条，分块大小最多 1024。

## 多结构与优化

`get_configurations` 以 `request.start/count` 分页读取 MCE，返回参数、各配置值、求解关系及可用 solve。`set_configuration(configuration)` 切换并更新系统。

```json
{"request":{"actions":[{"action":"add","copy_current":true}],"operands":[{"type":"THIC","parameters":{"1":1},"cells":[{"configuration":1,"value":3},{"configuration":2,"value":4}]}]}}
```

以上用于 `update_configurations`。actions 支持 add/insert/delete；指定 operand 修改现有行，省略时追加。parameters 使用原生编号 1–3。cells 可指定 fixed、variable、config_pickup、thermal_pickup。拾取要指定来源，替换现有关系需 replace_solve；同批最终关系禁止循环。结构增删或删除操作数与设置拾取分开调用，使用编辑后回读的编号。

TEMP、PRES 使用本机原生操作数。热工况应启用 `adjust_index_to_environment`，核对实际温压、材料热数据、机械口径和热拾取。曲面 `tce` 使用原生 TCE × 1E-6 列的数值；例如 100 表示 100 ppm/°C。玻璃 TCE 与空气间隔安装材料 TCE 的适用规则不同，不能把所有 THIC 都按中心厚度线性缩放。

`get_constraint_coverage` 返回 CONF 分段对应的操作数及配置，供审查约束作用域。是否为约束、是否满足目标仍须依据操作数定义和计算值判断。

```json
{"request":{"configurations":[1,2],"evaluation":{"spot":{"reference":"ChiefRay"},"merit":true}}}
```

以上用于 `run_configuration_evaluation`。逐配置从同一基线执行评估，结束或取消后恢复原配置与设计；逐配置重新对焦通过 evaluation.focus 明确指定。

`run_global_optimization` 和 `run_hammer_optimization` 接收 `{"request":{"runtime_seconds":10,"number_of_cores":1}}`。必须已有变量和正权重评价函数。预算到期后等待原生安全停止，保存候选设计，并独立执行 ChiefRay 光斑、64×64 FFT MTF（25/50 频率）及评价函数验证。取消结果保存当时候选和起始检查点，并标记独立验证未完成。优化保留当前设计，不自动恢复基线。

`run_multistart_optimization` 接收显式 starts（SurfacePatch 列表的列表）、optimization（有限循环局部优化）和 evaluation。每个起点从同一基线开始，按最终保存设计的评价函数选择最佳；取消恢复基线。完成状态仍需检查逐起点失败项及 retained_best。

变量接口同时支持曲面、MCE 和非序列单元格。MCE 使用 operand/configuration；非序列使用 `object/cell`，cell 采用 get_nsc_objects 返回的 available_columns，例如 ZPosition、Par1。

## 公差

`get_tolerances` 分页读取 TDE。`update_tolerances` 的 mode 为 replace/append，operands 包含 type、param1..3、minimum、maximum、comment、ignore、inverse_protected。COMP/CPAR 等补偿器也通过该接口定义。

```json
{"request":{"mode":"replace","operands":[{"type":"SEED","param1":42},{"type":"TTHI","param1":1,"param2":2,"minimum":-0.01,"maximum":0.01}]}}
```

`generate_tolerances` 按明确的表面/元件误差幅度运行向导，未选择的误差类型关闭。`run_tolerance_analysis` 支持 sensitivity、inverse_limit、inverse_increment、monte_carlo；逆灵敏度需 allow_tolerance_update=true。参数含 criterion、compensation、sampling、cycles、configuration、frequency、maximum_criterion、samples、save_samples、distribution。

结果保存原始 TDE、STAT 逐段分布、补偿器定义和范围、实际工具设置、原生摘要、灵敏度及样本准则列。SEED 通过 TDE 指定，ITolerancing 没有独立种子 setter。STAT 分布代码 0/1/2/3 对应 Normal/Uniform/Parabolic/UserDefined，后续行直到下个 STAT；Normal 的端点标准差倍数上限为 10。

`summarize_tolerance_results` 从已有任务按 criterion_column、unit、threshold 和 pass_when 统计。分母为请求样本数，非有限行和未返回样本分开列出。准则列必须是原生 criterion，不能用公差操作数列。原生可追迹数少于有限准则行、又不能确定失败行时拒绝生成合格率，保留原文供审查。

本机可从保留数据读取结果；原生请求的 .ZTD/文本路径不总会生成对应文件，结果中的存在标记和 saved_summary 是实际输出依据。补偿器生效方式由 compensation 决定；None 会忽略补偿器。

## 非序列、探测器与 ZRD

`new_system(mode="NonSequential")` 创建纯非序列系统。对象插入逐项确认原生返回对象和对象总数；失败时停止后续插入，错误详情包含已确认 inserted、当前 total、observed_change 和失败位置 failed_at。对象编号从 1 开始；get/insert/update/delete/copy_nsc_objects 使用 request 包装。对象类型及文件从本机列表选择。类型参数 data、sources、type_settings 和 diffraction 使用返回的原生标量字段名。

顺序系统内的混合组件通过 `request.nsc_surface` 选择；上述五个对象入口可读取和编辑该组对象，操作后恢复编辑器原活动组。对象编号与参考关系属于所选组，组入口坐标、恢复保护及请求示例见[混合模式对象组](nonsequential-validation.md#混合模式的对象组)。

faces 按原生零起始面号设置 coating、scatter_model、settings、number_of_rays；volume 设置原生体物理模型和标量参数；spectrum 设置 SourceColorMode 和参数。只读或未知字段拒绝，不执行任意代码。DLLDefinedScattering 的 volume.parameters 使用零基参数编号，写入检查原生返回及回读；其他数组和复杂模型按明确适配范围使用。

```json
{"request":{"changes":[{"object":1,"object_type":"SourceRay","data":{"NumberOfAnalysisRays":10,"ZCosine":1}},{"object":2,"object_type":"DetectorRectangle","z":10,"data":{"NumberXPixels":8,"NumberYPixels":8}}]}}
```

`run_nsc_ray_trace` 默认 detector_policy=clear，累积必须用 accumulate。split_rays 需要 use_polarization=true。可设置 scatter_rays、ignore_errors、number_of_cores、random_seed、save_zrd、filter。追迹结果记录完成状态及接口提供的总能量、错误与阈值终止数据；不能由这些字段推断全部损失类别。

`clear_detectors(detector=0)` 清空全部，正编号按对象编号清空指定探测器。`get_detector_data` 对 DetectorRectangle 支持 flux/irradiance/intensity/coherent，对 DetectorPolar 支持 flux/intensity；区域最多100×100，相干结果须指定 coherent_type。Polar 行为方位角、列为极角，返回角度中心、边界和立体角；按 value_unit/value_unit_prefix 解释数值。各探测器分别记录清空、累积、修订、配置、追迹选项和历史任务状态；跨修订、混合选项、失败/取消贡献或未知来源的数据不标为完整独立结果。累计功率报告保存这些历史条件并收集相关已结束任务。坐标、相干归一化及示例见[非序列数值条件](nonsequential-validation.md)。

`read_zrd` 接收 path、filter、start_ray、start_segment、max_segments，返回逐分段表和 summary.next_read。光线/分段位置从 0 开始，分块最多 100000 段。

过滤字符串执行前回读；summary.actual_filter与filter_scope说明实际设置和整条路径选择语义。X_WAVERANGE采用微米及闭区间，非转换光线已有边界和分页依据；记录的sample_3荧光ZRD细分仍有原生差异，wavelength_filter_validation明确该限制。源头WlUM不能代替转换后波长。详见[原生波长区间过滤](nonsequential-validation.md#原生波长区间过滤)。

`run_zrd_replay` 通过 Detector Viewer 读取受控的工作副本，指定 path、detector、filter、data_type；显示结果与当前探测器累积分别保存。保存过滤、读取过滤和回放过滤是三个独立设置。回放数据依赖与原始追迹一致的对象和探测器定义。

回放同时返回native_replay_summary，提供原生文本明确标注的总功率、显示精度和可取得的撞击数；单位或格式无法确认时返回不可提取原因，原始文本与网格保留。DataType的同值枚举别名按值核对，调用名称保存在settings.requested_data_type。详见[回放功率与追迹完整状态](nonsequential-validation.md#回放功率与追迹完整状态)。

## POP、光束与耦合

```json
{"request":{"start_surface":1,"end_surface":2,"field":1,"wavelength":1,"beam_type":"GaussianWaist","beam_parameters":{"0":0.1,"1":0.1},"x_sampling":"S_256x256","y_sampling":"S_256x256","x_width":2,"y_width":2,"fiber_type":"GaussianWaist","fiber_parameters":{"0":0.1,"1":0.1}}}
```

以上用于 run_pop。光束和接收模式参数从 0 开始，结果列出每个原生参数的名称和值。起始位置在起始面前、终止位置在终止面后；surface_to_beam 为接收光束平面的轴向偏移。结果平面沿主光线法向，长度按系统单位解释。

默认返回 Irradiance，可选择 Phase 和 EX/EY 对应数据；偏振、X/Y 采样和窗口独立指定。save_output_beam 默认 true，save_all_surfaces=true 时同时保留原生中间面文件。compute coupling 由 fiber_type 指定；分别返回 receiver_efficiency、system_efficiency、total_coupling_efficiency，不能把未计算时的文件零值当作真实零效率。

`get_beam_file` 解析version-1二进制及A文本.ZBF，返回元数据和分页复电场，按格式定义保留X索引最快的样本排列；其他版本明确拒绝。光束坐标、探测器文件、Color/Volume/Surface数据、波前映射及单项图片的约定见数据与输出（历史参考）。

`run_pop_convergence` 使用 settings、widths、samplings 或 sampling_pairs、metric、absolute_tolerance、relative_tolerance。采样两种写法互斥；最后一个采样/窗口组合为显式参考。容差由请求指定，结果不给通用的合格阈值。

## CAD 与报告

`run_cad_export` 接收 path、format、start/end、surfaces_as_solids、export_dummy_surfaces、number_of_rays、field/wavelength、tolerance。顺序模式选择曲面，非序列选择对象。VisualizationJSON 输出原生三角网格，非序列一次选择一个对象，结果独立保存坐标、法线及表面/对象索引。

`run_layout_export` 导出原生 PNG，使用以下参数：

```json
{"request":{"kind":"cross_section","path":"C:/绝对输出目录/layout.png","width":1200,"height":800,"start":1,"number_of_rays":5,"field":0,"wavelength":0}}
```

顺序类型为 cross_section、viewer_3d、shaded_model；非序列类型为 nsc_3d、nsc_shaded。顺序 end 缺省到像面，field/wavelength=0 表示全选；非序列使用对象的布局光线数量，不接受顺序范围和光线选择。3D 类型可选 viewpoint=Isometric/XY/YZ/XZ；截面采用原生 YZ 视图。输出像素边长为 64–4096，默认禁止覆盖。任务返回实际原生设置及 native_image 文件；报告可直接引用这些已保存图片。

`get_capabilities` 区分 DLL 格式枚举、本机真实调用状态和逐次许可检查。本机测试被原生拒绝的格式保留 Unsupported export format，不按枚举存在判定可运行。

```json
{"task_ids":["任务编号"],"title":"设计评估","include_charts":true,"formats":["markdown","pdf"],"background":true}
```

以上用于 export_evaluation_report。报告读取已保存任务及关联分析，输出 Markdown、完整 JSON、逐行/曲线/网格 CSV、图表和 PDF。PDF 和图表建议 background=true，复用任务查询与取消。最多关联 1000 个任务，超出时缩小结果集合。PDF 每任务预览前 200 行，显示总行数、展示行数、省略行数及完整 JSON/CSV 位置；逐行内容保留 values 和其他字段。PDF artifact 的 row_previews 返回相同的截断元数据，values 的列定义取自 summary.columns。报告生成不调用 Zemax。

图表/PDF 使用项目 reports 可选依赖；PDF 渲染测试使用 report-test。完整参数类型和本机选项由 MCP tools/list 与 get_capabilities 返回。当前证据及验收条件见 [能力与验收](capabilities.md)。

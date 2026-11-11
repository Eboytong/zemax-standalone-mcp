# MCP 工具清单

默认full模式直接注册107工具。compact模式注册11入口，包含9个连接/发现/任务控制工具和以下两个调用入口；各原生操作通过相同能力ID和参数合同执行。

| compact入口 | 用途 |
| --- | --- |
| `query_capability` | 按能力ID调用已审查的读取操作，arguments使用详情的MCP参数形状。 |
| `execute_capability` | 按能力ID调用建模、分析、保存和工程流程，保留原响应及任务编号。 |

详细用法见[能力发现](../guides/capability-search.md)，compact的11入口合同见[compact schema](compact-tool-schemas.json)。

1.4.0 提供107个工具、146种分析请求。支持Detector Viewer、制造几何评价、光纤对准、固定膜系优化、NSC效率/均匀性、玻璃贡献/替换、扫描瞳共轭、鬼像路径、共焦响应、热补偿、公差成本预算及双FSM离线控制。完整参数见[请求模型](tool-schemas.json)，调用约定见[使用指南](../guides/usage.md)，设置与数值条件见[原生分析矩阵](native-analysis-matrix.csv)及对应专题。

| 工具 | 用途 |
| --- | --- |
| `search_capabilities` | 按中文工程需求搜索工具与分析，离线读取条件、单位和schema入口。 |
| `manage_candidates` | 保存受保护基线、分支、检查点、选择、恢复和冻结条件比较。 |
| `run_candidate_evaluation` | 按同一评价合同串行重载候选，返回指标并恢复活动模型。 |
| `get_glass_slots` | 读取顺序系统可替换材料段、目录身份及跳过原因。 |
| `run_merit_program` | 预览或应用原生向导、OPD目标及几何约束，回读逐项贡献。 |
| `cancel_task` | 请求原生工具取消，继续查询状态确认；已完成任务保持其完成状态。 |
| `clear_detectors` | 清空指定探测器，detector=0 清空全部。 |
| `compare_results` | 比较成功的评估结果；分析条件不一致时返回差异，不计算改善结论。 |
| `connect` | 创建或复用本服务的后台实例，检查许可；默认使用本机已安装的 2024 R2。 |
| `copy_editor_rows` | 在同一MFE/MCE/TDE内复制连续行；引用重编号由原生编辑器处理。 |
| `copy_nsc_objects` | 原生复制非序列对象，复制后回读参考关系。 |
| `copy_surfaces` | 在物面与像面之间原生复制曲面，保留原物理光阑。 |
| `copy_system` | 创建并保存独立系统副本，释放副本，保留当前活动设计。 |
| `create_archive` | 启动 Zemax ZAR 归档创建任务；默认禁止覆盖。 |
| `delete_nsc_objects` | 删除指定非序列对象范围，保留检查点。 |
| `delete_surfaces` | 删除物面和像面之间的指定曲面；操作前保存检查点。 |
| `disconnect` | 保存检查点并关闭本服务创建的后台实例；有运行任务时先完成或取消。 |
| `evaluate_merit_function` | 计算当前评价函数并返回操作数结果；权重目标须结合独立像质分析解释。 |
| `export_analysis_image` | 从已保存结果绘图或导出已有原生图片，不重新计算 Zemax。 |
| `export_evaluation_report` | 以已取得的结果输出 Markdown、JSON 和 CSV；不会重新执行 Zemax。 |
| `export_point_cloud` | 在自有系统副本上导出曲面PCD，保留原生消息、文件头及关闭记录。 |
| `generate_tolerances` | 按显式幅度运行顺序公差向导，未选择的误差类型关闭。 |
| `get_coating_rta` | 指定顺序曲面、角度、波长和传播方向，直接读取原生S/P镀膜R/T/A。 |
| `get_beam_file` | 读取 version-1 二进制 ZBF 元数据和文件顺序复场样本。 |
| `get_capabilities` | 列出已实现工具、模式、面型及当前版本可用的设置枚举。 |
| `get_coating_layers` | 读取当前顺序曲面的镀膜层乘数、偏移、状态及拾取源。 |
| `get_configurations` | 分页读取 MCE 操作数、配置值和求解关系。 |
| `get_constraint_coverage` | 读取 CONF 分段下的评价函数配置作用域。 |
| `get_design_tool_options` | 读取设计工具原生默认设置和枚举，关闭工具并返回结果。 |
| `get_detector_data` | 读取矩形探测器指定数据类型及区域，完整矩阵保存为 JSON。 |
| `get_editor_metadata` | 读取MFE/MCE/TDE行类型、列标题、数据类型和活动状态；列分页从0开始。 |
| `get_external_dependencies` | 分页读取原生文件管理器列出的设计依赖及可解析位置。 |
| `get_historical_result` | 读取指定会话已落盘结果；支持行、曲线及网格区域分页。 |
| `get_hpc_settings` | 读取偏好或自定义HPC设置的实际节点、规格和配置状态。 |
| `get_lens_catalogs` | 读取本机原生镜头厂商目录和当前搜索设置，随后关闭工具。 |
| `get_material_properties` | 读取原生材料目录系数、热属性及内部透过率表，结束关闭目录工具。 |
| `get_merit_function` | 分页读取评价函数及操作数字段；编号从 1 开始，value 为上次计算值。 |
| `get_nsc_object_geometry` | 分页读取原生对象面顶点/法线；借用游标与坐标设置在退出时恢复。 |
| `get_nsc_objects` | 读取对象及原生参数；混合模式须指定nsc_surface，编号与坐标属于该NSC组。 |
| `get_optimization_wizard_options` | 读取原生向导设置、枚举及资源选项。 |
| `get_project_settings` | 读取当前设计的项目目录状态和位置。 |
| `get_request_status` | 按请求编号读取执行回执，区分请求已返回及原生任务状态。 |
| `get_star_data` | 读取当前顺序曲面的STAR状态、拟合设置及分页FEA点。 |
| `get_status` | 读取连接、模型修订与当前任务状态；任务超时不能视为原生计算停止。 |
| `get_surface_geometry` | 读取局部点 Sag 与全局变换；长度为镜头单位。 |
| `get_surfaces` | 分页读取曲面、参数和 solve/pickup；曲面从 0（物面）开始，count=1..200。 |
| `get_system_resources` | 分页查询本机材料目录、材料、镀膜和相关文件。 |
| `get_system_settings` | 读取实际系统设置；波长单位始终是当前环境空气参考下的 μm。 |
| `get_system_summary` | 读取单位、视场、波长、环境、结构编号与一阶光学数据。 |
| `get_task_result` | 读取已结束任务的数据、实际设置、模型版本及输出文件。 |
| `get_task_status` | 读取任务实际状态与可取消能力；取消中不代表已经停止。 |
| `get_tolerances` | 分页读取 TDE 公差、补偿器及 STAT 定义。 |
| `get_variables` | 列出顺序系统当前曲面优化变量及其数值。 |
| `insert_editor_rows` | 在MFE/MCE/TDE指定1基位置插入行，返回实际类型与读取结果。 |
| `insert_nsc_objects` | 在指定编号前插入非序列空对象。 |
| `insert_surfaces` | 在指定曲面前插入标准面，at 从 1 开始且不超过像面编号。 |
| `list_task_history` | 发现当前及磁盘历史任务，按会话、请求、种类与状态筛选分页。 |
| `load_archive` | 解包 ZAR 到新目录并加载设计，返回任务编号。 |
| `load_detector_data` | 替换或累积加载原生探测器数据；外部数据的追迹来源标记为未知。 |
| `load_merit_function` | 保存检查点后从绝对路径加载 .MF 评价函数。 |
| `load_tolerance_file` | 载入原生.tol公差文件，创建检查点并读取实际公差表。 |
| `new_system` | 保存当前检查点并新建顺序系统，建立项目输出目录中的工作副本。 |
| `open_lens` | 读取 .zos/.zmx 并建立工作副本；path 使用绝对路径，输入文件保持只读。 |
| `read_zrd` | 按光线/分段位置分块读取 ZRD，返回原生路径与后续读取位置。 |
| `run_analysis` | 执行本机适配的顺序成像/像差/曲面分析，返回任务；实际设置和曲线、网格或原生文本随结果保存。 |
| `run_batch_evaluation` | 按文件顺序运行同一评估，逐项记录失败，结束后恢复原设计。 |
| `run_batch_ray_trace` | 归一化或直接坐标批量追迹，可显式偏振，最多 10000 条；结果说明各模式可用字段和坐标。 |
| `run_cad_export` | 按本机原生格式导出指定顺序曲面或非序列对象，返回任务。 |
| `run_catalog_evaluation` | 从独立基线比较目录镜头/材料候选，复用评价并在结束时恢复基线。 |
| `run_catalog_lens` | 按厂商及唯一名称加载或插入原生目录镜头，创建恢复检查点。 |
| `run_configuration_evaluation` | 逐结构执行指定评估，每项从同一基线开始，结束恢复原设计与配置。 |
| `run_design_tool` | 执行缩放、Quick Adjust及非球面工具；建立检查点并返回任务。 |
| `run_fft_mtf` | 启动有焦 FFT MTF，返回任务编号。field/wavelength=0 为全部/多色；频率单位须与系统一致，结果附轴与曲线标签。 |
| `run_global_optimization` | 按显式有限时间预算运行原生全局优化。 |
| `run_hammer_optimization` | 按显式有限时间预算运行原生 Hammer 优化。 |
| `run_layout_export` | 导出本机原生顺序/非序列布局图片，保存实际设置并返回任务。 |
| `run_lens_catalog_search` | 按厂商、毫米EFL/EPD、形状及类型搜索镜头，返回可分页任务。 |
| `run_local_optimization` | 使用当前变量和评价函数运行原生局部优化，返回可查询的任务编号。 |
| `run_multistart_optimization` | 从显式起点集合独立局部优化并评估；完成保留最佳，取消恢复基线。 |
| `run_nsc_conversion` | 在工作模型中将顺序曲面组转换为混合模式或纯NSC，保留恢复检查点。 |
| `run_nsc_ray_trace` | 执行非序列追迹；默认清空，累积须显式指定，可保存 ZRD。 |
| `run_optimization_wizard` | 配置顺序/非序列优化向导，apply开启后生成评价函数，返回任务。 |
| `run_parameter_scan` | 单参数独立扫描，每点从基线开始；默认固定像面，完成或取消后恢复设计。 |
| `run_pop` | 运行物理光学传播，保存实际采样、窗口、光束/模式与结果网格。 |
| `run_pop_convergence` | 按显式采样、窗口和容差比较 POP 指标，最后一个组合为参考。 |
| `run_quick_focus` | 按显式 RMS 准则调整像面前一面的厚度；返回任务编号，其最佳焦点不等于最高 MTF。 |
| `run_speos_export` | 在独立系统副本中导出Speos LensSystem或Whitebox，返回任务与原生文件。 |
| `run_spot_analysis` | 启动原生标准点列图，返回任务编号；显式指定参考点，保留采样、权重条件、RMS/GEO 和原生文本。 |
| `run_star_operation` | 在检查点保护下导入、拟合或卸载STAR变形、温度或直接折射率数据，并执行组件及坐标控制。 |
| `run_tolerance_analysis` | 运行灵敏度、逆灵敏度或蒙特卡罗，记录补偿和分布，结束恢复原设计。 |
| `run_zrd_replay` | 用 Detector Viewer 回放 ZRD，结果与当前探测器累积数据分开保存。 |
| `save_detector_data` | 保存当前探测器的原生数据文件，默认禁止覆盖。 |
| `save_lens_as` | 保存设计副本到绝对路径；覆盖现有文件须显式设置 overwrite。 |
| `save_merit_function` | 将原生评价函数另存为 .MF；默认禁止覆盖。 |
| `save_tolerance_file` | 保存原生.tol公差文件，路径为绝对路径。 |
| `set_configuration` | 切换活动配置并读取实际系统设置。 |
| `set_variables` | 按曲面和 cell 设置或固定变量；替换已有 solve/pickup 需显式允许。 |
| `summarize_tolerance_results` | 从已有公差结果按显式准则列、单位及阈值计算分位数和通过比例。 |
| `update_coating_layers` | 修改镀膜层并检查最终状态，保留检查点及部分失败详情。 |
| `update_configurations` | 编辑配置及 MCE 操作数，已有求解关系受保护。 |
| `update_merit_function` | 替换/追加评价函数、按行 update/delete，或生成 RMS spot 向导。updates 按 operand 编号修改；删除用 operand_numbers。parameters 是原生列号2..9，先按header和data_type核对；曲面范围列必须为整数，MNEG/MNCT等边界阈值写target，不写面号列。多配置replace须以显式CONF行开头，CONF仅指定parameters并省略target/weight。最终回读拒绝静默改写；失败含部分修改明细时先回读，勿盲目重复追加。 |
| `update_nsc_objects` | 编辑对象类型、位置、材料及 get_nsc_objects 返回的原生标量参数。 |
| `update_project_settings` | 将当前设计转为项目目录或关闭项目模式，不修改全局偏好。 |
| `update_surfaces` | 批量修改曲面，几何值使用当前镜头单位；solve/pickup 默认受保护，Infinity 表示无限半径。 |
| `update_system_settings` | 修改系统设置并回读；只传需修改字段。fields/wavelengths 替换整组，550 nm 使用 wavelength_um=0.55。 |
| `update_tolerances` | 替换、追加、插入、逐行修改或删除TDE操作数，操作前保存检查点。 |

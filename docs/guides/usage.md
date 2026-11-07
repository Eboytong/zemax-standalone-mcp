# 调用、状态与故障处理

## 响应与编号

工具响应包含ok、data、error、warnings、context、artifacts。先检查ok；参数类型错误也可能由MCP SDK直接返回工具错误。长任务还需检查最终state和逐行失败状态。

曲面从0开始，0为物面；对象、视场、波长、配置及评价函数操作数从1开始。分析选择全部视场和多色组合时使用该工具定义的0选项。文件路径必须为本机绝对路径。

波长以微米输入，550 nm为0.55，与镜头单位无关。几何量采用实际镜头单位；无限半径采用字符串Infinity。CyclesPerMillimeter解释为像空间频率，CyclesPerMilliradian解释为物空间角频率，修改单位须显式设置系统。

context包含会话、模型修订、来源/工作文件、软件版本、配置和单位。外层context表示当前模型，任务结果中的data.context表示计算时模型，两者可能不同。

## 任务与分页

run_*返回任务编号。用get_task_status查询running、succeeded、failed、cancelling或cancelled；取消请求后继续查询至最终状态。原生步骤可能需要等安全边界，不能将cancelling当作已释放资源。

get_task_result按具体数据使用start/count或网格区域分页。响应提供total、next_start或区域后续位置；inline_data_truncated=true时读取artifacts中的完整文件。分页上限按各工具定义，不能将首屏当作完整结果。

扫描和批量评估通常恢复基线；优化通常保留最终设计并提供起始检查点。复合流程succeeded表示流程结束，仍需检查summary.failed、逐行state和restoration。

## 模型与文件

服务加载后保存内部工作副本，关键修改前建立检查点。save_lens_as导出设计并继续使用内部工作副本；默认禁止覆盖，确需覆盖时传overwrite=true。输出文件持续保留，任务编号仅在当前服务进程内可查询。

影响solve/pickup的修改须显式允许替换。修订号在原生修改前推进，部分失败同样推进；partial_changes_possible=true时读取当前值或从检查点恢复。新建/加载后的工作副本保存失败时，保留此前检查点，重新新建或加载后再继续。

工具关闭或基线恢复未确认时requires_reconnect=true，先保留检查点并断开、重连。输入模型和官方样例保持只读。原生分析文本采用OpticStudio编码，本机通常为UTF-16。

## 常见错误

| 错误 | 处理 |
| --- | --- |
| NOT_CONNECTED / INSTALL_NOT_FOUND | 核对安装目录并连接后台实例 |
| INVALID_LICENSE | 核对本机许可与客户端显式环境值 |
| SOLVE_PROTECTED | 读取原关系，明确是否允许替换 |
| SETTING_REJECTED / SOLVE_UPDATE_FAILED | 查看请求值、实际值、字段和已完成项，避免重复盲写 |
| UNIT_MISMATCH | 核对系统和分析的MTF单位 |
| SYSTEM_BUSY / TASK_NOT_FINISHED | 查询当前任务，必要时请求取消 |
| OUTPUT_EXISTS | 使用新路径，或显式允许覆盖 |
| LOAD_FAILED | 原生加载失败，检查路径和文件；不得假定请求模型已经加载 |
| TASK_START_FAILED | 用错误中的task_id查询失败任务和关闭状态 |
| REQUEST_TIMEOUT | 执行状态未确认，先用get_status及request_id查找，避免重复修改 |
| NATIVE_ERROR / PARTIAL_UPDATE | 查看cause、修订、检查点及partial_changes_possible |
| RECONNECT_REQUIRED / CLEANUP_FAILED | 保存可用依据并重新连接 |
| RESULT_UNAVAILABLE | 核对结果文件位置及可读性 |

原生诊断写stderr，与stdio协议隔离。FRU的内部根因未知，不以诊断文字单独替代任务、退出或数值状态。专项错误见探测器与复场（历史参考）。


## 0.1.8 顺序 solve 扩展

`update_surfaces.changes[].solves`新增18个有类型模式，覆盖近轴角度/法线、消球差、光焦度、同心、OPD、补偿器、曲率中心、瞳位置、材料模型/偏移/替代、自动/最大口径和ZPL宏。`mechanical_semi_diameter`与`chip_zone`可作为solve单元格读取及设置；`get_system_resources(kind="solve_macros", surface=6, cell="radius")`发现当前可用宏。设置后核对实际模式与参数。

单位、条件、原生限制和分项验收见[solve-extensions.md](../topics/modeling/solve-extensions.md)，请求例子见[solve_extensions018_requests.json](../../examples/requests/solve_extensions018_requests.json)。本批新增调用链路已实现，ED-02状态为implemented；逐项状态见开发任务表。材料数值、多配置Maximum、GridSag宏补测及安装包原生验收等待恢复ZOS-API连接。


## 0.1.9 编辑器扩展

新增TDE逐行修改、插入和删除，MFE/MCE/TDE行插入、复制及元数据查询，以及原生.tol公差文件读写。当前79个工具、run_analysis的42个请求种类。普通833项通过，新增原生用例等待连接初始化恢复；本次180秒探测超时及关闭情况单独记录。请求、单位、条件及证据见`docs/topics/analysis/editor-extensions.md`与`development/evidence/editor-extensions019-summary.json`。全部剩余功能的继续顺序见`development/archive/legacy/rolling-development.md`。


## 0.1.10 设计工具与向导

新增`run_design_tool`、`get_design_tool_options`、`run_optimization_wizard`和`get_optimization_wizard_options`，覆盖Scale、Quick Adjust、最佳非球面、非球面转换、Ray Aiming及四类MFE优化向导。当前83工具、42种通用分析请求。普通回归899项通过，448项原生未执行。设置、单位、条件、原生待测范围和证据见[design-tools.md](../topics/analysis/design-tools.md)及`development/evidence/design-tools020-summary.json`。


## 0.1.11 镜头目录与候选评价

新增原生镜头目录发现、筛选、按厂商/名称加载或插入，以及独立基线的镜头/材料候选评价。当前87工具、42种通用分析请求。候选支持common_settings，并核对实际评价条件；失败与取消保留逐项状态并恢复基线。普通回归926项通过，450项原生未执行。接口、资源条件和证据见[lens-catalogs.md](../topics/analysis/lens-catalogs.md)及`development/evidence/lens-catalogs021-summary.json`。


## 0.1.12 请求追溯与历史结果

新增list_task_history、get_historical_result和get_request_status，支持请求回执、重启后历史任务发现、版本0/1结果和行/曲线/网格分页。当前90工具、42种通用分析请求。全量950项普通检查通过，450项原生未执行；真实stdio两次启动、关闭及跨进程结果读取通过。文档与证据见[task-history.md](task-history.md)及`development/evidence/task-history022-summary.json`。


## 0.1.13 成像与扩展源

新增image_simulation、geometric_image、fft_line_edge_spread、geometric_line_edge_spread和extended_source_encircled_energy；90工具、47种通用分析请求。原生标量/RGB网格、曲线、散点保留通道/标签/消息，支持资源发现、区域/曲线/行分页及绘图。范围、单位、状态和具体待测见docs/topics/imaging/imaging.md、examples/requests/imaging023_requests.json及development/evidence/imaging023-summary.json。几何位图设置接口保留具体探查阻塞，原生采用与数值验收等待初始化恢复。


## 0.1.14 镀膜性能与层编辑

新增12种镀膜角度/波长性能分析、coating_listing及get_coating_layers/update_coating_layers；当前92工具、60种通用分析。层编辑支持局部乘数/偏移、优化状态、拾取保护、最终回读及部分失败。参数、单位、例子和待测见docs/topics/imaging/coatings.md、examples/requests/coatings024_requests.json及development/evidence/coatings024-summary.json。PO-01五项专题及IM-01几何位图的运行时设置阻塞已记录，继续MA-01材料专题。


## 0.1.15 材料目录与内部透过率

新增get_material_properties及internal_transmission_vs_wavelength；当前93工具、61种通用分析。返回具名拟合系数、热属性和分页IT/双折射表；专题设置明确毫米厚度和材料目录身份，检查同名资源歧义。请求及待测见docs/topics/imaging/materials.md、examples/requests/materials025_requests.json和development/evidence/materials025-summary.json。四项材料图表的运行时设置阻塞分别登记；下一步继续NS系列。

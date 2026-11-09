# 设计工具与优化向导

## 位图/道路向导及成像运行时验收

完成NSCBitmapWizard和NSCRoadwayLightingWizard两项：实际Apply、评价函数输出及保存重载通过；位图使用原生资源列表中的square.bmp。




## NSC 评价函数读回修复与设计/目录验收


完成8项：QuickAdjust、SEQOptimizationWizard2、NSCOptimizationWizard、ED-05全部五项。QuickAdjust焦点47.35560260563906 mm，独立光线方差二次拟合47.35536453358475 mm，绝对差0.00023807205431 mm，预设容差0.01 mm；保存重载与正常关闭通过。目录取消/失败恢复普通回归亦通过。

RayAiming在Cooke预览180秒及受控模型Apply90秒均未终态，保留具体超时与原始调用，继续检查原生完成/取消条件。FindBestAsphere原生评价函数下降及重载已执行，独立最优候选参考待补；Bitmap已有13个原生位图选项，Bitmap/Roadway实际Apply待执行。材料Model/Offset此前数值超限继续保留。









## 调用入口

| MCP工具 | 参数和作用 |
| --- | --- |
| `run_design_tool` | `request.kind`选择`scale_factor/scale_units/quick_adjust/find_best_asphere/convert_asphere/ray_aiming_wizard`，返回原生工具任务 |
| `get_design_tool_options` | `request.kind`选择同类工具，读取原生默认设置及枚举后关闭工具 |
| `run_optimization_wizard` | `request.kind`选择`sequential/nsc/bitmap/roadway`，返回协作任务 |
| `get_optimization_wizard_options` | `request.kind`选择向导，读取设置、枚举与原生资源选项 |

任务通过既有`get_task_status/get_task_result/cancel_task`查询、读取和取消；完整结果保存JSON。请求例子在`examples/requests/design_tools020_requests.json`，完整字段见`docs/reference/tool-schemas.json`。当前83个MCP工具，42个`run_analysis`请求种类。

## 设计工具参数与结果

- `scale_factor`：必填正有限`factor`；`first_component/last_component`省略时使用原生默认范围。可先查询选项获取实际边界，显式范围逐项写入并最终回读。原生组件编号规则待实际连接确认。当前入口支持顺序系统。
- `scale_units`：必填`unit`，取`Millimeters/Centimeters/Inches/Meters`。原生缩放保留波长；本机手册说明系数按量纲缩放，PRAM/NPAR、用户DLL参数和CAD对象尺寸存在例外。具体模型的实际行为待测。
- `quick_adjust`：必填`surface`；`parameter=Thickness`或`Radius`；`criterion=SpotSizeRadial`，可选X/Y光斑或角度准则。`evaluate_surface`省略使用像面，评价面必须位于调整面之后。受控solve须显式`replace_solve=true`，替换在打开原生工具前完成。
- `find_best_asphere`：必填`first_surface/last_surface`，均位于像面前；`asphere_type=Conic`或4至12阶的原生多项式选项。沿用当前评价函数和变量，返回原生起始/最佳评价函数及最佳曲面。候选资格由原生工具判定。
- `convert_asphere`：必填`surface/asphere_type`；支持Even/Extended/QType0/QType1。`number_of_terms`省略采用原生自动模式，显式传入时使用正整数；另有二阶项排除及半径/圆锥系数可变开关。返回`ResidualRMSError`，单位为执行前镜头单位。本机`IsAutomatic`只有setter，结果明确记录该模式没有直接回读出口；其余公开设置逐项及最终回读。
- `ray_aiming_wizard`：默认`apply=false`，运行原生推荐计算并返回建议，核对系统设置保持原值；`apply=true`建立检查点、调用`ApplyRecommendedSettings`，逐项核对实际Ray Aiming设置。建议以主波长为基础，原生未给建议时返回具体结果错误。


OpticStudio 24.2.0 的 `OpenRayAimingWizard` 只读选项查询可正常创建并关闭；Cooke 样例的系统设置及曲面数据保持。适配器目前返回空 `settings` 字典。推荐计算的原生任务仍受生命周期问题阻塞：10秒等待返回 `TimedOut`，取消后仍 `IsRunning=true`，`Close()` 返回false。该项继续blocked，待任务能进入终态且关闭成功后再验推荐与Apply结果及保存重载。

模型修改前创建检查点并递增修订号。结果保存执行前后曲面类型、半径、厚度、圆锥系数、配置和单位；系数完整数据仍由`get_surfaces`读取。模型修改失败或取消后保留实际状态及检查点恢复入口。SystemTool由既有任务所有者负责关闭；关闭失败触发现有重连处理。

## 优化向导设置

四类向导使用本机正式MFE属性。默认`reset=true`，先重置原生向导；省略的字段沿用重置后的原生值。`reset=false`时基于当前向导设置局部修改。显式字段不得为null。

默认`apply=false`只配置并回读设置。`apply=true`在应用前建立模型检查点，通过原生`Apply`生成评价函数，返回应用前后操作数数量、评价函数分页读取结果、应用前后设置和检查点。Apply可能推进StartAt，因此保留应用后的实际值。

顺序向导覆盖优化类型、准则、参考点、Gaussian/Rectangular瞳采样、环臂/网格、遮拦、玻璃/空气边界、配置/视场、轴对称/横向色差、制造良率及畸变选项。设置Gaussian/Rectangular其中一个为true时补全互斥状态，按最终组合检查从属参数；制造良率选项检查原生可用标志。

NSC/位图向导覆盖本机`INSCWizard`的全部公开可写标量字段；道路向导覆盖灯具布置、道路类型/级别、车道及几何尺寸、光线选项、配置和权重。资源查询返回原生getter的索引、标签和查询错误；显式资源选择须可由对应getter解析。位图实际应用需要原生位图列表中的输入资源。索引与实际控件值的对应仍需原生验收。

MFE向导由编辑器拥有，正式接口没有SystemTool的Run/Cancel/Close；任务在设置和Apply前提供协作取消边界。Apply已完成后收到取消时，结果保留已采用的模型状态。

## 探查与检查证据

- 本机手册摘录：同目录`manual-page-*.txt`，涵盖Scale、Quick Adjust、非球面、Ray Aiming及各向导。
- 新增66项普通检查：`tests/unit/test_design_tools.py`、`tests/unit/test_wizards.py`，覆盖类型边界、活动条件、最终回读、原始错误、取消、关闭及向导Apply。
Scale参考为独立量纲换算，容差`1e-8 + 1e-7×参考值`；非球面转换逐点比较sag，同一容差。Quick Adjust最优性、Ray Aiming应用、位图/道路资源Apply仍需补独立参考及输入夹具。

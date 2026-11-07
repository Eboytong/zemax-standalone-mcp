# 0.1.10 设计工具与优化向导

## 0.1.48 位图/道路向导及成像运行时验收

完成NSCBitmapWizard和NSCRoadwayLightingWizard两项：实际Apply、评价函数输出及保存重载通过；位图使用原生资源列表中的square.bmp。GeometricImage点源/条纹/边缘已完成设置采用、结果读取、分页及图像导出，独立数值参考仍待补，保持implemented。

ImageSimulation用受控IMA及BMP均未取得可读取结果，当前GetTextFile返回false；下一步探查正式输出图像和结果契约。GeometricBitmapImageAnalysis实际GetSettings为AS_Default且无GetFileNames；已返回含实际类型和缺失方法的UNSUPPORTED_INTERFACE，普通与原生关闭/会话复用检查通过。该条目转blocked，继续探查CFG采用及正式结果出口。

全量普通1702通过；独立安装0.1.48 wheel，真实stdio三项冒烟通过（位图Apply、道路Apply、几何位图限制及清理）。原始失败与成功报告分别保留，证据 verification/development/IM-01/acceptance050/summary.json；发行 verification/development/BASE-04/release048.json。下一步继续成像数值/出口探查，再推进偏振、镀膜和材料。全量目标继续进行。


## 0.1.47 NSC 评价函数读回修复与设计/目录验收

修复 get_merit_function 的顺序模式限制：NSC向导Apply后可正常读取生成的评价函数；请求字段保持原样，新增模式支持。补普通NSC读回回归，修正目录候选测试的材料字段路径。全量普通1701通过；安装包真实stdio四项通过，包括NSC向导Apply、独立焦点、目录加载/插入与候选恢复。

完成8项：QuickAdjust、SEQOptimizationWizard2、NSCOptimizationWizard、ED-05全部五项。QuickAdjust焦点47.35560260563906 mm，独立光线方差二次拟合47.35536453358475 mm，绝对差0.00023807205431 mm，预设容差0.01 mm；保存重载与正常关闭通过。目录取消/失败恢复普通回归亦通过。

RayAiming在Cooke预览180秒及受控模型Apply90秒均未终态，保留具体超时与原始调用，继续检查原生完成/取消条件。FindBestAsphere原生评价函数下降及重载已执行，独立最优候选参考待补；Bitmap已有13个原生位图选项，Bitmap/Roadway实际Apply待执行。材料Model/Offset此前数值超限继续保留。

证据 verification/development/ED-04/acceptance049/summary.json，发行 verification/development/BASE-04/release047.json。0.1.47 wheel已构建并独立安装；本轮初次失败及修复后报告分别保留。下一步按上述四项及后续成像/材料队列继续，全量目标保持进行。


## 2026-11-05 独立材料、编辑器与设计工具验收

本轮新增17项完成：MaterialSubstitute、ED-03的14项操作、Scale与非球面转换。六波长双入射角Substitute比较18项通过，保存重载及关闭通过。编辑器覆盖通用TDE插入及MFE/MCE/TDE最终状态重载；Scale两种路径及转换sag、曲面参数重载通过。163项相关普通检查通过。首次测试响应字段读取错误与修正后结果分别保留。

Model与Offset已拆成独立基线执行，原生舍入谱线阿贝数分别为59.99988524798844（目标60）和增量0.9992435881404731（目标1），仍超原容差1e-5+1e-7×参考值，继续implemented。下一步定位原生色散定义，继续ED-04剩余七项与ED-05；MCE独立文件正式入口仍缺失。

证据 verification/development/ED-03/acceptance048/summary.json，JUnit native048-final.xml及ED-04/native048.xml。本轮只修改测试、证据、文档与台账，版本保留0.1.46，全量目标继续进行。


更新日期：2026-11-05。ED-04九个操作已接入有类型请求和结果链路，状态为`implemented`。本批普通回归899项通过；448项原生检查未执行，其中新增10项原生用例。原生采用、数值和关闭验收待ZOS-API连接恢复后执行。

## 调用入口

| MCP工具 | 参数和作用 |
| --- | --- |
| `run_design_tool` | `request.kind`选择`scale_factor/scale_units/quick_adjust/find_best_asphere/convert_asphere/ray_aiming_wizard`，返回原生工具任务 |
| `get_design_tool_options` | `request.kind`选择同类工具，读取原生默认设置及枚举后关闭工具 |
| `run_optimization_wizard` | `request.kind`选择`sequential/nsc/bitmap/roadway`，返回协作任务 |
| `get_optimization_wizard_options` | `request.kind`选择向导，读取设置、枚举与原生资源选项 |

任务通过既有`get_task_status/get_task_result/cancel_task`查询、读取和取消；完整结果保存JSON。请求例子在`examples/design_tools020_requests.json`，完整字段见`docs/tool-schemas.json`。当前83个MCP工具，42个`run_analysis`请求种类。

## 设计工具参数与结果

- `scale_factor`：必填正有限`factor`；`first_component/last_component`省略时使用原生默认范围。可先查询选项获取实际边界，显式范围逐项写入并最终回读。原生组件编号规则待实际连接确认。当前入口支持顺序系统。
- `scale_units`：必填`unit`，取`Millimeters/Centimeters/Inches/Meters`。原生缩放保留波长；本机手册说明系数按量纲缩放，PRAM/NPAR、用户DLL参数和CAD对象尺寸存在例外。具体模型的实际行为待测。
- `quick_adjust`：必填`surface`；`parameter=Thickness`或`Radius`；`criterion=SpotSizeRadial`，可选X/Y光斑或角度准则。`evaluate_surface`省略使用像面，评价面必须位于调整面之后。受控solve须显式`replace_solve=true`，替换在打开原生工具前完成。
- `find_best_asphere`：必填`first_surface/last_surface`，均位于像面前；`asphere_type=Conic`或4至12阶的原生多项式选项。沿用当前评价函数和变量，返回原生起始/最佳评价函数及最佳曲面。候选资格由原生工具判定。
- `convert_asphere`：必填`surface/asphere_type`；支持Even/Extended/QType0/QType1。`number_of_terms`省略采用原生自动模式，显式传入时使用正整数；另有二阶项排除及半径/圆锥系数可变开关。返回`ResidualRMSError`，单位为执行前镜头单位。本机`IsAutomatic`只有setter，结果明确记录该模式没有直接回读出口；其余公开设置逐项及最终回读。
- `ray_aiming_wizard`：默认`apply=false`，运行原生推荐计算并返回建议，核对系统设置保持原值；`apply=true`建立检查点、调用`ApplyRecommendedSettings`，逐项核对实际Ray Aiming设置。建议以主波长为基础，原生未给建议时返回具体结果错误。

模型修改前创建检查点并递增修订号。结果保存执行前后曲面类型、半径、厚度、圆锥系数、配置和单位；系数完整数据仍由`get_surfaces`读取。模型修改失败或取消后保留实际状态及检查点恢复入口。SystemTool由既有任务所有者负责关闭；关闭失败触发现有重连处理。

## 优化向导设置

四类向导使用本机正式MFE属性。默认`reset=true`，先重置原生向导；省略的字段沿用重置后的原生值。`reset=false`时基于当前向导设置局部修改。显式字段不得为null。

默认`apply=false`只配置并回读设置。`apply=true`在应用前建立模型检查点，通过原生`Apply`生成评价函数，返回应用前后操作数数量、评价函数分页读取结果、应用前后设置和检查点。Apply可能推进StartAt，因此保留应用后的实际值。

顺序向导覆盖优化类型、准则、参考点、Gaussian/Rectangular瞳采样、环臂/网格、遮拦、玻璃/空气边界、配置/视场、轴对称/横向色差、制造良率及畸变选项。设置Gaussian/Rectangular其中一个为true时补全互斥状态，按最终组合检查从属参数；制造良率选项检查原生可用标志。

NSC/位图向导覆盖本机`INSCWizard`的全部公开可写标量字段；道路向导覆盖灯具布置、道路类型/级别、车道及几何尺寸、光线选项、配置和权重。资源查询返回原生getter的索引、标签和查询错误；显式资源选择须可由对应getter解析。位图实际应用需要原生位图列表中的输入资源。索引与实际控件值的对应仍需原生验收。

MFE向导由编辑器拥有，正式接口没有SystemTool的Run/Cancel/Close；任务在设置和Apply前提供协作取消边界。Apply已完成后收到取消时，结果保留已采用的模型状态。

## 探查与检查证据

- 本机接口：`verification/development/ED-04/probe/interfaces.json`；继承关系：`inheritance.json`。已确认Ray Aiming属于ISystemTool，SEQ向导属于IWizard。
- 本机手册摘录：同目录`manual-page-*.txt`，涵盖Scale、Quick Adjust、非球面、Ray Aiming及各向导。
- 新增66项普通检查：`tests/test_design_tools.py`、`tests/test_wizards.py`，覆盖类型边界、活动条件、最终回读、原始错误、取消、关闭及向导Apply。
- 全量普通回归：`verification/development/ED-04/ordinary020-final.xml`，899通过，448原生未执行，15.32秒。首次回归的测试替身错误保留在`ordinary020.xml`。
- 待执行原生用例：`tests/test_design_tools_live.py`。Scale参考为独立量纲换算，容差`1e-8 + 1e-7×参考值`；非球面转换逐点比较sag，同一容差。Quick Adjust最优性、Ray Aiming应用、位图/道路资源Apply仍需补独立参考及输入夹具。
- 原生连接条件沿用`verification/development/BASE-04/connection019/supervisor.json`：180秒初始化未返回。本批没有重启原生实例，正常原生关闭验收待测。
- 批次汇总：`verification/design-tools020-summary.json`。安装包与真实stdio结果由发行步骤补入该汇总。


B001进展（2026-11-05，基线0.1.56）：FindBestAsphere独立Conic候选比较完成。Cooke同一基线下手动分别设置曲面1/2的conic为变量并运行DLS Automatic，候选评价函数分别0.0030534502405461456、0.0016077722515191782；原生选择曲面2，最优值完全相同。初值0.00809324547994345，保存重载后的曲面、solve及评价函数保持；三个任务均succeeded/close_attempted，disconnect成功。原容差1e-7+1e-5×参考值。普通定向63通过；见verification/development/ED-04/acceptance062/summary.json，真实stdio输出outputs/runs/best_asphere062_1d547abc51。条目done，批次1/10，本轮无全量、wheel或独立安装。

转换差异探查：Cooke分别使用no_stop、ignore_errors、pure/no_stop，前两项TASK_START_FAILED，pure/no_stop成功。见outputs/runs/conversion_options062_35ee51bf2a/option-results.json；该探查用例通过表示三种结果记录完成，父条目原生等价光线/持久性仍待验收。早期探查辅助代码错误读取成功响应的ok字段已修正，失败记录8038cc0c1f保留。下一步继续RayAiming的新条件探查及纯NSC转换剩余验收，现有重复失败条件不重跑。

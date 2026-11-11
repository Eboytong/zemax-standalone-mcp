# GitHub源码参考与适配说明

核对日期：2026-11-11。实施时先读取本表对应文件，记录具体借鉴和本机验证；源版本固定到commit。[机器可读清单](tracking/github-references.json)维护仓库、commit、许可及任务映射。

| 编号 | 仓库 | 固定commit | 许可 | 对应任务 |
| --- | --- | --- | --- | --- |
| G2 | [YonggangG/Zemax_MCP_Server](https://github.com/YonggangG/Zemax_MCP_Server) | `193598e4ca6224dfa8615565d5e3b6f3cfa6d149` | MIT | D003、D007、D010 |
| G3 | [joeyijun/OpticStudioMCPServer](https://github.com/joeyijun/OpticStudioMCPServer) | `a7375ba48235b2db71ae40766dbc1969c0671401` | MIT | 已交付D002、D006；1.3.0的D020 |
| G4 | [chuang44-tiff/optivibe-mcp](https://github.com/chuang44-tiff/optivibe-mcp) | `50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3` | Apache-2.0 | 已交付D001、D004、D008；1.3.0的D019 |
| G5 | [zhaopeizhao41-ops/optiforge](https://github.com/zhaopeizhao41-ops/optiforge) | `6a197e467c7fceeb51ab651b3dbea21d9781d94e` | MIT | D005、D009、D010、D011 |

## G2：Detector Viewer与NSC

[NSC实现](https://github.com/YonggangG/Zemax_MCP_Server/blob/193598e4ca6224dfa8615565d5e3b6f3cfa6d149/src/zemax_mcp/zos/subsystems/nsc.py)，重点读取viewer的创建、Detector/ShowAs/DataType/Scale/Smoothing/Filter写入、结果和finally关闭。[运行报告](https://github.com/YonggangG/Zemax_MCP_Server/blob/193598e4ca6224dfa8615565d5e3b6f3cfa6d149/live-test-report.md)的Batch 3记录viewer运行；验收范围以其报告条件理解。

D003补本项目有类型请求、枚举值回读、当前数据/ZRD来源及结果分页。当前数据模式限制非空Filter；原始探测器数据与显示网格分别标识。D007已确认纯NSC优化、NCE变量及NSDD/NSTR/OSUM目标，D010复用正式ZRD和路径能力。

## G3：曲面镀膜直接R/T/A

[工具文件](https://github.com/joeyijun/OpticStudioMCPServer/blob/a7375ba48235b2db71ae40766dbc1969c0671401/src/ZemaxMCP.Server/Tools/Analysis/GetCoatingRtaTool.cs)：角度/波长/方向合同、曲面身份、S/P返回。实施前同时读其调用的底层interop路径；实际签名以本机DLL为准。

本项目2024 R2已实际取得GetCoatingPerformanceData及双向结果，D002可直接据此适配。源码中接口版本声明与本机可用版本分别记录。普通顺序面的扫描ReverseDirection受限，直接outward查询单独验收。

## G4：GRIN、玻璃试验与几何阈值

- [grin_surface.py](https://github.com/chuang44-tiff/optivibe-mcp/blob/50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3/packages/optivibe-harness/src/optivibe_harness/tools/grin_surface.py)：Gradient2的n²、Gradient3的n、系数映射与Variable。D001沿用本项目局部修改语义；外部实现省略系数清零及固定步长的行为按本机任务合同处理。
- [glass_explain.py](https://github.com/chuang44-tiff/optivibe-mcp/blob/50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3/packages/optivibe-harness/src/optivibe_harness/tools/glass_explain.py)：三阶/近轴贡献、镜片分组、材料目录绑定和Petzval预测。D008区分贡献定义、直接替换结果和重新优化结果。
- [glass_trial.py](https://github.com/chuang44-tiff/optivibe-mcp/blob/50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3/packages/optivibe-harness/src/optivibe_harness/tools/glass_trial.py)：对照组、候选、分块优化预算、最佳模型保存及恢复。D008复用现有catalog/evaluation，按本项目变量与预算合同实施。
- [clearance.py](https://github.com/chuang44-tiff/optivibe-mcp/blob/50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3/packages/optivibe-harness/src/optivibe_harness/tools/clearance.py)：几何间隙、中心/边缘厚度及折转模型处理。D004将阈值和测量量分开记录。

许可证[LICENSE](https://github.com/chuang44-tiff/optivibe-mcp/blob/50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3/LICENSE)和[NOTICE](https://github.com/chuang44-tiff/optivibe-mcp/blob/50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3/NOTICE)已读取；复制或改写代码时保留适用声明，记录修改文件及内容。

## G5：扫描、共焦及耦合工作流

[confocal_tools.py](https://github.com/zhaopeizhao41-ops/optiforge/blob/6a197e467c7fceeb51ab651b3dbea21d9781d94e/tools/confocal_tools.py)已核对三个函数：

| 函数 | 源实现 | 本项目采用方式 |
| --- | --- | --- |
| zemax_confocal_response | 改变像面前厚度，逐点读取PSF峰值，以离散半高索引求FWHM | 参考分析创建/采集流程；D011采用照明与检测双路径、有限针孔积分、统一归一化及交点插值 |
| zemax_fiber_coupling | 由PSF强度平方根构造实振幅并计算模式重叠 | D005采用现有原生POP复场/耦合积分，保留波前相位 |
| zemax_scan_pupil_check | 光线高度比及曲面间厚度和，读取主光线角 | 参考参数组织；D009用明确的实际镜面转轴、非退化光线和成像关系求瞳共轭，并核对坐标变换 |

[tolerance_tools.py](https://github.com/zhaopeizhao41-ops/optiforge/blob/6a197e467c7fceeb51ab651b3dbea21d9781d94e/tools/tolerance_tools.py)是公差和反射估算的额外参考入口，实施对应分项时再核对具体函数。反射率估算与实际ZRD功率分别标记。


## 1.3.0的D019/D020新增参考

D019复用已交付D008及G4的glass_trial/glass_explain，增加多槽位联合候选、预算和比较。材料身份与原生优化合同继续按本项目实现。

D020已实际读取G3固定commit的[ForbesMeritFunctionTool.cs](https://github.com/joeyijun/OpticStudioMCPServer/blob/a7375ba48235b2db71ae40766dbc1969c0671401/src/ZemaxMCP.Server/Tools/Optimization/ForbesMeritFunctionTool.cs)和[ForbesPupilSampling.cs](https://github.com/joeyijun/OpticStudioMCPServer/blob/a7375ba48235b2db71ae40766dbc1969c0671401/src/ZemaxMCP.Server/Tools/Optimization/ForbesPupilSampling.cs)。构建事务及参数检查可作参考；普通采样0—π、轴上单子午线及象限缩减分别需要相应对称条件。采用原生向导并用完整瞳数值参考核对自定义目标，详见[选题记录](evidence/PLAN-20261111/README.md)。

## 官方定义与现有实现

- [Gradient2官方定义](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Gradient_2.html)
- [Gradient3官方定义](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Gradient_3.html)
- [Detector Viewer官方定义](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v251/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Detector_Viewer.html)；版本差异以本机设置对象确认。
- [Ansys共焦荧光显微镜教程](https://optics.ansys.com/hc/en-us/articles/42712682220691-How-to-design-a-confocal-fluorescent-microscope-in-OpticStudio)
- [Ansys系统级杂散光自动化](https://optics.ansys.com/hc/en-us/articles/42047529058963-Automating-system-level-stray-light-analysis-and-optical-noise-reduction-with-Ansys-Optics)
- 本项目：catalogs/evaluation、physical_optics/pop_models、path_analysis、coatings/coating_models、geometry_backend、nonsequential、configurations和tolerancing。
- [四项本机探查](evidence/native-feature-portability-20261110.md)保留原始数据、运行环境、误差和关闭情况。

当前记录属于源码参考登记；每项原生验收按[计划第7节](plan.md#7-完成状态与证据)补具体输入、设置和结果。GitHub运行记录可复用其方法，数值结论按本项目实际模型取得。

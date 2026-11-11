# 能力索引

Zemax Standalone MCP 1.4.0 提供 107 个工具和 146 种 `run_analysis` 请求类型。

full直接提供107工具；compact提供11个固定发现/调用/任务控制入口，通过tool、analysis和action能力ID访问同一套操作。单项详情只返回相关schema；工程流程可与原生工具自主组合。见[披露模式](../guides/capability-search.md)。

| 领域 | 主要能力 | 文档 |
| --- | --- | --- |
| 系统与建模 | 系统设置、顺序曲面、配置、变量、评价函数、材料、镀膜与目录镜头 | [建模](../topics/modeling/) · [工具清单](tools.md) |
| 光线与非序列 | 顺序批量追迹、NSC 追迹、ZRD、探测器、对象与路径数据 | [非序列](../topics/nonsequential/) |
| 成像与分析 | 光斑、MTF、PSF、RMS、波前、畸变、照度、偏振、材料与文本报告 | [分析](../topics/analysis/) · [成像](../topics/imaging/) |
| 物理光学 | POP、Gaussian Beam、ZBF 复场、耦合与传播图 | [传播](../topics/propagation/) |
| 优化与公差 | 评价函数、局部/全局优化、参数扫描、公差、Monte Carlo 与 QuickYield | [公差](../topics/tolerancing/) |
| 导出与交付 | 布局、分析图、报告、CAD、Speos、点云、探测器和归档文件 | [交付](../topics/delivery/) |
| 扩展接口 | STAR、HPC 和相关原生扩展数据 | [扩展](../topics/extensions/) |

完整的工具名称、字段、枚举、单位和结果结构以 [工具清单](tools.md) 与 [请求 schema](tool-schemas.json) 为准。各专题页面说明运行所需的本机资源、可选输入文件及结果字段。

## 工程计算入口

| 入口 | 结果 |
| --- | --- |
| `search_capabilities` | 中文需求检索、静态条件及schema详情 |
| `manage_candidates` / `run_candidate_evaluation` | 候选分支、恢复和冻结评价比较 |
| `get_glass_slots` / `run_analysis: glass_trials` | 目录身份、多个材料槽位联合搜索及同预算比较 |
| `run_merit_program` | 原生向导、完整瞳OPD目标、尺度与几何约束 |
| `run_analysis: design_desensitize` | 固定公差、原生制造良率优化和独立Monte Carlo |
| `run_analysis: sequential_energy_budget` | 逐面偏振损耗、截断定位和带权W换算 |
| `get_coating_rta` | 指定曲面的双向S/P镀膜反射、透射与吸收 |
| `run_analysis: manufacturing_geometry` | sag、坡度、曲率和制造阈值 |
| `run_analysis: fiber_alignment` | 原生POP耦合、位姿扫描、对准与损耗宽度 |
| `run_analysis: coating_optimization` | 固定膜系、多条件厚度优化 |
| `run_analysis: nsc_efficiency` | ROI功率、均匀性、扫描与原生优化 |
| `run_analysis: glass_trials` | 材料贡献、目录候选和同预算优化比较 |
| `run_analysis: scan_pupil` | 扫描镜、瞳共轭、光束走离与通过率 |
| `run_analysis: ghost_diagnostics` | 原生ZRD鬼像路径及候选变更 |
| `run_analysis: confocal_response` | 双路径PSF、有限针孔和轴向响应 |
| `run_analysis: thermal_compensation` | 均温多配置及独立焦点补偿 |
| `run_multistart_optimization.pareto` | 有限权重网格的可行候选和非支配集合 |
| `run_analysis: tolerance_budget` | 原生成本公差候选、良率区间和独立验证 |
| `run_analysis: fsm_control` | 双FSM响应矩阵、离散控制与逐步原生追迹 |

参数范围、模型结构和结果定义见[分析专题](../topics/analysis/README.md)及请求schema。

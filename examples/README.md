# 使用示例

从项目根目录使用 `.venv\Scripts\python.exe -B` 运行。光学流程需要本机 OpticStudio 和相应许可。

| 入口 | 用途 |
| --- | --- |
| [run_workflow.py](workflows/run_workflow.py) | 分析、文件、NSC、POP、公差与布局工作流，使用 `--help` 查看选项 |
| [evaluate_design.py](workflows/evaluate_design.py) | 官方 Cooke 样例的追迹、扫描、评价、比较及报告 |
| [extended_workflows.json](requests/extended_workflows.json) | 工作流请求模板 |
| [solve_requests.json](requests/solve_requests.json) | solve 请求 |
| [model-adaptation.json](requests/model-adaptation.json) | 面型、参数、映射与对象设置请求 |
| [universal-targets236.json](requests/universal-targets236.json) | Universal 操作数及评价函数目标 |
| [universal-numeric-mce261.json](requests/universal-numeric-mce261.json) | Universal 多配置数值扫描轴 |
| [point-cloud179.json](requests/point-cloud179.json) | 点云导出请求 |
| [bitmap-intensity.json](requests/bitmap-intensity.json) | 几何位图、原生强度网格分页与图像导出 |

其余 JSON 按专题提供请求模板，字段说明见 [docs](../docs/reference/capabilities.md) 和 [请求模型](../docs/reference/tool-schemas.json)。将路径、模型编号和任务编号替换为实际值，并核对模板中的前置条件。

脚本通过工作副本执行修改并生成输出。`run_*` 先返回任务编号，查询至终态后读取结果；重启后的任务使用历史结果接口查询。


高斯光束：`gaussian-beams.json` 提供近轴 M² 和 skew 双轴调用；参数、单位和输出见 `../docs/topics/propagation/README.md`。

`sag-table.json` 提供制造表 MinimumVolume 查询；字段说明见 `../docs/topics/analysis/README.md`。

`ray-diagrams.json` 提供 Y-Ybar 及入射角随像高请求；参数和坐标定义见 `../docs/topics/analysis/README.md`。

`biocular.json` 提供双配置会聚/发散扫描；`biocular-fov.json` 提供四槽配置和非方形网格示例。

- `test-plates.json`：样板目录资源发现、原生活动目录读取及显式TPD文件读取。

IMA/BIM 查看示例：[`ima-bim-viewer.json`](requests/ima-bim-viewer.json)。

请求模板位于 `requests/`，工作流脚本位于 `workflows/`，配置模板位于 `config/`。运行输出默认位于 `.local/runs/`。

默认报告示例见 `requests/native-text-reports.json`，STAR 分析见 `requests/star-analyses.json`，STAR 卸载见 `requests/star-unload.json`。参数和资源条件见对应专题文档。

NSC光源模式请求见[nsc-source-spectra.json](requests/nsc-source-spectra.json)：十种原生模式使用专属参数；NCE源设置与独立光谱查看器的输入分别记录。

工程计算请求：[均温补偿](requests/thermal-compensation.json)、[多目标候选](requests/pareto-search.json)、[公差成本预算](requests/tolerance-budget.json)、[双FSM控制](requests/fsm-control.json)。输入须对应当前模型和专题说明中的坐标、单位及原生资源。

工程搜索及损耗请求：[能力搜索](requests/capability-search.json)、[评价函数](requests/merit-program.json)、[逐面能量](requests/sequential-energy-budget.json)。候选、联合玻璃和去敏感化的完整调用见[使用指南](../docs/README.md)。

精简工具披露：[compact波前](requests/compact-wavefront.json)提供搜索、单能力详情、执行及只读调用形状；[材料试验关闭贡献](requests/glass-trials-optional-contribution.json)适用于单波长、有限共轭或非球面模型。调用顺序与配置见[能力发现指南](../docs/guides/capability-search.md)。

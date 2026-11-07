# 使用示例

从项目根目录使用 `.venv\Scripts\python.exe -B` 运行。光学流程需要本机 OpticStudio 和相应许可。

| 入口 | 用途 |
| --- | --- |
| [run_workflow.py](run_workflow.py) | 分析、文件、NSC、POP、公差与布局工作流，使用 `--help` 查看选项 |
| [evaluate_design.py](evaluate_design.py) | 官方 Cooke 样例的追迹、扫描、评价、比较及报告 |
| [extended_workflows.json](extended_workflows.json) | 工作流请求模板 |
| [solve_requests.json](solve_requests.json) | solve 请求 |
| [model-adaptation.json](model-adaptation.json) | 面型、参数、映射与对象设置请求 |
| [universal-targets236.json](universal-targets236.json) | Universal 操作数及评价函数目标 |
| [universal-numeric-mce261.json](universal-numeric-mce261.json) | Universal 多配置数值扫描轴 |
| [point-cloud179.json](point-cloud179.json) | 点云导出请求 |

其余 JSON 按专题提供请求模板，字段说明见 [docs](../docs/capabilities.md) 和 [请求模型](../docs/tool-schemas.json)。将路径、模型编号和任务编号替换为实际值，并核对模板中的前置条件。

脚本通过工作副本执行修改并生成输出。`run_*` 先返回任务编号，查询至终态后读取结果；重启后的任务使用历史结果接口查询。


高斯光束：`gaussian-beams.json` 提供近轴M²和skew双轴调用；来源、单位、输出和验收见 `../docs/gaussian-beams.md`。


`sag-table.json`提供制造表MinimumVolume查询，当前implemented；完整状态见`../docs/sag-table.md`。


`ray-diagrams.json`提供Y-Ybar及入射角随像高请求，已完成本机原生验收；参数和坐标定义见`../docs/ray-diagrams.md`。


`biocular.json`提供双配置会聚/发散扫描；已完成本机原生验收，副本真实追迹验证与数据状态见`../docs/biocular.md`。


`biocular-fov.json`提供四槽配置和非方形网格示例，已完成本机原生验收；详见`../docs/biocular-fov.md`。

- `test-plates.json`：样板目录资源发现、原生活动目录读取及显式TPD文件读取。

IMA/BIM 查看示例：[`ima-bim-viewer.json`](ima-bim-viewer.json)。

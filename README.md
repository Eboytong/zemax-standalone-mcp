# Zemax Standalone MCP

本机 Windows x64、Python 3.14、OpticStudio 2024 R2 的 stdio MCP 服务。1.0.0 正式版提供 101 个工具和 132 种 run_analysis 请求类型。发行范围及逐项成熟度见能力说明和接口清单。

原生功能历史计划包含 96 组（OpticStudio 内建、官方 STAR 与 HPC）。其中 7 组完成过完整验收；其余 89 组保持原状态，作为冻结的后续工作记录，不属于 1.0.0 的完成声明。

1.0.0 将当前源码与发行接口统一为 101 个工具、132 种分析请求。项目进入维护阶段；当前版本基线、已知限制和验证结果见 1.0.0 发行记录。

项目于 2026-11-09 停止新增功能排期并进入维护阶段。历史原生计划的完成度和未完成条目保留在台账中；发行验证见[1.0.0发行记录](development/evidence/BASE-04/release100.md)。


- [使用文档](docs/README.md) · [工具参考](docs/reference/tools.md) · [请求schema](docs/reference/tool-schemas.json)
- [维护与开发记录](development/README.md) · [1.0.0发行记录](development/evidence/BASE-04/release100.md) · [冻结的后续工作表](development/remaining-ranked.md)
- [调用示例](examples/README.md) · [测试说明](tests/README.md)

安装：`powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe C:\Users\tonge\anaconda3\python.exe -WithReports -WithGeometry`。
启动：`powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1`。
安装生成的客户端配置位于 `.local/config/mcp.config.json`。

| 目录 | 用途 |
| --- | --- |
| src | 产品源码 |
| docs | 使用指南、接口和专题 |
| development | 计划、台账、证据和交接 |
| tests | 普通/原生测试与共享参考 |
| scripts | 开发统计、探查和发行工具 |
| examples | 工作流、请求和输入资源 |
| requirements | 锁定依赖 |
| releases | 已发行wheel |
| .local | 本机运行、状态、复现数据和历史归档 |

`.local/runs`为默认运行目录；`.local/state`为状态目录。显式环境变量优先采用。当前默认wheel位于`releases/1.0.0/`。

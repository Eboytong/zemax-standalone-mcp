# Zemax Standalone MCP 0.1.61

本机Windows x64、Python 3.14、OpticStudio 2024 R2的stdio MCP服务。100工具、110种分析。B005已发行；B006为5/10，目标0.1.62。

- [使用文档](docs/README.md) · [工具参考](docs/reference/tools.md) · [请求schema](docs/reference/tool-schemas.json)
- [开发入口](development/README.md) · [当前交接](development/handoff.md) · [剩余排序](development/remaining-ranked.md)
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

`.local/runs`为默认运行目录；`.local/state`为状态目录。显式环境变量优先采用。当前wheel保留0.1.61原始产物。

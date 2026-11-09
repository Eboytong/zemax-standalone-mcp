# Zemax Standalone MCP

Zemax Standalone MCP 是运行于 Windows x64、Python 3.14 与 OpticStudio 2024 R2 的 stdio MCP 服务。当前发布版本为 **1.0.0**，提供 **101 个工具**与 **132 种 `run_analysis` 请求类型**；接口、适用条件和结果格式见使用文档与工具参考。

项目当前处于维护阶段。1.0.0 的版本基线、安装验证和运行条件见 [发行记录](development/evidence/BASE-04/release100.md)。


- [使用文档](docs/README.md) · [工具参考](docs/reference/tools.md) · [请求schema](docs/reference/tool-schemas.json)
- [维护与开发记录](development/README.md) · [1.0.0发行记录](development/evidence/BASE-04/release100.md)
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

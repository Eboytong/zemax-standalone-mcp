# Zemax Standalone MCP 1.0.0

本地正式发行包：zemax_standalone_mcp-1.0.0-py3-none-any.whl。

运行基线为 Windows x64、Python 3.14 和 OpticStudio 2024 R2。服务提供 101 个 MCP 工具和 132 种 run_analysis 请求。历史原生功能计划包含 96 组，其中 7 组有完整验收记录、89 组未完成并冻结；未完成项不属于本版本完成声明。

在仓库根目录执行安装：

    powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe C:\Users\tonge\anaconda3\python.exe -WithReports -WithGeometry

安装生成 .local/config/mcp.config.json。接口与限制见 docs/README.md、docs/reference/tools.md 和 docs/reference/capabilities.md；发行验证见 development/evidence/BASE-04/release100.md。

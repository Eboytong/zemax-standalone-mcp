# Zemax Standalone MCP 1.0.0

本地正式发行包：zemax_standalone_mcp-1.0.0-py3-none-any.whl。

运行基线为 Windows x64、Python 3.14 和 OpticStudio 2024 R2。服务提供 101 个 MCP 工具和 132 种 `run_analysis` 请求类型。接口、适用条件和限制见 `docs/README.md`、`docs/reference/tools.md` 与 `docs/reference/capabilities.md`。

在仓库根目录执行安装：

    powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe python -WithReports -WithGeometry

`python` 应指向 Python 3.14 x64，也可使用该版本解释器的绝对路径。`-WithReports` 和 `-WithGeometry` 安装对应可选依赖。

安装生成 `.local/config/mcp.config.json`。

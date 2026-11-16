# 原生启动与连接

服务采用 OpticStudio Standalone 模式。日常使用时由 MCP 通过 `connect` 创建后台实例；无需打开 OpticStudio 的“交互扩展”窗口。

默认启动环境为 Windows x64、Python 3.14 与 Ansys Zemax OpticStudio 2026 R1，安装路径为`C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio`。运行账户需要具有可用的 ZOS-API 许可。`connect` 成功后读取许可、主系统和当前设置；`disconnect` 关闭由服务创建的应用实例。

`ZEMAX_INSTALL_DIR`覆盖安装路径；`ZEMAX_OUTPUT_DIR`和`ZEMAX_STATE_DIR`分别指定输出与状态目录。安装脚本和启动脚本采用已有环境值。`start.ps1`默认目录为`.local/runs`、`.local/state`；`start-2026r1.ps1`使用`.local/runs-2026r1`、`.local/state-2026r1`。

默认工具目录为`compact`。`install.ps1`、`start.ps1`和`start-2026r1.ps1`支持`-ToolMode full`；显式参数优先于`ZEMAX_TOOL_MODE`，环境变量优先于默认值。通过MCP客户端启动Python时，配置中的env决定该进程的环境；修改后重启连接生效。

如连接失败，依次检查 OpticStudio 安装、许可证状态、Python 运行环境和同一用户会话。`get_status` 返回连接状态、模型修订和正在运行的任务；错误响应中的 `startup_stage` 标识安装检查、CLR 加载、API 程序集加载、应用创建或许可检查阶段。

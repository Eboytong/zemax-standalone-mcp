# 原生启动与连接

服务采用 OpticStudio Standalone 模式。日常使用时由 MCP 通过 `connect` 创建后台实例；无需打开 OpticStudio 的“交互扩展”窗口。

启动环境为 Windows x64、Python 3.14 与 Ansys Zemax OpticStudio 2024 R2。运行账户需要具有可用的 ZOS-API 许可。`connect` 成功后读取许可、主系统和当前设置；`disconnect` 关闭由服务创建的应用实例。

如连接失败，依次检查 OpticStudio 安装、许可证状态、Python 运行环境和同一用户会话。`get_status` 返回连接状态、模型修订和正在运行的任务；错误响应中的 `startup_stage` 标识安装检查、CLR 加载、API 程序集加载、应用创建或许可检查阶段。

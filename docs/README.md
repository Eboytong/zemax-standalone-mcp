# Zemax Standalone MCP 使用文档

Zemax Standalone MCP 1.0.0 在 Windows x64、Python 3.14 与 Ansys Zemax OpticStudio 2024 R2 上提供 101 个 MCP 工具和 132 种 `run_analysis` 请求类型。

## 文档导航

- [调用、任务与错误处理](guides/usage.md)
- [工具清单](reference/tools.md)
- [请求 schema](reference/tool-schemas.json)
- [能力索引](reference/capabilities.md)
- [专题文档](topics/)
- [调用示例](../examples/README.md)

## 使用范围

服务支持顺序与非序列建模、批量光线追迹、像质与波前分析、优化、公差、物理光学传播，以及图像、报告、CAD、Speos 和数值数据导出。每个请求的参数、单位、输出结构和资源条件以请求 schema 及对应专题文档为准。

任务结果包含请求编号、实际设置、模型修订、数据分页入口和输出文件位置。使用结束时调用 `disconnect` 关闭服务创建的 OpticStudio Standalone 实例。

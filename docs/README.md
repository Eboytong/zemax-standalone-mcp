# Zemax Standalone MCP 使用文档

Zemax Standalone MCP 1.4.1 以 Windows x64、Python 3.14 与 Ansys Zemax OpticStudio 2026 R1 为默认环境，提供107项工具操作和146种`run_analysis`请求类型。默认compact目录披露11个入口；显式full目录直接披露107个工具。

## 文档导航

- [调用、任务与错误处理](guides/usage.md)
- [原生启动与环境变量](guides/native-startup.md) · [Windows发行包](guides/windows-distribution.md)
- [能力搜索](guides/capability-search.md) · [候选管理与比较](guides/candidates.md)
- [联合玻璃搜索](guides/joint-glass-search.md) · [评价函数构建](guides/merit-program.md)
- [设计去敏感化](guides/design-desensitization.md) · [逐面能量损耗](guides/sequential-energy-budget.md)
- [工具清单](reference/tools.md)
- [请求 schema](reference/tool-schemas.json)
- [能力索引](reference/capabilities.md)
- [专题文档](topics/)
- [调用示例](../examples/README.md)

## 使用范围

服务支持顺序与非序列建模、批量光线追迹、像质与波前分析、优化、公差、物理光学传播，以及图像、报告、CAD、Speos 和数值数据导出。每个请求的参数、单位、输出结构和资源条件以请求 schema 及对应专题文档为准。

同步工具直接返回结果；长任务返回任务编号，使用 `get_task_status` 查询终态并通过 `get_task_result` 读取数据、实际设置和输出文件。使用结束时调用 `disconnect` 关闭服务创建的 OpticStudio Standalone 实例。

专题中的2024 R2版本、手册页码和实测数值保留其原始证据条件。2026 R1升级前结果见[兼容性记录](compatibility/2026r1/README.md)，当前版本的复测结论随整合与回归更新。

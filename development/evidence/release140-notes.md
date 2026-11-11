# Zemax Standalone MCP 1.4.0

本版提供107个直接工具与146种分析请求，运行于Windows x64、Python 3.14和OpticStudio 2024 R2。

## 工具按需披露

- 默认`full`模式直接提供107个工具。
- 可选`compact`模式提供11个固定的连接、搜索、执行及任务控制入口，按需读取单项能力的精确参数。
- 用`search_capabilities`寻找能力，用`get_capabilities`读取对应工具、分析种类或候选操作的契约，再通过`query_capability`或`execute_capability`调用。
- 两种模式共用原生执行链、参数校验、任务、分页、取消和恢复机制。安装或启动时指定`-ToolMode compact`即可启用。

## Agent自主组合

原生建模、评价函数、优化和公差工具可由Agent自行组合。候选管理、联合材料试验和设计改进流程作为可选快捷调用。

材料试验增加`include_contributions=false`，可在有限共轭、非球面及单波长条件下执行材料替换和原生评价；贡献计算默认保持开启。

## 检查结果

- 全量普通测试3775项通过；另完成最终派发、请求收据及状态定向检查。
- full和compact各完成12个真实stdio与原生场景，12组数值对照通过。
- 独立安装包完成两种模式的接口读取、MTF、光线分页、波前网格和图像导出，以及材料试验原生检查。
- compact初始工具目录为12,862字节，full为1,432,668字节，目录字节量减少99.10%；wavefront单项详情1,145字节。这些指标测量工具目录与契约大小，模型token用量未采集。
- 固定60条能力检索任务通过59条。

安装和调用见仓库README与`docs/guides/capability-search.md`。本页附件为1.4.0 wheel安装包。

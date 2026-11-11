# 按工程需求查找能力

`search_capabilities`在未连接OpticStudio时即可使用。短结果返回能力ID、用途、读写分类和详情入口；参数、单位、前置条件和默认值通过详情按需读取。

```json
{"query":"镀膜反射率透射率吸收率","limit":5,"category":"all"}
```

检索结果中的`detail_request`可直接传给`get_capabilities`：

```json
{"topic":"detail","capability_id":"tool:get_coating_rta"}
```

读取`request_schema`后，连接、打开模型，再调用对应工具。schema使用实际MCP参数形状，例如`update_system_settings`的外层是`settings`，`run_analysis`的外层是`request`。分析能力以`analysis:<kind>`定位，候选操作以`action:manage_candidates:<action>`定位。`include_metadata=true`返回完整元数据；原生执行按当前模型、资源和许可确认。

完整索引使用`get_capabilities(topic="index",start=1,count=100)`分页，编号从1开始。`topic="dependencies"`返回指定能力的条件及修改作用。检索的`category`可选择`tool`或`analysis`，默认`all`。

## 两种披露模式

`full`直接提供107个工具。`compact`提供11个固定入口：连接/断开、状态、能力搜索/详情、任务状态/结果/取消、请求状态，以及`query_capability`、`execute_capability`。全部107项操作和146种分析在compact中仍可通过能力ID调用。

安装时使用`-ToolMode compact`；已有客户端配置的env可设置`ZEMAX_TOOL_MODE=compact`，重启该MCP连接后生效。`start.ps1 -ToolMode compact`也可指定。两种模式使用同一个后台执行所有者。

```json
{"topic":"detail","capability_id":"analysis:wavefront"}
```

取得契约后调用`execute_capability`：

```json
{"capability_id":"analysis:wavefront","arguments":{"request":{"kind":"wavefront","field":1,"wavelength":1,"sampling":"S_64x64"}}}
```

读取系统设置通过`query_capability`：

```json
{"capability_id":"tool:get_system_settings","arguments":{}}
```

query只接受已审查的读取操作；建模、分析、保存和工程流程使用execute。结果保持原工具的响应和任务编号。随后直接调用`get_task_status`、`get_task_result`或`cancel_task`。已知能力ID可直接调用；搜索用于寻找候选，详情用于获取准确参数。

嵌套评价只读取本次分析种类：`get_capabilities(topic="detail",capability_id="tool:run_batch_evaluation",analysis_kinds=["wavefront"])`。候选单操作：`get_capabilities(topic="detail",capability_id="action:manage_candidates:list")`。目录在进程启动时固定，搜索和详情读取保持目录稳定。

## Agent自主组合

Agent可自行选择原生变量、MFE目标、优化算法和评价顺序。候选、换玻璃、去敏感化等工程流程作为可选快捷调用，与底层原生工具并存。材料试验可设`include_contributions=false`，按当前模型运行材料替换和评价；具体设置见[材料试验](../topics/modeling/glass-trials.md)。

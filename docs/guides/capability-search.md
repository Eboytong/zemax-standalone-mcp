# 按工程需求查找能力

连接 OpticStudio 前即可调用 `get_capabilities(topic="overview")`。它返回能力分组、各组数量和代表性能力 ID。`search_capabilities` 根据当前需求查找用途、compact 调用入口、前置条件和预期产物。常见出图能力附最小调用示例，详情提供完整参数、单位和默认值。

```json
{"query":"镀膜反射率透射率吸收率","limit":5,"category":"all"}
```

检索结果中的`detail_request`可直接传给`get_capabilities`：

```json
{"topic":"detail","capability_id":"tool:get_coating_rta"}
```

读取`request_schema`后，连接、打开模型，再调用对应工具。schema使用实际MCP参数形状，例如`update_system_settings`的外层是`settings`，`run_analysis`的外层是`request`。分析能力以`analysis:<kind>`定位，候选操作以`action:manage_candidates:<action>`定位。`include_metadata=true`返回完整元数据；原生执行按当前模型、资源和许可确认。

完整索引使用`get_capabilities(topic="index",start=1,count=100)`分页，编号从1开始。`topic="dependencies"`返回指定能力的条件及修改作用。检索的`category`可选择`tool`、`analysis`或`action`，默认`all`。

## 报告插图

搜索「镜头结构图、MTF 曲线、标准点列图」即可定位布局、FFT MTF、点列分析和图像导出。推荐按如下路线调用。

| 图像 | 调用 | 产物 |
| --- | --- | --- |
| 镜头布局 | `tool:run_layout_export`，传入绝对 `.png` 路径 | OpticStudio 原生 PNG |
| MTF | `tool:run_fft_mtf`，任务完成后调用 `tool:export_analysis_image`，取 `source="data_plot"` | 由原生 FFT 曲线绘制的 PNG，`item` 选择曲线组 |
| 点列 | `tool:run_batch_ray_trace`，向 `rays` 传入归一化视场、光瞳坐标和波长号。以默认目标像面追迹后导出 `source="data_plot"` | 各视场的未渐晕像面交点图，按 `(hx,hy)` 排序选择 `item` |

标准 `tool:run_spot_analysis` 提供原生 RMS、GEO、参考点和分析文本。Standalone 模式下这些统计量和批量追迹点列通过各自的任务获取。`get_task_result` 的 `image_exports` 列出可用来源、已有原生图路径、可绘制项数及相应替代入口。`source="native"` 用于复制已保存的原生图。如果任务无原生图，返回 `UNSUPPORTED_NATIVE_IMAGE` 及可用路径。

## 工程表达与复合需求

检索在本地按能力名称、别名和说明评分。精确能力ID和名称优先；工程概念高于“镜头、计算、分析”等通用词。“加工误差、合格率”扩展为公差、蒙特卡洛和良率，“清晰程度”扩展为MTF和光斑，“光电接收面”扩展为探测器。

“读取波前再保存候选设计”会拆成两个意图，分别检索后合并去重。在`limit`允许时，每个意图优先保留一个候选，再按相关度补齐。`category`同时过滤各个意图；`total_matches`表示过滤后的候选并集数量。

结果按需增加三个字段：`intents`给出子需求及其候选能力ID，`expanded_terms`列出使用的工程扩展词，`retry_requests`最多提供两组可直接传给`search_capabilities`的参数。普通单意图、无扩展的检索沿用简短结果结构。

Agent先检查候选用途、前置条件和副作用，再读取详情与参数契约。候选不合适时，可采用重检参数或工程术语改写，最多重检一轮；仍有歧义时向用户确认需求。检索返回能力候选，Agent根据模型状态、任务终态和用户目标决定执行顺序。例如先等待波前任务结束并读取结果，再保存候选设计。

## 两种披露模式

默认`compact`提供11个固定入口：连接/断开、状态、能力搜索/详情、任务状态/结果/取消、请求状态，以及`query_capability`、`execute_capability`。显式`full`直接提供107个工具。全部107项操作和146种分析在compact中仍可通过能力ID调用。

安装和启动默认使用compact。需要full时使用`install.ps1 -ToolMode full`、`start.ps1 -ToolMode full`或`start-2026r1.ps1 -ToolMode full`。模式优先级为显式参数、已有`ZEMAX_TOOL_MODE`环境值、默认compact。已有客户端配置可在env中设置`ZEMAX_TOOL_MODE=full`，重启连接后生效。两种模式使用同一个后台执行所有者。

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

# 任务追溯与历史结果

## 工具与编号

| 工具 | 请求 | 返回 |
| --- | --- | --- |
| `list_task_history` | 可选 `session_id`、`request_id`、`kind`、`state`，以及 `start=0,count=50` | 当前工作进程及已保存历史任务、来源、执行状态、结果位置和读取错误。 |
| `get_historical_result` | 必填 `session_id` 与 `task_id`；可提供行、曲线或网格区域参数 | 指定历史结果的分页内容、版本、来源与计算上下文。 |
| `get_request_status` | 必填 `request_id` | 请求回执、原始参数、错误、会话、修订、任务编号及产物引用。 |

会话和任务编号为 32 位小写十六进制。MCP 桥接层生成唯一请求编号；正常响应在 `context.request_id` 返回，等待超时时在 `error.details.request_id` 返回。

## 请求状态

工作进程在分派前写入 `dispatching` 回执，命令返回后写入 `returned`。异步任务使用 `task_id` 查询最终状态。回执保存 `ok`、原始错误、任务编号、模型修订和产物引用。

回执位于配置输出目录的 `_requests/<request_id>.json`。当前进程尚未写出的回执返回 `queued_or_dispatching`；来自已退出工作进程的未终态记录返回 `unknown_after_worker_exit`。

## 结果版本与分页

新结果包含 `result_schema_version=1`；缺少该字段的既有 JSON 按版本 0 读取。历史结果位于 `ZEMAX_OUTPUT_DIR` 配置的输出目录；需要读取其他目录时显式设置该输出根目录。

- 行数据使用 `start/count`，返回 `total/next_start`。
- 曲线指定 `series` 后按点使用 `start/count`，`series` 是结果中的 0 基位置。
- 网格使用 `grid/x_start/y_start/width/height`，每次最多读取 10,000 个值。
- 大型散点和曲线通过结果 `artifacts` 读取。

读取历史结果不会创建 OpticStudio 实例。损坏或不支持的记录在结果的 `errors` 字段中返回。

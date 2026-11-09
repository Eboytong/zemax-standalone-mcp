# 调用、状态与故障处理

## 首次调用

在 MCP 客户端依次调用下列工具，`arguments` 为每次调用的参数；将文件路径替换为本机绝对路径：

```json
{"tool":"connect","arguments":{}}
{"tool":"open_lens","arguments":{"path":"C:/optics/example.zmx"}}
{"tool":"get_system_summary","arguments":{}}
{"tool":"run_analysis","arguments":{"request":{"kind":"relative_illumination"}}}
```

从 `run_analysis` 的响应取得 `task_id`，代入下列请求并轮询状态；任务成功后读取结果，结束时断开：

```json
{"tool":"get_task_status","arguments":{"task_id":"<task_id>"}}
{"tool":"get_task_result","arguments":{"task_id":"<task_id>","start":0,"count":100}}
{"tool":"disconnect","arguments":{}}
```

每一行表示一次独立工具调用；实际客户端以其自身的工具调用界面提交。结果数据量较大时，根据 `next_start` 继续读取。

## 响应与编号

工具响应包含 `ok`、`data`、`error`、`warnings`、`context` 和 `artifacts`。先检查 `ok`；长任务还应读取最终 `state` 和逐行失败状态。

曲面从 0 开始，0 为物面；对象、视场、波长、配置及评价函数操作数从 1 开始。分析选择全部视场和多色组合时使用该工具定义的 0 选项。文件路径使用本机绝对路径。

波长以微米输入，550 nm 为 `0.55`。几何量使用当前镜头单位；无限半径使用字符串 `Infinity`。`CyclesPerMillimeter` 表示像空间频率，`CyclesPerMilliradian` 表示物空间角频率。

`context` 包含会话、模型修订、来源/工作文件、软件版本、配置和单位。任务结果中的 `data.context` 表示计算时模型。

## 任务与分页

`run_*` 返回任务编号。使用 `get_task_status` 查询 `running`、`succeeded`、`failed`、`cancelling` 或 `cancelled`；取消请求后查询至最终状态。

使用 `get_task_result` 读取曲线、行数据或网格。响应提供 `total`、`next_start` 或网格区域的后续位置；`inline_data_truncated=true` 时从 `artifacts` 读取完整文件。

扫描和批量评估恢复起始基线；优化保留最终设计并提供起始检查点。复合任务完成后，读取 `summary.failed`、逐行 `state` 和 `restoration`。

## 模型与文件

服务加载镜头后保存内部工作副本，关键修改前建立检查点。`save_lens_as` 导出设计并继续使用内部工作副本；默认禁止覆盖，覆盖已有文件时传入 `overwrite=true`。

影响 `solve` 或 `pickup` 的修改须显式允许替换。部分修改失败时读取当前值或从检查点恢复。`requires_reconnect=true` 时断开、重连后继续操作。输入模型与官方样例保持只读。

## 常见错误

| 错误 | 处理 |
| --- | --- |
| `NOT_CONNECTED` / `INSTALL_NOT_FOUND` | 核对安装目录并连接后台实例。 |
| `INVALID_LICENSE` | 核对本机许可与客户端环境值。 |
| `SOLVE_PROTECTED` | 读取原关系，明确是否允许替换。 |
| `SETTING_REJECTED` / `SOLVE_UPDATE_FAILED` | 查看请求值、实际值、字段和已完成项。 |
| `UNIT_MISMATCH` | 核对系统和分析的单位。 |
| `SYSTEM_BUSY` / `TASK_NOT_FINISHED` | 查询当前任务，必要时请求取消。 |
| `OUTPUT_EXISTS` | 使用新路径，或显式允许覆盖。 |
| `LOAD_FAILED` | 核对路径与文件，并重新加载模型。 |
| `TASK_START_FAILED` | 使用错误中的 `task_id` 查询任务和关闭状态。 |
| `REQUEST_TIMEOUT` | 用 `get_status` 与 `request_id` 查询执行状态。 |
| `NATIVE_ERROR` / `PARTIAL_UPDATE` | 查看 `cause`、修订、检查点及 `partial_changes_possible`。 |
| `RECONNECT_REQUIRED` / `CLEANUP_FAILED` | 断开后重新连接。 |
| `RESULT_UNAVAILABLE` | 核对结果文件位置与访问权限。 |

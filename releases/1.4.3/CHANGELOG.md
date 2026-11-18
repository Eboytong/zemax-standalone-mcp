# Zemax Standalone MCP 1.4.3

## 结果与产物

- `outcome.execution_state` 记录执行终态或运行状态；`coverage` 独立记录覆盖状态及计划、成功、失败、跳过和待处理数量。批处理可以同时返回 `succeeded` 与 `incomplete`，失败原因保存在对应子项。中止时，`skip_reason` 标识跳过剩余项目的原因。单项任务的计数为 `null`。
- `outcome.restoration` 单独记录模型恢复状态、检查点和错误；`resource_release` 记录原生关闭状态。资源释放或模型恢复失败时停止后续批处理。应用可继续读取原有 `state` 和 `completed`。
- 曲线和网格采用 `axes`，`provenance` 提供来源任务、模型修订、计算来源和已记录的实际设置。新 `series_csv` 每行给出 `x_label`、`x_unit`、`x_value`、`y_label`、`y_unit`、`y_value`。旧 CSV 保留原列结构。历史数据中未记录的元数据为 `null`，CSV 对应单元格为空。

## 请求恢复

compact 和 full 都接受可选的请求编号（32 位小写十六进制），例如：

```json
{
  "capability_id": "tool:update_system_settings",
  "arguments": {"settings": {"title": "Working copy"}},
  "request_id": "3fb551140fff473bb9a693b4eabde278"
}
```

在相同 `ZEMAX_OUTPUT_DIR` 下，通过 `get_request_status` 查询该编号。`returned` 表示请求已经返回；如收到 `task_id`，用任务查询确认实际计算结果。`queued_or_dispatching` 和 `dispatching` 表示仍需等待。`unknown_after_worker_exit` 表示应先核对模型或任务历史；相同编号只返回回执，不会再次派发。`not_registered` 表示尚无持久回执，可以使用相同编号重试。相同编号及同一调用返回原结果或当前回执；参数冲突返回 `REQUEST_ID_CONFLICT`。

## 运行条件

能力搜索与 `get_capabilities(topic="dependencies")` 共用 `requirements`、`produces` 和 `readiness`。可向详情传入目标工具的 `arguments`。`blocked` 给出已知缺项及可用的下一步；`unknown` 标记尚未观测、缺少参数或未纳入首批预检的能力。`ready` 表示已声明的前置条件通过，原生运行结果通过任务接口读取。`get_status` 离线可读版本、工具模式和能力索引版本。

## 发行验证

- 离线测试：3,877 项通过，13 项跳过。
- 已安装 wheel：compact（11 个入口）和 full（108 个入口）通过工具枚举、回执恢复和旧结果读取检查。
- OpticStudio 2026 R1：3 项原生集成测试通过，覆盖工作副本建模、顺序分析、非序列追迹、批处理部分失败和报告导出。

# 连接恢复

当响应包含 `requires_reconnect=true`、`RECONNECT_REQUIRED` 或 `CLEANUP_FAILED` 时，调用 `disconnect`，等待任务终态后重新调用 `connect`。重新连接后读取 `get_system_summary`、`get_system_settings` 和目标资源，确认当前模型与配置。

修改类任务使用工作副本和检查点。出现 `PARTIAL_UPDATE` 时，响应中的 `partial_changes_possible`、`completed_items` 和检查点信息用于决定读取当前值或恢复模型。

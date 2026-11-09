# 系统检查

调用 `run_analysis`，请求 `{"request":{"kind":"system_check"}}`，生成 OpticStudio 的 System Check 报告。

结果保留原生 UTF-16 文本及逐行 `rows` 数据；行号从 1 开始。使用 `get_task_result` 的 `start/count` 读取分页结果。报告中的配置范围、警告和错误保持原生表述。

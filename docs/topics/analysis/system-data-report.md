# 系统数据报告

`run_analysis` 接受 `{"request":{"kind":"system_data"}}`。本机 SystemData 只有 AS_Default 基础设置，没有业务设置参数。通过已有 `update_system_settings` 修改源模型，再生成报告。

保留原生 UTF-16 文本、标题、消息、模型修订、版本及许可。`rows` 为一基行号，`get_task_result` 使用零起始 `start/count` 分页。原生数值保留显示精度和单位，详细设置仍从 `get_system_settings` 读取。


环境温度或压强写入后检查实际采用；需要启用环境折射率修正的模型可同时传入 `adjust_index_to_environment=true`，该开关先于从属数值写入。原先静默忽略的值现在返回SETTING_REJECTED及请求/实际值。

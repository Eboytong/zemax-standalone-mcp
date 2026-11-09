# 光学处方文件比较

`run_analysis.request.kind=file_comparator` 调用本机 `FileComparatorSettings`。`file1/file2` 使用已有 `.zos/.zmx` 的绝对路径；`file1_configuration/file2_configuration` 是可选的1起始配置编号，省略时关闭对应原生 SpecifyConfig。显式编号在独立系统副本中检查实际配置总数，检查后关闭副本。

15项 `include_*` 比较段落默认全部开启，`show_differences_only` 默认 true。具体字段见 tool-schemas.json 的 FileComparator。所有请求设置逐项写入并在最终组合回读，任务 settings 保存原生值和配置预检结果。

结果保留 UTF-16 原生报告文件，`rows` 为 `{line,text}`，line 从1开始，保留空行、原生颜色和段落标记。通过 `get_task_result(task_id,start,count)` 分页，start 从0开始。光学数值单位和报告精度由原生段落给出；文本行可用现有报告链路读取。此分析输出文本。

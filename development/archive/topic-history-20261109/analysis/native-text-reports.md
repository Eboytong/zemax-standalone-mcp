# 原生处方与曲面文本报告

`run_analysis` 增加两个默认范围的文本报告入口：

```json
{"request":{"kind":"prescription_data"}}
```

```json
{"request":{"kind":"surface_data"}}
```

返回任务后通过 `get_task_status` 等待终态，再用 `get_task_result` 读取。处方报告包含章节、原始行和文件/标题/日期；曲面报告包含报告实际面号、镜头单位、材料、折射率行及原生表面光焦块。`lines` 保留原文，`native_text` 指向原始导出文件；任务设置记录原生默认设置的实际回读。

省略处方 `sections` 时保留默认完整报告。曲面报告接受 `kind`，实际面号来自报告标题，并与表面光焦块面号核对。默认结果的 `selection_support=default_only`、`acceptance_scope=default_report_only`。

处方报告支持从原生导出文本中选择章节：

```json
{"request":{"kind":"prescription_data","sections":["general_data","index_data","files_used"]}}
```

`sections` 为1至15个不同章节标识。可选值为 `general_data`、`surface_data`、`surface_detail`、`edge_thickness`、`multi_config_data`、`solves_variables`、`index_data`、`thermal_expansion_data`、`global_vertex`、`center_of_curvature`、`element_volume`、`f_numbers`、`cardinal_points`、`pop_settings`、`files_used`。

选择结果按原文顺序输出，包含文档标题/文件/日期及所选章节的完整原生行。`selection` 记录请求与实际章节、来源 `native_report_section_selection`、原生设置保持默认和原文一基行号。`selected_sections` 包含章节行区间；`selected_text` 是UTF-8文本产物；`get_task_result` 的 `rows` 支持 `start/count` 分页。完整原文仍在 `native_text` 和 `lines` 中，完整章节仍在 `sections` 中。

所选章节缺失或重复时返回 `INVALID_RESULT_DATA`，附请求/现有/缺失或歧义章节、原生消息与完整报告位置。例如单配置模型可能没有 `multi_config_data`。写出失败返回 `EXPORT_FAILED`。

当前选择发生在原生文本导出之后，`acceptance_scope=exported_report_sections`。本机设置对象为 `AS_Default`，原生设置页章节选择和曲面面号选择的正式写入/回读仍有缺口，`selection_scope` 单独记录该状态。章节输出与默认报告真实stdio、分页、失败后复用、重载及关闭证据见[验收记录](../../../development/evidence/NS-04/prescription-sections-20261109.md)。

元件报告可在每个光焦块中列出前后两面。`surface_power_components`保留各块全部曲面行，`surface_power`选取标题对应面的值；块内存在其他面号时仍保留其数据。光焦块缺少标题对应面时返回带原始文本和部分解析结果的身份错误。

无文本、读取/解码失败、报告身份错误及面号冲突分别报告来源并保留原生消息和文件位置。执行、取消、任务文件和原生对象关闭沿用现有任务机制。完整专题验收状态见 `development` 中 D008 的对应条目。

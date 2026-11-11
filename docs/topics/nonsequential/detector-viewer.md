# Detector Viewer

通过 `run_analysis` 查看当前非顺序探测器累积数据，或以 ZRD 为来源运行原生 Detector Viewer。需要先连接并打开非顺序模型，完成追迹。

```json
{"request":{"kind":"detector_viewer","source":"current_detector","detector":2,"show_as":"FalseColor","data_type":"IncoherentIrradiance","scale":"Linear","smoothing":0}}
```

ZRD 来源设置 `source="zrd"`、`path`，可附原生 `filter`；当前累积数据来源会清空原生数据库与筛选条件。探测器编号从1开始，须为当前模型中的有效探测器。

`scale` 支持 Linear、Normalized、Log_Minus_5、Log_Minus_10、Log_Minus_15；`smoothing` 为0—10。`show_as`、`data_type` 的可用项取决于探测器类型。原生枚举存在同值别名，实际设置按枚举值核对。矩形截面可采用 `CrossSection_Row` / `CrossSection_Column` 和 `row_col`。

调用返回任务编号，通过 `get_task_status` 和 `get_task_result` 读取终态及结果。网格按 `values[y][x]` 返回，支持区域分页；矩形空间网格附像素中心 `x_coordinates/y_coordinates` 和镜头单位，`native_axes` 保留原生边缘坐标。角度探测器保留其原生轴和单位。结果中的 `detector_viewer` 标记来源、显示设置及探测器类型。

使用 `export_analysis_image` 导出结果图。Scale 和 Smoothing 为原生显示设置；原始辐射量通过 `get_detector_data` 读取。无累积数据时可取得全零网格；原生未生成文本文件的情况记录在 `native_text_exported/native_export_error`，已有结构化网格继续返回。

旧 `run_zrd_replay` 保持可用，新增可选显示设置共享同一写入与回读路径。

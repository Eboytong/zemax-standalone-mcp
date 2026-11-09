# 扩展衍射与部分相干图像

当前源码通过run_analysis提供两个原生图像入口，使用已确认的CFG键和报告回读：

```json
{"request":{"kind":"extended_diffraction_image","field":2,"wavelength":1,"source_width":0.1,"display_width":0.2}}
```

```json
{"request":{"kind":"partially_coherent_image","field":2,"wavelength":1}}
```

两项均使用当前原生分析中的图像，input_mode固定为native_current_input。结果input_selection.identity_verified=false说明尚未确认所选输入文件身份。扩展衍射的source_width和display_width为毫米，须显式传入；部分相干入口采用当前原生相干和采样条件，结果image_header记录实际模式及尺寸。

当前报告回读适用于毫米镜头单位和唯一的非负Y方向角度视场。请求波长为明确单色编号。设置键拒绝、报告未采用、尺寸冲突和计算错误分别返回原始来源。

结果返回原生全精度强度网格、文本报告及实际设置。网格为values[y][x]；文本行序与原生数组的Y方向相反，适配器检查两者数值对应。网格分页和绘图使用像素索引；native_axes保留原生轴信息，physical_axes_verified=false。

通过get_task_result的grid/x_start/y_start/width/height读取区域，export_analysis_image导出数据绘图。任务查询、取消和资源关闭沿用共用链路。

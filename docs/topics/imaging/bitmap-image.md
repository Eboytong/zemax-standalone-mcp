# 几何位图图像

`run_analysis`的`geometric_bitmap_image`使用本机GeometricBitmapImageAnalysis、正式GBM配置和原生报告回读。输入为BMP/JPG/PNG绝对路径或Images资源名，当前报告适配使用毫米镜头单位。

```json
{"request":{"kind":"geometric_bitmap_image","input_file":"C:/path/source.bmp","field_size":1,"rotation":0,"rays_per_pixel":1000,"x_pixels":17,"y_pixels":11,"x_pixel_size":0.1,"y_pixel_size":0.1}}
```

`grids[0..2]`保持RGB显示网格，`value_unit=8-bit display RGB`。报告含“正常化强度值”时，新增`grids[3]`，channel为I、quantity为native_normalized_intensity。该网格直接读取原生浮点表，保留报告精度。`normalized_intensity_available`标记实际存在性。

四个网格均为`values[y][x]`、X向右/Y向上、像素中心0.5起。通过`get_task_result`传`grid=3`和区域参数分页；通过`export_analysis_image`传`item=3`导出强度图。归一化强度与RGB分别返回，原生BMP继续作为native_image保存。

`native_efficiency`记录报告百分数、来源和`independently_verified=false`。原生受控用例存在大于100%的报告值，完整通量归一化仍待定位。物理像元尺寸通过physical_pixel_sizes返回；物理原点仍为physical_origin_verified=false。

当前控制已确认视场对称性影响：4×4白图轴上400%、仅Y偏移200%、X非零100%；原值保留，具体输入与结果见强度证据。完整效率验收继续覆盖源尺寸及受控遮挡。

非零X视场后续六种奇偶尺寸均为100%；半径0.5/0.25 mm圆孔报告24.635%/6.269%，通过25%/6.25%均匀入口瞳面积参考。适用条件和采样门槛见证据；对称计数的正式定义仍待确认。

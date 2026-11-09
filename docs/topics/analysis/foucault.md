# Foucault Analysis

`run_analysis` accepts `kind="foucault"` for the native Foucault analysis. The typed request covers field, wavelength, pupil sampling, intensity scale, display mode, knife direction, data selection, section row/column, polarization, image position/decenter, and X/Y scale. The adapter writes and reads back these settings before standard native execution and result collection.

```json
{
  "request": {
    "kind": "foucault",
    "field": 1,
    "wavelength": 1,
    "sampling": "S_64x64",
    "intensity_scale": "Linear",
    "show_as": "GreyScale",
    "knife": "Horiz_Above",
    "data": "Computed",
    "row_column": 32
  }
}
```





新增可选 `source`，传入绝对BMP路径；`Reference` 和 `Difference` 必须提供。路径存在性及BMP扩展名在创建原生分析前检查；设置写入回读。受控黑白半平面BMP的64×64参考网格逐点一致。`y_position` 单位为微米，刀口方向选择其X/Y物理轴；参考偏心以图像宽/高为单位，缩放为参考与计算像素尺寸之比。网格保留原生轴，结果附条件和无量纲强度说明；原生显示坐标不作为追迹入口瞳坐标使用。

```json
{"request":{"kind":"foucault","data":"Reference","source":"C:/data/reference.bmp"}}
```

原生结果可能同时包含一条占位曲线和网格。图像导出 `item` 先编号所有曲线，再编号网格；例如一条曲线加一个网格时传 `item=1` 导出shadowgram。

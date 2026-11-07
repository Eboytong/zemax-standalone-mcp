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

The installed 2024 R2 API reflection identifies `IAS_Foucault` and its enum-backed display, knife, data and intensity-scale settings. The string properties `Source` and `SaveBMP` are recorded in the reflection; exposing them still requires confirmation of their runtime path semantics. See `.local/evidence/development/BASE-01/probe/api-interfaces.json` and the native execution evidence below.

2026-11-06：Cooke 原生探查取得一组曲线和一组网格，原生 `SeriesLabels=null`。读取器现使用 `column_1` 等列标识并记录 `labels_source`，同时检查列数和每行长度，保留原生轴及单位。设置、执行与结果读取回归已通过，证据见 `.local/evidence/development/CV-01/outlets265/summary.json` 和 `.local/evidence/development/BASE-04/native266-results.xml`。完整条目仍待受控数值参考、刀口方向及生命周期验收；Source/SaveBMP 路径语义继续单列待探查。


2026-11-06 执行300验收完成：受控抛物面镜的四方向刀口与独立标量FFT/刀口掩码/逆FFT逐像素对照，最大绝对差1.2677e-9，容差1e-7+1e-7×参考值；±1000µm分别验证全闭和全开。零刀口的中央频率样本取半权，128×128补零后裁剪64×64，并按裁剪最大强度归一化。

新增可选 `source`，传入绝对BMP路径；`Reference` 和 `Difference` 必须提供。路径存在性及BMP扩展名在创建原生分析前检查；设置写入回读。受控黑白半平面BMP的64×64参考网格逐点一致。`y_position` 单位为微米，刀口方向选择其X/Y物理轴；参考偏心以图像宽/高为单位，缩放为参考与计算像素尺寸之比。网格保留原生轴，结果附条件和无量纲强度说明；原生显示坐标不作为追迹入口瞳坐标使用。

```json
{"request":{"kind":"foucault","data":"Reference","source":"C:/data/reference.bmp"}}
```

原生结果可能同时包含一条占位曲线和网格。图像导出 `item` 先编号所有曲线，再编号网格；例如一条曲线加一个网格时传 `item=1` 导出shadowgram。

正式 `SaveBMP` 在Computed、Reference、Difference三种模式均写入回读成功，执行后均无文件，原生消息为空；暂待可工作的正式导出触发方式或修正版本。公共 `export_analysis_image` 可导出有效PNG。探查和原始输出见 `.local/evidence/development/CV-01/foucault297-files/probe.json`。

相关普通66通过；原生数值、选择/偏振、BMP、分页、PNG查看、越界/缺资源、取消/复用、模型/solve/配置/MFE保持、保存重载和关闭完成。原始公共Source路径NameError和修复后报告分别保留。完整汇总：`.local/evidence/development/CV-01/acceptance300.json`。B004计入1项，累计4/10。

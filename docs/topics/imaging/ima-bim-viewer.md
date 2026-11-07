# IMA/BIM 文件查看

`run_analysis` 的 `ima_bim_viewer` 提供两种来源：

```json
{"kind":"ima_bim_viewer","input_file":"sample.IMA","map_index":2,"method":"native_source_bitmap"}
```

文件必须来自 `get_system_resources(kind="image_simulation_files")` 返回的 Images 目录。`map_index` 从 1 开始。文本 IMA 按手册的 N 行数字格式读取；二进制 IMA 读取 int16 头部、多个 uint8 图层；BIM 读取 int32 尺寸和 float64 像素。结果坐标使用 `values[y][x]`，像素原点定义为左下角；IMA 的原生顶行顺序在读取时反转。每个结果包含原始强度网格、以输入峰值归一化的网格，以及逐像素 `rows`。

`method=file` 只读取并归一化文件，保留双精度 BIM 值。`method=native_source_bitmap` 还调用 ImageSimulation 的 `SourceBitmap`，回读 `InputFile` 和 `ShowAs`，并保留原生 RGB 8 位显示网格。三图层二进制 IMA 的图层分别对应 R/G/B；系统波长选择不会改变这一映射。其他图层数按所选图层转换为临时 BIM 后交给原生显示，结果记录转换来源和清理状态。

零输入返回峰值 0 和全零归一化网格。格式、尺寸、图层编号、非有限或负强度在启动原生分析前拒绝。结果支持 `rows` 与网格区域分页、图像导出、取消后复用和保存重载。

验收证据：`.local/evidence/development/CV-02/native451-binary-source.xml`、`native452-normalization.xml`、`native454-viewer.xml`、`native455-viewer-final.xml`；普通检查见 `ordinary455-viewer-final.xml`。

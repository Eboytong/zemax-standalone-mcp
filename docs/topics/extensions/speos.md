# Speos 导出



`run_speos_export` 使用本机正式 LensSystem / Whitebox 工厂，在独立系统副本中执行。任务查询、取消及结果文件沿用现有工具。源系统保留；工具先于副本关闭，关闭失败要求重连。

```json
{"request":{"kind":"lens_system","path":"C:\\ZemaxOutput\\lens.optdistortion","sensor_width":10,"sensor_height":8,"configuration":0,"sampling":"S_64x64","x_sampling":11,"y_sampling":11}}
```

LensSystem 需要顺序系统。传感器宽高使用镜头单位，必须为有限正数；配置0表示当前配置。默认二维采样11×11；`assume_radial_symmetry=true` 使用 `sample_points`（默认21），两类采样参数互斥。采样枚举覆盖原生32×32至16384×16384。`skip_system_reversal` 默认false。输出须为绝对 `.optdistortion` 路径；覆盖已有文件需要 `overwrite=true`。所有可写设置及最终配置逐项回读，返回原生FileFormatVersion。

```json
{"request":{"kind":"whitebox","output_directory":"C:\\ZemaxOutput\\whitebox_new"}}
```

Whitebox正式接口没有可写属性。请求使用尚不存在的绝对目录，副本保存为该目录内input.zos；项目资源随工作副本准备。结果保留原生只读OutputFilename、ErrorCode及实际文件。输出文件名与格式由原生接口决定；文件落在其他目录或不存在时返回具体错误。目录中同时保留工作输入和原生支持文件，接收端实际导入状态沿历史记录保留。

结果包含实际设置、源系统元数据、输出文件、工具/副本关闭确认和接收端状态。源状态自动比较范围为系统编号、文件名、模式、配置、单位及行数；完整属性与solve保留由原生用例进一步检查。失败保留原始错误，设置失败也释放已创建资源。取消使用原生CanCancel/Cancel及任务终态机制。

## 验收状态


历史接收端验收状态为blocked，现已移出当前计划：本机v242目录及HKLM卸载记录未发现可运行的Speos接收端。当时缺少明确版本的接收端及产物导入的单位、几何和资源引用证据。原生Whitebox文件命名与支持文件组织已由上述运行记录确认。

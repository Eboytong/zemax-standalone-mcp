# 成像与扩展源


## 位图/道路向导及成像运行时验收

完成NSCBitmapWizard和NSCRoadwayLightingWizard两项：实际Apply、评价函数输出及保存重载通过；位图使用原生资源列表中的square.bmp。





| kind | 本批设置与条件 |
| --- | --- |
| image_simulation | 必填 input_file；视场1；RGB波长或1+2+3或明确编号；物方全Y高 field_height；翻转/90度旋转；过采样/保护带；瞳及像面采样；像差模式；PSF场点数5×5；固定孔径、相对照度、偏振；像元与像素数量0采用原生自动值 |
| geometric_image | 必填 input_file；视场1、波长1；物方全X宽 field_size；image_size为接收区域大小，SpotDiagram下为标尺；光线数量约为rays_x1000×1000；Uniform/Lambertian、NA、总功率、奇偶、旋转、显示及像素参数 |
| geometric_bitmap_image | 必填BMP/JPG/PNG的input_file；正式GBM配置：field_size为全Y高、rotation为度、rays_per_pixel为每源像素每颜色光线数，独立X/Y像素及像素大小；RGB文本读取，详见geometric-bitmap.md |
| fft_line_edge_spread | 视场1、波长1、64×64采样；Line/Edge；完整原生X/Y强度、对数、相位及实虚部类型；相干PSF、偏振、显示尺度 |
| geometric_line_edge_spread | 视场1、波长1、像面、64×64采样；LineEdge/Line/Edge、偏振；radius_maximum为微米，0自动 |
| extended_source_encircled_energy | 必填 image_name；视场1、波长1、像面、Centroid；Encircled/X_Only/Y_Only/Ensquared/X_Distrib/Y_Distrib；物方全X宽、旋转、最大距离、光线数量、偏振、渐晕；衍射极限修正适用于Encircled |

本批支持有焦顺序系统。输入通过 get_system_resources 的 image_simulation_files 或 geometric_image_files 发现；结果含原生 ImagesDir。仿真支持原生列表中的 BMP/JPG/PNG/IMA/BIM，几何图像与扩展源选择 IMA/BIM。文件名按原生列表精确匹配（忽略大小写），并记录实际名称。几何行列编号0调用 UseColumnRowCenter，保存实际编号；显式编号适用于CrossX/CrossY。

所有可写设置在写入后及最终组合时检查；枚举使用原生值相等比较。字段、波长和目标曲面最终回读。分析以 settings-first 创建，任务所有者执行Apply、轮询、取消及关闭；设置失败也关闭分析。资源查询创建的分析在finally关闭，关闭失败返回RESOURCE_CLOSE_FAILED并沿用重连状态。既有模型修订及配置快照随任务保存。

结果保留原生标量/RGB网格、曲线及散点。RGB拆为R/G/B三个通道，保留通道和原生数据编号；单通道可复用现有绘图及报告。网格为values[y][x]，非方形数组按Nx/Ny识别转置，方形方向待非对称原生图验证。轴参数、标签、原生头和消息原样记录，光强单位采用原生ValueLabel。无效值为null并计数；散点全量含无效状态保存在rows，绘图使用有效点。单数据集结构化读取上限400万点/单元，超限返回具体错误。

当前任务和历史结果均支持series分页；网格使用既有grid区域分页，散点明细使用rows分页。GetTextFile返回false或抛异常时保留错误并继续读取结构化数据；空结果的错误附原生头、消息和已有文本路径。几何成像的持久输出设置清空；ImageSimulation改为本任务目录下唯一的原生OutputFile BMP，写入及回读后执行。无原生数组时读取该文件的R/G/B显示像素，保留原生文件并接入任务分页和导出。

Image Simulation按原生定义将输出峰值归一化到输入峰值；RGB固定波长为0.606/0.535/0.465 µm，1+2+3对应R=3/G=2/B=1。原生衍射模式在严重像差下可能转几何PSF，消息随结果保留。实像高视场在该分析中按原生近轴像高处理。几何图像的TotalWatts为入瞳源功率，实际网格数值保留原生定义。

请求例子在 examples/requests/imaging023_requests.json。tests/resources/imaging023 提供本项目生成的33×33点源、条纹和阶跃边缘ASCII IMA；格式来自本机2024 R2用户手册印刷页830。原生用例通过ImagesDir复制唯一测试文件，结束删除该文件，准备于tests/native/test_imaging_live.py。9个用例尚未执行；数值参考仍需补齐PSF/LSF/ESF、归一化、方向和图像功率比较，当前用例提供资源采用及结果读取基础。


















`extended_source_encircled_energy` 已完成六种数据类型的原生执行与数值验收。`field_size` 为输入方形图像的完整宽度，角度视场使用degrees，高度视场使用当前镜头单位；`maximum_distance` 和曲线位置使用微米。光线数为约 `rays_x1000 × 1000`，实际数量随像素与波长权重分配；当前正式结果未给出实际追迹总数，结果中保留该状态。

```json
{"request":{"kind":"extended_source_encircled_energy","image_name":"point.IMA","field":1,"wavelength":1,"data_type":"Encircled","reference":"ChiefRay","field_size":0.02,"rays_x1000":100,"maximum_distance":20}}
```

先通过 `get_system_resources(request={"kind":"geometric_image_files"})` 选择已存在的IMA/BIM文件。设置和最终资源名称沿用原生写入回读；失败信息保留原生工件、消息及文本路径。

Encircled为圆形区域能量分数，X_Only/Y_Only为指定半宽的无限长狭缝，Ensquared为方形区域能量分数。X_Distrib/Y_Distrib返回原生峰值归一化的相对分布。曲线的 `labels`、`value_units` 和 `extended_source_conditions` 明确其身份、单位与来源，原生标签和横轴保留在 `native_labels`、`native_x_label`、`native_x`。

本机2024 R2的累计曲线有396个等距显示样本，对应100个原始样本和4倍显示细分。受控方形源、点源与Airy参考验证：累计值的围合边界比原生报告位置落后一个原始间隔。结果保留原生 `x/y`，在可识别的采样形态下附 `native_binning.interval_um` 和 `enclosure_radius_um=max(0,x-interval_um)`，并标明计算解释与证据来源。它们随series分页同步切片。其他形态保留原生坐标。衍射修正采用原生无遮拦圆瞳近似；验收使用匹配围合边界的独立Bessel积分。

均匀257×257方形源的四类区域积分、两类分布的累计积分、16/20/40µm范围、近点源极限、自动范围和衍射修正均通过预设0.01绝对容差；最大区域能量差0.006882，点源/标准几何差0.000895，Airy差0.000574。非对称条带旋转90度交换X/Y结果；单/多色、ChiefRay/Centroid/Vertex、视场/偏振/渐晕设置、分页/PNG查看、资源缺失/越界/取消复用、保存重载及曲面/solve/配置/MFE保持、正常关闭和自有资源清理均已执行。






几何位图现返回RGB及原生正常化强度网格，支持强度区域分页和PNG；原生效率百分数保留实际值并标记独立定义待验。调用与结果字段见[几何位图](bitmap-image.md)。

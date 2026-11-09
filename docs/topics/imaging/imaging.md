# 成像与扩展源

2026-11-09：几何位图已通过正式GBM配置和RGB文本接入，受控输入、旋转、17×11通道网格、分页与PNG已有真实stdio证据。当前请求及剩余范围见[几何位图](geometric-bitmap.md)。以下发行验收记录保留其历史范围。

## 0.1.48 位图/道路向导及成像运行时验收

完成NSCBitmapWizard和NSCRoadwayLightingWizard两项：实际Apply、评价函数输出及保存重载通过；位图使用原生资源列表中的square.bmp。GeometricImage点源/条纹/边缘已完成设置采用、结果读取、分页及图像导出，独立数值参考仍待补，保持implemented。

ImageSimulation用受控IMA及BMP均未取得可读取结果，当前GetTextFile返回false；下一步探查正式输出图像和结果契约。GeometricBitmapImageAnalysis实际GetSettings为AS_Default且无GetFileNames；已返回含实际类型和缺失方法的UNSUPPORTED_INTERFACE，普通与原生关闭/会话复用检查通过。该条目转blocked，继续探查CFG采用及正式结果出口。

全量普通1702通过；独立安装0.1.48 wheel，真实stdio三项冒烟通过（位图Apply、道路Apply、几何位图限制及清理）。原始失败与成功报告分别保留，证据 .local/evidence/development/IM-01/acceptance050/summary.json；发行 .local/evidence/development/BASE-04/release048.json。下一步继续成像数值/出口探查，再推进偏振、镀膜和材料。全量目标继续进行。


IM-01 已接入六项有类型分析；原生设置采用、非对称网格方向和数值参考待连接恢复。逐项记录见 `development/evidence/imaging023-summary.json` 与本轮 `.local/evidence/development/IM-01/`。

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

`GeometricBitmapImageAnalysis` 的分析 ID 为61；反射未显示独立 BitmapImage 设置接口，使用共享 `IAS_GeometricImageAnalysis` 设置适配。它已进入类型请求、设置回读、结果读取和标准任务关闭路径。运行时 `GetSettings` 类型、结果形状及真实关闭验收等待连接恢复，记录见 `.local/evidence/development/IM-01/geometric-bitmap-image027.json`。


2026-11-06续验086：几何成像理想近轴非对称源发现并修复原生左上边界/向下行序的坐标适配，公开坐标改为像素中心且Y递增，native_axes保留。1W积分、解析质心一像素容差、分页/PNG、模型保持及关闭通过；普通64、原生1通过。仍需旋转/奇偶性及取消恢复，状态implemented。QuickYield18组RMS参考未匹配；原容差保持。证据分别IM-01/probe086.json与TO-01/probe086.json。B002仍8/10；无活动原生会话，无全量或wheel。


2026-11-06：GeometricImageAnalysis完成。理想非对称源四组0/90度及Even/Odd解析位置和1W积分共12次比较通过，原容差保持；四PNG、分页、保存重载后设置/曲面/solve保持，运行中取消cancelled/closed，资源错误后复用成功。相关普通64通过、原生1通过；证据.local/evidence/development/IM-01/acceptance087.json。公开网格使用像素中心、Y递增，保留native_axes及原生单位。B002累计9/10，继续MatrixSpot/ConfigurationMatrixSpot输出验收；本项无全量或wheel。


2026-11-06 ImageSimulation文件出口接通：本机支持OutputFile绝对路径，原生数组数为0时仍生成BMP。解析器支持本机原生非压缩24/32位RGB，结果坐标为实际输出像素中心（X向右、Y向上），单位output_pixel；亮度为8-bit display RGB，采样、保护边框及原生波长着色均保留。输出像素数可能超过请求的XPixels/YPixels，尚未赋予物理探测器坐标或功率单位。

点源、条纹、边缘三组真实stdio完成设置采用、网格分页、数据图、原生彩色PNG及关闭，普通64通过、原生3通过。原生彩色图使用 `export_analysis_image` 的 `source=native`；BMP到PNG会实际转换格式，转换使用reports依赖。默认data_plot绘制所选单通道。见IM-01/probe144.json。ImageSimulation仍为implemented，待受控数值/方向、ShowAs文件语义、状态与取消验收。


2026-11-06 ImageSimulation完成：ShowAs实际选择保存视图；SimulatedImage为原生归一化显示，SourceBitmap含输入翻转/旋转/过采样/guard处理，PSFGrid为原生PSF网格显示。结果的output_view、description和normalization已按视图区分。理想非对称17×11图像逐像素参考通过：模拟图绝对差≤1个8位灰阶，源图及处理后源图精确一致；PSFGrid验证3×3理想显示点阵。单色1/2/3分别使用B/G/R通道，1+2+3、偏振、几何/衍射分支、模型保持/保存重载、失败及运行取消后复用通过。普通64通过、原生4通过；证据IM-01/acceptance150.json。显示像素单位和物理像面坐标分别保留其实际支持范围，RGB不作为辐射功率返回。GeometricBitmap专题CFG接口仍独立开放。

2026-11-06 FFT 线边扩散读取修复：本机 Cooke 的专题结构化数组为空，原生文本包含带索引的位置/数值表。读取器在数组缺失时解析该表，要求匹配的 FFT 线/边扩散标题、连续索引及有限单调坐标，保留原生显示精度和数值，不另作归一化。横轴单位为微米，方向保留原生线/边约定。普通结果读取及相关回归 148 项通过，原生 FFT 线边扩散执行、曲线读取和 PNG 导出通过；见 `.local/evidence/development/CV-01/outlets265/summary.json`、`.local/evidence/development/BASE-04/ordinary266-related.xml` 和 `native266-results.xml`。完整数值参考及其余生命周期验收继续按条目执行。


2026-11-06 FFT线边扩散推进320/321：修复中文“边缘扩散”标题读取；补垂直扫描轴回读、相位degrees/复振幅单位及原生独立标量插值说明。Cooke轴上/离轴PSF边缘积分与ESF累积通过，最大LSF差0.004683、ESF差0.000287，保持0.005容差；原FFT节点复振幅恒等式通过。普通74通过，参考原生2通过、生命周期1通过，含偏振/多色/分页/PNG/取消复用/重载。额外受控镜面的独立相干瞳FFT仍差0.260976；显式坐标范围和入/出瞳3001点检查未消除，继续定位采样/重采样，保留原容差及原始失败。证据CV-01/progress320-spread.json；保持implemented，B004仍6/10。并行的执行队列下一步为几何扩散受控圆盘参考，原生实例始终串行。


2026-11-06 几何线边扩散完成325：原生文本确认四列X/Y方向LSF/ERF，修复None标签并附微米/相对强度/能量分数和chief-ray参考；LineEdge/Line/Edge均保留原生完整四列。受控圆盘解析参考在1024采样、20um范围通过，最大LSF误差0.023568、ESF误差0.003701，保持0.03/0.01容差；256采样诊断另存。相关普通77通过，最终原生3通过，覆盖单/多色、视场3/波长2/像面/偏振、分页/有效PNG查看、失败/取消复用、重载与曲面/solve/配置/MFE保持、正常关闭。证据CV-01/acceptance325.json。B0047/10、剩余139组；继续扩展源包围能量，FFT相干参考0.261差异保持implemented、原容差及探查。


## 扩展源包围能量：2026-11-06 验收337

`extended_source_encircled_energy` 已完成六种数据类型的原生执行与数值验收。`field_size` 为输入方形图像的完整宽度，角度视场使用degrees，高度视场使用当前镜头单位；`maximum_distance` 和曲线位置使用微米。光线数为约 `rays_x1000 × 1000`，实际数量随像素与波长权重分配；当前正式结果未给出实际追迹总数，结果中保留该状态。

```json
{"request":{"kind":"extended_source_encircled_energy","image_name":"point.IMA","field":1,"wavelength":1,"data_type":"Encircled","reference":"ChiefRay","field_size":0.02,"rays_x1000":100,"maximum_distance":20}}
```

先通过 `get_system_resources(request={"kind":"geometric_image_files"})` 选择已存在的IMA/BIM文件。设置和最终资源名称沿用原生写入回读；失败信息保留原生工件、消息及文本路径。

Encircled为圆形区域能量分数，X_Only/Y_Only为指定半宽的无限长狭缝，Ensquared为方形区域能量分数。X_Distrib/Y_Distrib返回原生峰值归一化的相对分布。曲线的 `labels`、`value_units` 和 `extended_source_conditions` 明确其身份、单位与来源，原生标签和横轴保留在 `native_labels`、`native_x_label`、`native_x`。

本机2024 R2的累计曲线有396个等距显示样本，对应100个原始样本和4倍显示细分。受控方形源、点源与Airy参考验证：累计值的围合边界比原生报告位置落后一个原始间隔。结果保留原生 `x/y`，在可识别的采样形态下附 `native_binning.interval_um` 和 `enclosure_radius_um=max(0,x-interval_um)`，并标明计算解释与证据来源。它们随series分页同步切片。其他形态保留原生坐标。衍射修正采用原生无遮拦圆瞳近似；验收使用匹配围合边界的独立Bessel积分。

均匀257×257方形源的四类区域积分、两类分布的累计积分、16/20/40µm范围、近点源极限、自动范围和衍射修正均通过预设0.01绝对容差；最大区域能量差0.006882，点源/标准几何差0.000895，Airy差0.000574。非对称条带旋转90度交换X/Y结果；单/多色、ChiefRay/Centroid/Vertex、视场/偏振/渐晕设置、分页/PNG查看、资源缺失/越界/取消复用、保存重载及曲面/solve/配置/MFE保持、正常关闭和自有资源清理均已执行。

相关普通145通过；原生三类场景通过，点源用例有追加自动范围执行。原始按reported x比较的偏差与分箱定位记录分别保留。完整证据见 `.local/evidence/development/CV-01/acceptance337.json`，B004累计8/10。FFT线边扩散的独立相干瞳参考仍保持implemented，见 `progress320-spread.json`。

2026-11-07 coherent line reference513 compares strict guard nodes (i-N/2)/(N/2-1) against the prior interior-node reference at identical physical output positions. Mirror64 sampling passes;128 sampling fails at focus/defocus with maximum intensity differences0.0059158907/0.0060081473, against0.005. Both sessions disconnect before numerical failures are reported. This preserves the unresolved pupil-edge weighting/coherent-resampling condition. Native513 is1passed/1failed, evidence CV-01/progress513-guard.json; original500 results remain retained.


2026-11-07 B006执行544–547：FFT线边扩散完成声明范围验收。相干参考改用手册明确的默认FFT瞳网格拉伸：`p=(i-N/2)*sqrt(N/32)/(N/2-1)`，仅追迹严格瞳内节点。64/128采样分别有43/63个一维节点；独立新追迹的OPD/强度经物理Fraunhofer求和，在焦面−100/−100.02mm的最大强度差分别为0.000692780、0.000810981、0.000418584、0.000263290，均低于原0.005门槛。544的旧相位插值仅为假设实验，最终545使用准确节点的新光线。

546重新执行Cooke轴上/离轴PSF边缘积分、ESF累积、原FFT节点复振幅强度/相位和生命周期，共3原生通过；545独立参考2原生通过。最大LSF/ESF差0.004682579/0.000286458，强度恒等式差9.97405e-7、相位差0.00239177degrees，沿用原门槛。偏振/多色、设置回读、分页、PNG导出与查看、失败/取消/复用、曲面/solve/系统/MFE保持、保存重载及关闭均通过。ordinary547定向120通过。原0.260976及489/500/513失败实验保留；生产原生曲线/坐标未作补偿。条目CV-01.FftPsfLineEdgeSpread现为done，计入B006第3项。证据`.local/evidence/development/CV-01/acceptance547-spread.json`；请求沿用`examples/requests/imaging023_requests.json`。
# 几何位图更新（2026-11-09）

几何位图现返回RGB及原生正常化强度网格，支持强度区域分页和PNG；原生效率百分数保留实际值并标记独立定义待验。调用与结果字段见[几何位图](bitmap-image.md)。


## 2026-11-09公共方法探查

七种分析的ToFile后缀对照实际均输出结果文本；showSettings仅为StandardSpot列出专用设置，六种AS_Default未取得输入选择器。CreateSettingsFromParent两类parent均返回空键字典。具体结果与生命周期见[证据](../../../development/evidence/D005/common-analysis-outlets-20261109.md)。几何位图已确认的GBM路径及正常化强度支持见[专题](bitmap-image.md)。

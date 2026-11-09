# D005正式CFG与两种图像入口

2026-11-09；主仓C:/Users/tonge/Desktop/mcp，源码0.1.62未发行工作区，主仓.venv Python，COMPLUS_LoadFromRemoteSources=1；OpticStudio24.2.0/build240529/PremiumEdition，配置1、Millimeters。全部原生执行串行。源码能力由101工具/130分析增至101工具/132分析，发行0.1.62仍为101/118；新增完整验收0，累计3/10、剩余93组。

## 单项计划与正式探查

先复核六专题的正式设置类型及结果出口；对已文档化EXD/PCI/GBM键做独立CFG写入、加载和输出回读；只有确认采用的字段接入有类型请求。随后执行真实stdio的设置、结果、分页、绘图和关闭。受控输入为官方Cooke 40 degree field样例的工作副本，原文件保持。

命令：`python -B -X utf8 scripts/probes/D005/runtime_contracts.py .local/evidence/development/D005/runtime-contracts-20261109`。六种默认专题加三种CFG变体，共9项任务全部succeeded、close_attempted=true；系统设置和曲面保持。首次探针从task.result读取到null，原生完整结果实际已保存在每项task.result_path；通过对应JSON形成outlet-summary.json，保留原probe.json，探针后续改用可读取的result_path。原始结果未丢失。

六种实际设置均AS_Default。专题配置文件位于任务自有目录，仅使用MODIFYSETTINGS官方已列键。所有实际键和返回在probe.json。

| 专题 | 原生出口与实际设置结论 |
| --- | --- |
| BeamFileViewer | 一网格和文本；报告明确没有定义文件，尚未取得输入文件选择 |
| BitmapFileViewer | 八类结果数量均0，文本导出false；文件选择及图像出口仍缺 |
| LightSourceAnalysis | 一条提示、无网格；Cooke无限共轭收到finite_conjugate_only，需有限共轭及DAT/SDF选择 |
| GeometricBitmapImageAnalysis | AS_Default；无结构化/RGB网格，但文本含输入名及完整xpix/ypix/R/G/B表；GBM键被接受且尺寸/像素/旋转等可回读 |
| ExtendedDiffractionImageAnalysis | 一网格、文本；四个EXD键实际采用：field2=14度、wave1=.48µm、源宽.1mm、显示宽.2mm |
| PartiallyCoherentImageAnalysis | 一网格、文本；field2/wave1采用，PCI_FILESIZE=.2改变报告宽度；文件身份与完整相干选择仍缺 |

## 非方形网格控制

新增仅运行单专题的参数。命令：`python -B -X utf8 scripts/probes/D005/runtime_contracts.py .local/evidence/development/D005/partial-resampling-20261109 partially_coherent_image`。

PCI_RESAMPLE=1、RSNX=9、RSNY=7、RSDCX/RSDCY=0、RSDLX=.02、RSDLY=.03。写入/加载均返回true；结果Ny7/Nx9、Values形状[7,9]，报告宽.18mm。报告与原生数组按原行序比较最大差.7589753548，反转文本Y后最大差4.879303579130578e-5，符合四位有效数字文本舍入门槛5.1e-5。默认13×13也仅反转Y后匹配，最大4.718079009302656e-5。

原生轴元数据默认MinX/MinY为2，重采样变体为.4，与报告物理宽度不同；其物理定义尚未确认。新适配器保留原轴、以像素索引分页/绘图，不推导未经确认的物理坐标。

## 实现与有类型契约

新增scene_images.py；run_analysis接入extended_diffraction_image及partially_coherent_image。前者暴露field/wavelength/source_width/display_width，后者暴露已确认field/wavelength。均明确input_mode=native_current_input，返回input_selection.identity_verified=false。尚未确认的文件/相干选项由严格请求模型拒绝。

创建前检查范围、镜头单位及能唯一回读的视场条件；SaveTo/ModifySettings/LoadFrom逐项保留返回，报告回读核对最终选择和EXD尺寸。结果验证Nx/Ny、有限非负强度及与反向文本行的全网格数值对应。CFG拒绝时关闭分析，关闭失败标记requires_reconnect并保留原始错误。普通测试覆盖请求边界、回读拒绝、非方形方向、坏数据、CFG拒绝及关闭失败。

已修正image_viewers.py中几何位图拥有IAS_GeometricImageAnalysis的旧描述：该类型属于其他分析，本机构建的几何位图实际为AS_Default。文档键可用性与专题属性可写性分别返回。查看器出口说明同步为本次实测。

## 检查与执行证据

最终普通命令：`python -B -m pytest tests/unit/test_scene_images.py tests/unit/test_image_viewers.py tests/unit/test_imaging.py tests/unit/test_contracts.py tests/unit/test_development_status_report.py -q -p no:cacheprovider --basetemp=.local/tmp/scene-final-20261109`，163项通过。修正保存报告测试和重放程序的迁移路径，原先三项跳过测试本轮实际运行。

原生命令：`python -B -m pytest tests/native/test_scene_images_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/scene-native-20261109 --junitxml=.local/evidence/development/D005/scene-native-20261109.xml`，2 passed in25.96s。

真实stdio原始调用分别位于`.local/runs/runs/scene_extended_diffraction_image_cbda9f87e3/`、`.local/runs/runs/scene_partially_coherent_image_567b37b1bf/`。两项均检查报告实际采用、全精度网格/文本对应、7×5区域分页、PNG输出、任务succeeded/close_attempted且无cleanup_warnings、系统/曲面保持以及正常disconnect。此处数值门槛为原生数组与文本舍入的一致性，不作为独立衍射参考。

两次直接探针shutdown回执包含实际session_id，native.closed=true、forced=false、native.error=null。真实stdio通过工具disconnect及正常退出判定断开。FRU__delta_init既有警告仍留存。

通过真实stdio重新生成docs/reference/tool-schemas.json，请求示例见examples/requests/scene-images.json。产品说明见docs/topics/imaging/scene-images.md。

## 状态和下一步

EXD/PCI由blocked改为implemented，完整功能验收仍未完成。EXD余输入文件/相干及OTF选择、独立衍射参考和物理坐标；PCI余文件/复场身份、Gamma/Alpha/Fraction、部分相干积分参考及完整生命周期。

几何位图的新正式替代出口为GBM配置加RGB文本，下一步先明确独立请求字段与既有GeometricImage继承字段的语义对应，再用自有非对称RGB输入确认文件/通道/像素方向及归一化。其他查看器和光源条目保留具体选择与出口条件，按队列继续。

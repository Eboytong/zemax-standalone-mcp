# 非序列探测器、坐标与数值条件

适用环境：Windows x64、OpticStudio 2024 R2 / API 24.2.0 / build240529 / PremiumEdition。所有原生访问在同一实例串行执行。

## 探测器读取

| 对象 | 请求 kind | 原生读取 | 数量与单位 |
| --- | --- | --- | --- |
| DetectorRectangle | flux / irradiance / intensity | GetAllDetectorDataSafe | 每像素功率 / 辐照度 / 单位立体角功率 |
| DetectorRectangle | coherent | GetAllCoherentDataSafe | 用 coherent_type 指定 Real、Imaginary、Amplitude、Power |
| DetectorPolar | flux | GetAllPolarDetectorDataSafe: Power | 每角度像素功率 |
| DetectorPolar | intensity | GetAllPolarDetectorDataSafe: PowerSolidAngle | 每单位立体角功率 |
| DetectorPolar | irradiance / coherent | 返回 UNSUPPORTED_DETECTOR_DATA | 当前未适配 |
| DetectorColor | flux / irradiance / intensity / spectral | GetAllColorDetectorDataSafe / GetColorDetectorData | 颜色量与辐射量分开；spectral为谱箱空间统计 |
| DetectorVolume | flux / absorbed_flux / absorbed_density | GetDetectorData，X快体素编号 | 三维区域、W/镜头单位³；入射体素通量不作总功率求和 |
| DetectorSurface | flux / irradiance | GetDetectorSize / GetDetectorData | 原生三角像素行，无规则网格顶点映射 |

get_detector_data 保留已有请求。区域宽高各最多100；完整矩阵写入返回的 JSON 文件。区域起点必须位于矩阵内；空矩阵、错误维度和无效原生返回报错。非有限值返回 null，并计入 invalid_count。

value_unit 和 value_unit_prefix 表示当前数值的单位及前缀；source_units、source_unit_prefix、units、analysis_unit_prefix 保留原生设置，其中 units 是原生 AnalysisUnits，不能用于解释全部 kind。flux 的 total_flux 是完整矩阵通量或能量之和；其他 kind 的 total_flux 为 null。平方根振幅的前缀作用于根号内的功率单位。

Polar 的 Power/PowerSolidAngle 为辐射量，即使 SourceUnits=Lumens，也分别返回带光源前缀的 Watts、Watts/sr。SourceUnits=Joules 时对应 Joules、Joules/sr；当前不开放 Polar 的 Lumens/LumensSolidAngle 数据类型。矩形探测器 flux 和 coherent Power 使用系统光源单位。能量模式下，辐照度字段解释为能量密度，value_unit 将原生分析单位中的 Watts/Lumens 分别解释为 Joules/Talbots。原生 units 字段仍原样保留。

Watts/Lumens/Joules 与 None/Milli 共六种条件均具有独立原生进程和 stdio 对照。该检查核对接口数值与单位语义，不替代独立光谱光视效率函数验收。报告指标的单位字符串包含前缀，不将1 mW标成1 W。

### Polar 角度坐标

矩阵列为极角、行为方位角。x_start 对应极角索引，y_start 对应方位角索引。极角相对局部+Z；方位角从局部+X朝+Y增加。全局方向须先使用对象旋转矩阵的转置转入局部坐标。

x_axis/y_axis 返回完整坐标中心与边界，单位 degrees。极角增量为 MaximumAngle/(NumberPPixels-1)，首尾像素在角度边缘截断。方位角边界按像素中心展开，可以为负或超过360°；按周期360°解释，不排序或翻转原生行。

pixel_solid_angle_sr 按极角列返回，每个方位行重复使用。像素立体角为 Δφ*(cos θ_low-cos θ_high)，角度代入公式前转换为弧度。极轴上方位角退化，保留原生功率分配；不能要求极轴光线只占一个方位像素。关闭插值时，用已知非轴向方向核对角度像素；开启插值和镜像的结果具有额外分配规则。

## 对象坐标与设置

### 混合模式的对象组

顺序系统中的 NonSequential 组件通过 `nsc_surface` 选择。对象读取、插入、修改、复制、删除均接受该可选字段；纯非序列系统省略它。

```json
{"request":{"nsc_surface":6,"start":1,"count":50}}
```

```json
{"request":{"nsc_surface":6,"changes":[{"object":2,"x":0.5,"ref_object":1}]}}
```

对象身份是 `(nsc_surface, object)`；`ref_object` 与 `inside_of` 引用同组对象。原生对象矩阵属于组入口坐标，返回 `frame="NSC group entrance coordinates"`，可与 `get_surface_geometry(surface=nsc_surface)` 的顺序系统变换组合。位置应用旋转和平移，方向只应用旋转。

每次操作核对原生组选择，并在成功或失败后恢复原编辑器组；恢复失败返回 `RESTORE_FAILED` 并要求重连。错误保留检查点、修订号、部分修改状态及组编号。未指定组或指定普通曲面会在模型写入前拒绝。非序列追迹、探测器、ZRD 和对象变量入口仍按纯非序列模式使用；此处的编辑能力不代表混合模式完整追迹已验收。

get_nsc_objects 的每行包含 global_transform：rotation、translation、frame、position_unit、formula。采用：

global_position = rotation @ local_position + translation

global_direction = rotation @ local_direction

矩阵来自原生 GetMatrix，包含参考对象关系。读取失败或非有限数据返回错误，不返回单位矩阵代替。公开倾斜参数单位为度。

update_nsc_objects 对位置、倾角、材料、注释、参考对象及包含关系逐项回读；通过 sources 设置 InitialPhaseDeg、CoherenceLength、Jx/Jy、XPhase/YPhase；通过 type_settings 设置 NormalizeCoherentPower 和 UsePixelInterpolation。上述直接属性及 data/sources/type_settings 写入未采用时返回 SETTING_REJECTED，停止同批后续写入，错误包含属性、请求值、实际值、对象编号及检查点。partial_changes_possible 表示已有原生修改，应从检查点恢复或读取当前状态后继续处理。

参考对象和包含关系先检查整个请求合并后的图。原生引用单元格的 None 表示不具有 solve 的可写状态；已有 pickup/solve 继续受替换保护。无材料标记 - 及 MIRROR/ABSORB 不作为玻璃目录依赖。

## 清空、累积与来源

clear_detectors(detector=0) 清空全部；正编号表示对象编号，调用原生 ClearDetectorObject。它与原生 ClearDetectors 的探测器序号参数含义不同。

每个探测器独立保存 trace_history；每条包含 task_id、state、error、finished_at、model_revision、configuration 和 trace_options。trace_options 保存实际偏振、分裂、散射、忽略错误、核心数、过滤表达式及请求随机种子；random_seed=null 表示采用原生随机种子重置，不表示已取得实际种子值。清空策略、ZRD输出路径不参与追迹条件判定。

history_known 表示清空与累积来源已知；model_matches_history 只表示历史对应当前模型修订和配置；trace_options_known 表示历史追迹选项完整；mixed_conditions 表示存在不同修订、配置或追迹选项。同一模型的非偏振与偏振累积返回 model_matches_history=true、mixed_conditions=true、complete=false。过滤和核心数变化采用保守的条件区别，不等同于断言数值必然变化。

complete=true 要求来源已知、全部相关任务成功、对应当前模型、追迹选项已知且一致。缺少历史选项时不将结果标为完整。模型修改后，旧数据仍可读取，其来源匹配状态会改变。显式 accumulate 保留各修订及各追迹条件的贡献。新建、加载、归档恢复及对象编号/类型变化按实际状态重置来源；加载已有探测器数据后，当前服务的追迹来源为未知。

追迹任务结果的 complete 表示该次原生步骤结束；探测器是否构成当前模型的完整独立结果，以 get_detector_data 的 complete 和 trace_history 为准。

取消后的部分数据保留；通过任务状态确认取消完成，不能把取消请求等同于追迹结束。关闭失败沿用服务的重连保护。

run_nsc_ray_trace 的已保存结果包含支持探测器的累计总功率表、单位、complete、mixed_conditions 和 trace_conditions。trace_conditions 在保存时记录各历史任务状态、错误及选项，即使仅保存这份 JSON，也能识别失败或取消的贡献。表中是追迹结束时的累计探测器状态；区域矩阵及相干数据通过 get_detector_data 单独保存。

export_evaluation_report 自动收集累计表关联的已结束任务，包括失败和取消任务；Markdown 展示累计来源，完整 JSON/逐行 CSV/PDF保留状态及错误。关联任务不存在或尚未结束时，unavailable_trace_tasks 标明缺口，保留累计表内的历史快照。报告只读取已有结果，不重新追迹。

## 相干数据的解释

固定等光程、同偏振、同像素、两束等功率光线，关闭 NormalizeCoherentPower 时，相干度为：

C = |Σ sqrt(Pn)*exp(-i*φn)|² / (Σ sqrt(Pn))²

相干 Power 为该像素非相干功率乘 C。相位差0°/90°/180°/270°对应 C=1/0.5/0/0.5。原生初相位单位为度；CoherenceLength=0关闭相干长度导致的随机退相干。

Amplitude、Real/Imaginary和Power分别保留原生定义，并结合像素数、Polarization和NormalizeCoherentPower解释。既有8×8模型与1×1局部分量模型具有不同的显示量核对条件，不能把某个模型的Amplitude含义推广到全部探测器设置，也不能直接以Real²+Imaginary²替代Power。具体公式与独立参考见[相干数值方法](../../guides/numerical-validation.md#有限模型验收与复现)。完全相消时相位没有独立参考意义。

coherence 返回实际归一化与插值开关及上述解释。开启 NormalizeCoherentPower 时按原生总功率归一化规则另行解释；当前等像素模型核对其总 Power 与非相干功率一致。NSC 相干光线模型的结果范围见手册§2.3.2.4.4和§2.3.2.1.9。

## 数值参考与执行

| 场景 | 独立参考 |
| --- | --- |
| Polar | 1 W定向光线；四象限、0°/360°接缝、极区；功率与解析立体角 |
| 参考对象反射 | 非零平移、5°/-7°/11°倾斜的独立旋转矩阵；反射定律；交点与方向 |
| N-BK7平行板 | 本机SCHOTT.AGF Sellmeier系数，0.55 μm；0°/30°、s/p；Snell方向与第一界面Fresnel反射率 |
| 相干 | 10 mm光程、0.55 μm、显式初相位与不同源功率；相干度、原生相位分量及归一化 |
| 来源 | 单探测器清空、跨修订累积、重新加载、归档恢复和取消 |

默认数值容差 rtol=1e-7、atol=1e-8，按量的单位解释。ZRD分支按 SegmentParent/SegmentLevel识别；OpticalPathLU和PathLength为该段数值，不能用于选择最短总路径。ZRD保存值可能具有单精度舍入，实际检查记录保留原值及容差。未被探测功率单列，不自动归因于吸收。

运行专项测试：

~~~powershell
$env:PYTHONUTF8='1'
.venv/Scripts/python.exe -B -m pytest tests/native/test_nsc_validation_live.py tests/native/test_nsc_units_live.py tests/native/test_nsc_provenance_live.py --run-zemax -q -s
~~~

运行示例：

~~~powershell
.venv/Scripts/python.exe -B examples/workflows/run_workflow.py nsc_polar
.venv/Scripts/python.exe -B examples/workflows/run_workflow.py nsc_coherent
.venv/Scripts/python.exe -B examples/workflows/run_workflow.py nsc_reference
~~~

每个场景保存 calls.json、checks.json、工作模型和ZRD。普通测试、真实客户端调用和数值依据分别记录；光学模型见非序列光学验收（历史参考），属性采用、追迹条件、离线来源及完整回归见来源验收（历史参考）。

其他探测器、有限大角多介质散射、CAD及DLL模型按各自支持清单和数值依据使用。CIE官方积分、稀薄荧光、有限带宽相干及近前向多事件的范围见[数值方法](../../guides/numerical-validation.md)。


## 专项数据与适用边界

Color、Volume、Surface、原生探测器文件、光学设置快照及离线报告的完整约定见支持范围（历史参考）。清空失败保留受影响探测器的历史并标为未知，关闭失败继续要求重连。类型、标量和求解模式写入均按原生结果回读。

## 原生波长区间过滤

`read_zrd`的`filter`按原文传给原生读取器。执行前回读Filter，不一致时任务失败为SETTING_REJECTED并关闭工具。ZRDFile是本机接口的只写属性，文件有效性由输入路径及原生执行状态判断，不调用不存在的getter。结果summary保留filter，另返回actual_filter与filter_scope；X_WAVERANGE请求附加wavelength_filter_validation，能力查询返回同一范围说明。


手册2.3.2.1.19定义`X_WAVERANGE(n.f,a,b)`的波长单位为微米，区间双端包含，可省略面号。过滤选择符合条件的光线/路径，读取结果仍包含该路径中的其他段。若需指定对象上的功率，调用方须另选HitObject/HitFace；不能把整条路径每段的Intensity相加当作命中功率。start_ray是同一过滤结果中的零起始位置，分页续读须保持文件和filter相同。

```json
{"request":{"path":"C:/Project/Vibe_Zemax/outputs/my-trace.zrd","filter":"X_WAVERANGE(3,0.5,0.525)","max_segments":10000}}
```

已验证非转换控制模型：七个二进制精确波长0.4375、0.5、0.515625、0.5625、0.625、0.6875、0.75 μm，每源一条已知功率光线。普通区间、精确/共有端点、无匹配、对象及面号、科学计数法与跨光线/段分页有逐条对应依据。相邻闭区间可能共有端点光线，汇总应按(RayNumber, segment_index)去重，或显式单列边界，不直接相加。

本机2024 R2的记录稀薄`_sample_3`标准PhotoluminescenceModel存在原生差异：Polar模型402条转换光线的独立波长约为0.500–0.734 μm，但X_WAVERANGE在0.55 μm附近选中整批光线。该差异在DetectorPolar、DetectorRectangle和开启光谱记录的DetectorColor上均复现，Reader与Viewer回放均不符合独立波段参考。Color显式记录400–800nm、81点后仍复现。三类非转换对照均通过。直接属性式与官方ReadNextResult/ReadNextSegmentFull共享Reader，不能据两个包装推断两个独立过滤引擎。

改变当前波长表、对象/面写法、CompressedFullData/UncompressedFullData，以及开启偏振或偏振加分裂追迹均未取得可靠细分。限制绑定上述模型、本机版本及已测路径；其他荧光算法、离散波移和其他版本仍须各自依据。Reader与Viewer可能共享内部数据处理，内部原因尚未确认。

GUI `ZRDPLAYBACK` 在159条命中的最小Polar工作副本上，完整400–800nm返回159次命中；650–675nm返回0次，独立参考应有ray159/segment2的一次命中。该宏路径未建立可靠的荧光细分替代。请求、六组输出及参考（历史参考）只核对回放总量，不提供逐段筛选成功依据。

荧光细分不计为数值通过。WlUM仍是源光线头波长；正非零光程比值与Sellmeier独立参考仅用于受控验收，不自动替换原生过滤或扩展到零光程、GRIN及任意多次转换。FluxvsWavelength在本机返回AS_Default，尚无已验证的专用替代路径。逐光线差异及原生对照（历史参考）分别提供接口一致性和数值失败依据。

相关复现测试：`tests/native/test_wavelength_filter_live.py`、`tests/native/test_fluorescence_integral_live.py`和`tests/test_fluorescence_path_reference_live.py`。numeric_membership及spectrum为严格数值检查，当前记录模型继续失败；无宽泛xfail。所有原生场景串行运行，输入依赖及具体执行命令见验收记录。

## 回放功率与追迹完整状态

`run_zrd_replay`执行前检查原生文件选择、Filter、探测器、DataType和ShowAs。DataType在本机包含同值别名，例如RadiantIntensity/LuminousIntensity都为3，IncidentFlux/IncoherentIrradiance/PositionSpace都为0；检查采用枚举值，settings.requested_data_type保留调用名称。物理量仍按探测器类型及原生文本单位解释。

回放结果的native_replay_summary从原生文本中提取唯一的总功率瓦特行，包含value、unit、native_token、display_rounding_W及来源行。hit_count在文本可识别时返回整数，否则为空。缺少明确单位、重复总功率、非法数值及未知格式返回extraction_status=unavailable和原因，不填零、不对网格套用统一面积积分。非零文本数值按末位显示精度计算舍入预算；零科学计数值不附加不合理的大误差预算。

`run_nsc_ray_trace`同时检查Succeeded与DeadRayErrors。默认ignore_errors=false时，错误光线能量大于零返回NSC_TRACE_ERRORS；get_task_status.error.details保留原生ZRD位置，任务标记失败。显式ignore_errors=true时可以返回带错误的部分结果，native_trace_complete与结果complete均为false。任务状态及trace_history保存native_dead_ray_errors；该原生量不解释为失败光线条数。源、配置及追迹选项相同也不能使带已知错误的结果标记为完整。

矩形/彩色平面探测器的稀薄荧光对照使用位于目标之外、均匀N-BK7介质内部的吸收保护球，终止未命中目标的光线，避免外部玻璃边界全反射导致提前停止。目标平面全部位于保护球内，过滤参考使用各自无过滤ZRD的实际命中集合。没有转换命中的模型不计作荧光细分通过。配对模型和执行依据（历史参考）分别记录设置成功、完整追迹、原生读取和数值状态。

探测器Polarization=0按手册定义采用标量强度及几何相位，正交Jones输入也参与标量叠加。标志1/2选择局部Ex/Ey，受控模型的独立清空追迹分别得到0.25/0.75 W，与相位无关；返回coherence包含实际标志。有限相干长度的4000条光线、种子42、10mm传播具有99% Markov衰减上界核对；它不替代相干可见度曲线。

# 镀膜层及性能

## 0.1.55 主波长、镜面和生命周期

波长扫描副本保持源系统主波长，避免相对膜厚随扫描下限变化。临时波长表包含请求端点及原主波长，调用 MakePrimary 后回读；扫描区间内、区间外的原主波长均已通过数值验收。实际设置返回 primary_wavelength_um 和完整 temporary_wavelengths。

相对0.25波长厚度、n=1.38薄膜在主波长0.55 µm下，物理厚度为0.25×0.55/1.38 µm。六类指标完成角度、0.45–0.70 µm及0.60–0.70 µm扫描，共18次分析、450次数值比较，最大误差5.41e-13（相位项为度）；容差沿用1e-4°和系数1e-6。源系统/曲面保持及保存重载通过。

MIRROR 的 Phase 主曲线标记 S/P reflection phase；其他介质为 transmission phase。显式 IDEAL2（S反射振幅−1、P反射振幅+1）提供180°/0°参考，两次扫描40项比较通过，最大误差2.85e-14°。无镀膜 MIRROR 的原生导体相位单独保留，不套用理想导体参考。

ReverseDirection原生条件为NonSequential组件曲面，普通顺序曲面传true返回INACTIVE_SETTING并记录曲面类型和条件来源。NSC对象/面选择及反向介质对照单列后续条目。1000层膜系完成运行中取消，任务cancelled、分析和副本关闭、源模型保持，随后新分析成功。副本早期设置失败时检查Close返回值，失败则要求重连，并保留原始设置错误。

证据 .local/evidence/development/CO-01/acceptance058.json；调用示例 examples/requests/coating_conditions058_requests.json。此前0.1.54的600次绝对膜厚参考与本轮相对膜厚、镜面、取消共同覆盖现有顺序请求；六项顺序偏振扫描条目已完成，NSC扩展见CO-01.NscSurfaceScans。

## 0.1.54 波长选择修复与独立薄膜参考

本机镀膜角度分析的 IAS_Wavelength 选择器使用从0开始的列表索引。公开 wavelength 字段继续使用从1开始的系统编号，适配器写入 wavelength-1 并回读；实际设置同时保留原生 Wavelength 和公开 wavelength_number。此前多波长系统中请求2会计算第3个波长，该缺陷由独立薄膜参考发现；历史结构性通过记录保留其范围。

本轮采用 n=1.38、绝对厚度0.1 µm的单层膜和 SCHOTT N-BK7 基底，使用独立 Fabry–Perot 复振幅求和及 Sellmeier 公式。三种系统波长0.45/0.55/0.70 µm的角度扫描，加0.45–0.70 µm波长扫描，覆盖相位、延迟、二向衰减、R/T/A，共24次原生分析和600次比较。相位/延迟以360°为周期比较，容差1e-4°；系数容差1e-6。最大相位/延迟误差4.55e-13°，最大无量纲系数误差2.23e-15。24次分页、PNG导出、关闭及源模型保持通过。

测试实现见 tests/support/thin_film.py、tests/native/test_coating_reference_live.py；证据 .local/evidence/development/CO-01/acceptance057.json 和 native057-final.xml。反向传播、MIRROR相位通道、相对膜厚及原生失败/取消继续验收，相关条目保持 implemented。

## 0.1.53 偏振性能扫描与波长副本

`phase_vs_angle`、`phase_vs_wavelength`、`retardance_vs_angle`、`retardance_vs_wavelength`、`diattenuation_vs_angle` 和 `diattenuation_vs_wavelength` 已加入真实 stdio 执行记录。六项均回读原生 Surface、Wavelength/Angle 和扫描范围，任务成功终止并释放；角度曲线为 400 点，波长扫描结果覆盖请求的 0.45–0.70 微米端点。波长扫描在临时系统副本执行并保留源系统编号，原活动模型设置及曲面状态前后相同。

主曲线分别标注 S/P 透射相位、反射/透射延迟及反射/透射二向衰减；相位定义依据 native analysis header 和 OpticStudio 定义。独立薄膜矩阵数值对照仍待完成，因此这六项维持 implemented。普通专项检查 95 项通过；全量普通检查 1762 项通过，559 项原生测试因默认要求显式 `--run-zemax` 而跳过。显式运行 `pytest tests/native/test_coating_polarization_live.py --run-zemax` 后，六项真实 stdio 分析、结果读取、分页、绘图和任务释放通过，源系统设置及曲面快照保持一致；启动输出含 `FRU__delta_init(): Attempt to start when running!` 警告。证据见 `.local/runs/coating_polarization055_0147d061ae/calls.json`、`.local/runs/coating_polarization055_6bd54c03d5/calls.json`、`.local/evidence/development/CO-01/range055`、`range055b` 及 `.local/evidence/development/BASE-01/remaining-audit056.json`。

## 0.1.51 材料目录修复与镀膜波长参考

完成六项：ReflectionvsWavelength、TransmissionvsWavelength、AbsorptionvsWavelength、CoatingListing、MaterialProperties、InternalTransmissionvsWavelength。十三项镀膜扫描的原生设置/结果/分页/导出通过；相位、延迟、二向色性仍保留独立数值参考，继续implemented。

修复材料工具返回SCHOTT.AGF、已加载目录返回SCHOTT的身份解析，接受可选.AGF后缀，拒绝歧义别名并返回原生名称；读取实际实现对象，避免IsCancelling代理属性不可访问导致整项失败。原生系数与本机SCHOTT.AGF六项逐一对照；波长0.45至0.7微米、45度入射的R/T/A与Sellmeier/Fresnel比较，容差1e-6+1e-5×参考值；内部透过率与半厚度Beer–Lambert参考比较通过。目录查询前后系统设置保持，正常关闭。

全量普通1719通过；独立安装0.1.51 wheel，真实stdio六项冒烟通过，包含目录名/文件名两种形式、AGF系数、内部透过率、三项波长曲线及Listing文本。原始失败、修复结果和实际误差见 .local/evidence/development/MA-01/acceptance053/summary.json，发行BASE-04/release051.json。

下一步继续镀膜偏振量和衍射效率的受控参考，以及GRIN/材料剩余运行时接口。全量目标继续进行。


## 0.1.50 膜层依赖顺序、读取恢复及全字段原生验收

完成CO-01.LayerRead、LayerEdit、LayerSolve三项。原生WAR双层膜系覆盖厚度乘数、折射率偏移、消光系数偏移及各自Fixed/Variable/Pickup状态，保存重载通过；数值回读容差1e-12+1e-12×参考值。只读访问临时启用原生膜层设置，读出设置快照后恢复原开关，修订号保持；零层镀膜直接返回空行，避免不活动开关写入。返回数值为原生设置快照，Pickup状态与源层另列。

预检查采用同样的受控读取，实际修改仍先建立检查点、启用依赖再写参数；失败保留原始读写错误与恢复错误。恢复失败设置requires_reconnect，公开响应同时报告partial_changes_possible。相关注入错误与局部失败普通检查通过。

全量普通1712通过；独立安装最终0.1.50 wheel，真实stdio膜层全字段及反射Fresnel回归两项通过，正常断开。初次零层开关拒绝、原生重载和各次安装包报告分别保留，发行BASE-04/release050.json，完整证据CO-01/acceptance052/summary.json。

PO-01五项通过正式IAS_.SaveTo导出五个18448字节二进制CFG，分析及应用关闭完成；尚未确认参数键。后续使用IAS_.SaveTo/LoadFrom/ModifySettings继续正式键名与采用验证，旧SaveSettings名称改按本机实际接口处理。下一步推进其余镀膜光谱/衍射效率、偏振CFG及材料条目；全量目标继续进行。


## 0.1.49 镀膜曲线修复与偏振运行时探查

完成ReflectionvsAngle、TransmissionvsAngle、AbsorptionvsAngle三项：裸界面0至60度与独立Fresnel对照通过，容差保持1e-6+1e-5×参考值。完整系数表与主曲线分别保留；原生SeriesLabels为空时采用明确标注的列编号，不推断S/P名称。修复顺序系统错误写入ObjectNumber=0和空标签导致曲线读取失败。真实stdio分页、图像导出、正常关闭与独立安装包三项冒烟通过；全量普通1706通过。

PO-01五项已实际构造SettingsFirst并读取运行时接口，均为AS_Default；分析及应用关闭完成。新增可复用runtime_settings_probe.py及三项生命周期普通检查。阻塞依据更新为CFG/正式设置路径探查，替换旧启动失败原因。

膜层原生探查确认UseLayerMultiplierAndOffsets=false时GetLayerSettings(0/1)均返回null，启用后索引1返回Layer=1。下一步实现启用依赖顺序和只读状态恢复，再验收膜层读写/solve；继续偏振CFG路径及后续材料/光线队列。

证据 .local/evidence/development/CO-01/acceptance051/summary.json、PO-01/runtime051/settings.json、CO-01/runtime051/probe.json；发行BASE-04/release049.json。原始四项首次失败及后续定位报告保留，版本0.1.49，全量目标继续进行。


CO-01本批实现13种run_analysis请求及两个层操作工具，状态为implemented。原生设置采用、持久性与数值验收等待启动恢复。正式接口见.local/evidence/development/CO-01/probe024.json，执行证据汇总见development/evidence/coatings024-summary.json。

## 性能分析

六类指标为reflection、transmission、absorption、diattenuation、phase及retardance；分别与_vs_angle、_vs_wavelength组合构成12种kind。均要求surface。顺序系统使用从1开始的实际曲面编号和当前配置；纯NSC使用surface=0及显式对象/面选择。

角度扫描：wavelength默认1，minimum_angle=0、maximum_angle=89（度），reverse_direction=false。波长扫描：angle=0度，minimum_wavelength_um=0.4、maximum_wavelength_um=0.7。minimum_y/maximum_y须成对指定并满足递增；省略时保留原生显示范围，并在实际设置中返回。波长以微米输入，角度定义沿原生入射介质。反向传播沿ReverseDirection定义。

coating_listing读取当前原生镀膜列表文本，无额外设置。文本返回false或异常时保留错误；性能分析继续读取可用曲线/网格；列表条目必须有可导出的原生文本。

RTA两种专用接口逐项写入并最终回读Surface、Wavelength和范围/方向等属性。普通顺序曲面保留不活动的原生NSC选择器默认值；NSC目标显式写入并最终回读ObjectNumber/FaceNumber。结果包含原生标签、头、消息、S/P及平均值的原生曲线身份，保留原生单位和符号；不从曲线位置推断S/P身份。Phase用于MIRROR时为反射相位，其他材料为透射相位，具体轴单位来自原生输出。结果及设置保存模型修订、配置、曲面材料和镀膜名称。

任务通过现有所有者启动、轮询、取消和关闭，设置失败也关闭；曲线支持series分页、网格支持区域分页，并复用export_analysis_image及报告。0.1.14补齐get_task_result在MCP实际签名中的series参数；0.1.13内部请求模型已包含该字段，其stdio签名曾遗漏。

## 层操作

get_coating_layers使用surface、start=1、count=100，返回层编号、ThicknessMultiplier、IndexOffset、ExtinctionOffset、Fixed/Variable/Pickup及拾取源，并提供分页。NumberOfLayers及Layer编号从原生回读；返回编号不符时拒绝继续。UseLayerMultiplierAndOffsets是已公开的活动条件。

update_coating_layers接受局部设置：use_layer_multiplier_and_offsets及layers。每层支持thickness_multiplier、index_offset、extinction_offset和对应thickness_status/index_status/extinction_status。状态请求为{"mode":"Fixed"}、{"mode":"Variable"}或{"mode":"Pickup","layer":2}。厚度乘数无量纲且非负，折射率和消光偏移为有限无量纲增量。

修改层参数要求最终启用层乘数/偏移；省略的设置保持原值。修改已有拾取属性的数值，须显式转为Fixed或Variable。同一属性的Pickup和显式数值不能并用。预检最终拾取关系，拒绝自引用、循环、越界和重复层；先解除需更换的旧拾取，再提交新设置，逐层及最终回读。

层编辑沿用检查点和修订号。部分失败返回completed_layers、prepared_layers、failed_layer、failed_property、失败层当前状态和原始cause；当前状态读取失败时保留次级read_error及原始修改错误。编辑器层对象由系统拥有，没有独立Close。原生基础膜层材料及厚度由镀膜文件定义；本入口编辑公开的乘数、偏移和优化状态。

## 检查与待测

普通检查覆盖13种请求、范围/类型、局部修改、活动依赖、拾取关系、最终回读、原始错误、结果和关闭。tests/native/test_coatings_live.py准备17项原生用例：13种专题、3项无膜空气至n=1.5界面的Fresnel比较，以及有层样例的修改和保存重载。Fresnel预设容差为1e-6绝对差+1e-5×参考值，比较S/P及平均系数。

早期17项用例的逐次状态保留于台账及原记录。本机原生启动已恢复；本轮绝对厚度单层膜独立参考通过，仍需复杂膜系、反向传播、镜面相位和失败/取消验收。正式接口/枚举与本机手册索引930–942页的摘录存于.local/evidence/development/CO-01。

PO-01五项专题已记录独立阻塞。完整静态接口未提供专用设置类型；PolarizationPupilMap有手册PPM CFG键。PolarizationPupilMap 已有后续正式 CFG 和数值验收记录；其余专题继续确认运行时设置、CFG采用和实际回读，见.local/evidence/development/PO-01/probe024.json。IM-01几何位图也已找到官方GBM CFG键，剩余条件为运行时回读及结果探查。


## NSC 对象与镀膜面扫描

十二种扫描支持混合模式的NonSequential组件和纯NSC模型。`nsc_object`为从1开始的对象编号；`nsc_face`为从0开始的原生光学面分组，由`get_nsc_objects`的faces读取。RectangularVolume的光学分组为0、1、2。混合模式的`surface`为组件实际LDE编号，纯NSC为0。两个选择器成对提供，并检查对象和面范围；普通顺序曲面使用原有请求。

```json
{"request":{"kind":"reflection_vs_angle","surface":2,"nsc_object":1,"nsc_face":1,"wavelength":1,"minimum_angle":0,"maximum_angle":60,"reverse_direction":true}}
```

```json
{"request":{"kind":"phase_vs_wavelength","surface":0,"nsc_object":1,"nsc_face":1,"angle":45,"minimum_wavelength_um":0.45,"maximum_wavelength_um":0.7}}
```

NSC扫描在独立原生系统副本执行，保留源模型、活动组件和修订；波长副本同时保留源主波长供相对膜厚计算。`coating_target`记录对象类型、材料、镀膜、面数量、系统模式、实际设置和副本来源。反向传播交换入射介质；N-BK7反向60度裸界面通过全反射对照。曲线保留原生系数表与标签，S/P相位单位为度；角度为度，波长为微米。查询、分页、绘图及任务关闭复用现有入口。

受控N-BK7/N-F2对象、三个光学面、正反向与SPLIT面选择，以及绝对厚度单层膜十二种扫描的数值对照见`.local/evidence/development/CO-01/native160-complete.xml`和对应outputs/runs证据。独立Fresnel容差1e-8+1e-7×参考值；薄膜功率/二向色性绝对差1e-6，相位/延迟的环绕角差1e-4度。

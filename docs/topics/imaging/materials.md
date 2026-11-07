# 材料目录及内部透过率（0.1.15）

## 0.1.51 材料目录修复与镀膜波长参考

完成六项：ReflectionvsWavelength、TransmissionvsWavelength、AbsorptionvsWavelength、CoatingListing、MaterialProperties、InternalTransmissionvsWavelength。十三项镀膜扫描的原生设置/结果/分页/导出通过；相位、延迟、二向色性仍保留独立数值参考，继续implemented。

修复材料工具返回SCHOTT.AGF、已加载目录返回SCHOTT的身份解析，接受可选.AGF后缀，拒绝歧义别名并返回原生名称；读取实际实现对象，避免IsCancelling代理属性不可访问导致整项失败。原生系数与本机SCHOTT.AGF六项逐一对照；波长0.45至0.7微米、45度入射的R/T/A与Sellmeier/Fresnel比较，容差1e-6+1e-5×参考值；内部透过率与半厚度Beer–Lambert参考比较通过。目录查询前后系统设置保持，正常关闭。

全量普通1719通过；独立安装0.1.51 wheel，真实stdio六项冒烟通过，包含目录名/文件名两种形式、AGF系数、内部透过率、三项波长曲线及Listing文本。原始失败、修复结果和实际误差见 .local/evidence/development/MA-01/acceptance053/summary.json，发行BASE-04/release051.json。

下一步继续镀膜偏振量和衍射效率的受控参考，以及GRIN/材料剩余运行时接口。全量目标继续进行。


本批实现get_material_properties和run_analysis.kind=internal_transmission_vs_wavelength。当前93个工具、61种通用分析。两项状态为implemented；实际原生材料身份、系数/表索引、数值与关闭待启动恢复后验收。接口探查见.local/evidence/development/MA-01/probe025.json，汇总见verification/materials025-summary.json。

get_material_properties要求catalog及material，按原生GetAllCatalogs/GetAllMaterials选择唯一名称（忽略大小写），写入并回读SelectedCatalog和SelectedMaterial。返回原生具名色散拟合系数、Nd/Vd、热系数、状态、波长范围及可取得的机械属性/活动标志；保留目录参考温度、压力和公式类型等实际属性。系数单位随原生公式，机械与热属性保留原生定义。

内部透过率表和双折射表默认读取，可通过include_internal_transmission/include_birefringence分别关闭。table_start=0、table_count=200（最多1000）控制两种表的分页，结果附各自total和next_start；系数及表行保留native_index。接口零基索引尚待原生采用确认。目录工具在成功、失败时均关闭，读取过程不调用SaveCatalog；目录资源选择不会修改镜头材料和光学结构。

internal_transmission_vs_wavelength要求catalog和1至4个不重复glasses。目录须已在当前系统加载；同名材料出现在多个已加载目录时返回AMBIGUOUS_MATERIAL，因为专题Glass字符串无法指定目录身份。可通过现有update_system_settings.material_catalogs选择目录，get_system_resources查询目录及材料。

默认波长0.4至0.7微米，厚度thickness_mm=10毫米，minimum_transmission=0、maximum_transmission=1。波长上下限同时为0时使用原生自动范围，其余须正数递增。厚度以毫米输入，与当前镜头长度单位分开记录。结果为内部透过率，表面Fresnel反射损失遵循独立的镀膜/界面分析。

设置通过IAS_InternalTransmissionvsWavelength写入并最终回读，显式清空未使用的Glass2–4槽。分析复用任务状态、取消、结果、series/网格分页、绘图和报告；设置失败关闭分析，终态由任务所有者关闭。结果保留实际目录/材料、设置、单位、配置、修订、原生标签、头和消息。GetTextFile失败可继续读取有效结构化结果。

33项普通检查覆盖边界、身份匹配、目录歧义、未使用槽、最终回读、表分页、非有限数据、资源缺失和关闭。tests/test_materials_live.py准备两项串行原生用例：SCHOTT/N-BK7属性与曲线读取；使用原生IT表节点及半厚度验证Beer-Lambert幂律。透过率预设容差1e-6绝对差+1e-5×参考值；首节点波长容差1e-10绝对差+1e-10×参考值。

四项材料图表DispersionDiagram、GlassMap、AthermalGlassMap、DispersionvsWavelength在完整静态接口清单中未发现专用设置类型，已逐项记blocked。解除条件为恢复原生启动，确认各运行时GetSettings或正式CFG字段、实际采用回读和输出。温度/压力下的色散与热图数值参考仍需原生条件和独立公式检查。既有BASE-04初始化超时仍为原生执行阻塞，本批没有新建原生实例。

例子见examples/materials025_requests.json。默认材料样例来自本机Glasscat/SCHOTT.AGF，实际选择经原生目录工具取得。2024 R2手册索引1353页明确内部透过率厚度单位为毫米，摘录保存在.local/evidence/development/MA-01。

## 指定环境与材料状态的折射率、dn/dT

`get_material_properties.star_samples` 可选，最多100组。目录与材料仍由原生材料目录工具选择并回读；随后使用本机 `ISTARMaterials.GetRefractiveIndex/GetDNDT` 查询。

```json
{"request":{"catalog":"SCHOTT","material":"N-BK7","include_internal_transmission":false,"include_birefringence":false,"star_samples":[{"wavelength_um":0.5875618,"environment_pressure_atm":1,"environment_temperature_c":20,"material_pressure_atm":1,"material_temperature_c":35,"delta_temperature_c":0.01}]}}
```

每组明确波长（微米）、环境/材料各自的压力（大气压）和温度（摄氏度），以及GetDNDT使用的温差。返回请求条件、原生折射率和dn/dT，保留数值参考定义的原生来源。环境与材料条件分别传递，零压力可用于真空条件。

新查询保持原有工具生命周期：读取成功、原生失败或非有限结果均关闭材料目录工具，关闭失败保留原始查询错误与关闭诊断。实际可用性由原生材料接口判定；资源文件发现或STAR模块标志不替代该接口的执行结果。

本机参数名及顺序记录于 `.local/evidence/development/EXT-STAR/probe039.json`。已准备六个波长、固定环境与材料温度中心差分的原生用例，dn/dT预设容差 `1e-8/°C + 1%×参考值`。折射率绝对/相对参考定义、目录Nd差异及受控材料的独立热公式参考仍待初始化恢复后确认；既有Nd容差保持。状态implemented。


## 0.1.52 原生探查更新

GRIN 剖面已完成独立多项式参考与三轴验收，定义见 [GRIN 剖面](grin-profile.md)。四项材料专题本轮实际运行时均为 AS_Default，无专属可写设置；正式 SaveTo 成功，仍需可采用的正式 CFG 参数及结果契约。证据 .local/evidence/development/MA-01/runtime054/settings.json，当前阻塞来源已替换旧启动失败。

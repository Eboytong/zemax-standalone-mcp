# ED-01 属性页扩展（0.1.6）

update_system_settings新增author、afocal_mode_units、aperture_options和advanced。口径选项与Advanced分别覆盖本机9项可写属性。字段名称与类型见tool-schemas.json；get_capabilities连接后提供property_enums。

update_surfaces新增drawing、type_properties、composite、physical_optics、scattering及disable_clear_semi_diameter_margins。局部属性页省略字段保持原值；aperture和scattering为指定类型的设置集合。长度使用镜头单位，散射角度参数沿原生属性定义。

```json
{"settings":{"author":"ED-01","aperture_options":{"apodization_type":"Gaussian","apodization_factor":1},"advanced":{"reference_opd":"ExitPupil"}}}
```

```json
{"changes":[{"surface":1,"scattering":{"type":"Gaussian","scatter_fraction":0.1,"sigma":1},"drawing":{"draw_local_axis":true},"physical_optics":{"resample_after_refraction":true,"auto_resample":false,"x_sampling":"S64","y_sampling":"S64","x_width":10,"y_width":10}}]}
```

新增口径Spider要求width_of_arms及number_of_arms；UserAperture/UserObscuration要求aperture_file，可设置uda_scale。文件来自get_system_resources(kind=aperture_files)。None及FloatingAperture无尺寸参数。

散射支持None、Lambertian、Gaussian、ABg、ABgFile、BSDF、User和ISScatterCatalog。get_system_resources(kind=scattering_files,scattering_type=...)查询对应资源；参数模型按type区分。User参数编号使用原生零起始索引。

get_surfaces的properties包含各页、散射类型及property_activity；系统返回settings_activity。枚举在写入前检查，属性逐项回读，批量错误附completed_surfaces、failed_surface及当前曲面状态与checkpoint。

## 已执行与剩余验收

真实stdio已覆盖系统设置、全部Advanced当前值回写、无焦开关、内置散射与ABg、Spider/Floating/UserAperture/UserObscuration、绘图、类型属性、Composite当前标志及POP各字段回写。既有建模、POP和扩展光线回归通过。

本机创建User散射设置时出现UILDEScatterData不可序列化异常，原始NATIVE_ERROR保留。ABgFile、BSDF及ISScatterCatalog返回的列表只有原生空选项，仍需有效输入文件。FloatingAperture切至None的实测结果保持FloatingAperture，适配层返回SETTING_REJECTED（批量外层PARTIAL_UPDATE）。FRU__delta_init诊断继续保留。

ED-01状态为implemented。待补验收：孔径已知瞳点通过率、Composite非零叠加数值、镜面绘图与导出、逐面POP设置变化的数值对照、各资源型散射有效输入。现有回归验证调用链路，数值范围见原有专题记录。

0.1.7补充验收、修复及原生限制见[property-pages017.md](property-pages017.md)。

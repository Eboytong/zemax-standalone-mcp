# Full Field Aberration

`run_analysis` 新增 `kind="full_field_aberration"`，基于本机 `IAS_FullFieldAberration`。请求支持矩形或椭圆视场、X/Y视场宽度、Zernike项分解、项数、X/Y视场采样、瞳采样、像差类型及显示设置。原生枚举来源为 `.local/evidence/development/BASE-01/probe/api-interfaces.json`。

像差选择使用 `SetAberrationByType`；`SpecifiedTerm` 使用 `SetAberrationByNumber`，两种选择均检查原生返回值并回读像差类型或项编号。其余可写设置通过标准设置写入与回读适配器校验。Field/Wavelength通过其原生选择对象设置并回读，默认各为1；结果经通用文本、曲线和网格收集器读取并由标准任务生命周期释放。

请求例：

```json
{"kind":"full_field_aberration","field_shape":"Elliptical","x_field_width":1,"y_field_width":0.8,"aberration_type":"SpecifiedTerm","aberration_number":5,"maximum_term":15,"x_field_sampling":11,"y_field_sampling":11,"pupil_sampling":"S_64x64","show_as":"FalseColor","display":"Absolute"}
```

2026-11-06已完成四种像差输出的设置采用、7×5网格与独立真实光线OPD拟合对照。Defocus为Standard Zernike第4项；PrimaryAstigmatism为第5/6项平方和开方；PrimaryComa为第7/8项平方和开方；SpecifiedTerm使用有符号指定项。三视场12点在1e-4 waves+1%参考值容差内通过。

结果返回waves和当前物理视场单位，保留native_axes，数组为values[y][x]。本机XFieldWidth=4、YFieldWidth=2对应x±4/y±2，采样包含端点；原生文本Y宽标题重复X值，采用实际设置及网格轴。指定第5项与独立OPD拟合确认Y索引递增方向。

声明范围已完成，证据 `.local/evidence/development/CV-01/acceptance295.json`。非零离焦验证Relative为逐点绝对值减去有效采样点算术均值，Average为同均值常量且保留原掩码。椭圆7×5中16个无效点与椭圆外掩码逐点一致。

参考视场2/波长2的中心为实际视场(0,14°)，与相同条件单视场Standard离焦系数对照通过；ObjectHeight有限物距系统的厘米坐标及范围通过。4×3分页、PNG导出及查看、越界拒绝后复用、运行取消及关闭、取消后复用、保存重载及曲面/solve/配置/MFE保持通过。相关普通20项，原生3项通过，均正常断连关闭。完整例子见 `../examples/requests/full-field-aberration295.json`；请求schema继续沿用 `tool-schemas.json`。

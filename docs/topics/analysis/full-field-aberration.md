# Full Field Aberration


像差选择使用 `SetAberrationByType`；`SpecifiedTerm` 使用 `SetAberrationByNumber`，两种选择均检查原生返回值并回读像差类型或项编号。其余可写设置通过标准设置写入与回读适配器校验。Field/Wavelength通过其原生选择对象设置并回读，默认各为1；结果经通用文本、曲线和网格收集器读取并由标准任务生命周期释放。

请求例：

```json
{"kind":"full_field_aberration","field_shape":"Elliptical","x_field_width":1,"y_field_width":0.8,"aberration_type":"SpecifiedTerm","aberration_number":5,"maximum_term":15,"x_field_sampling":11,"y_field_sampling":11,"pupil_sampling":"S_64x64","show_as":"FalseColor","display":"Absolute"}
```


结果返回waves和当前物理视场单位，保留native_axes，数组为values[y][x]。本机XFieldWidth=4、YFieldWidth=2对应x±4/y±2，采样包含端点；原生文本Y宽标题重复X值，采用实际设置及网格轴。指定第5项与独立OPD拟合确认Y索引递增方向。

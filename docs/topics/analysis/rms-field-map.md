# CV-01 RMS Field Map

通过`run_analysis`运行本机`RMSFieldMap`分析。请求按Field和Wavelength选取中心视场及波长；Surface省略时使用像面。X/Y field size分别给出物理视场半宽，X/Y sampling分别给出网格列数和行数。

```json
{"request":{"kind":"rms_field_map","field":1,"wavelength":1,"data_type":"SpotRadius","method":"RectArray","sampling":"S_64x64","x_field_size":4.0,"y_field_size":2.0,"x_field_sampling":7,"y_field_sampling":5}}
```

Data类型支持`Wavefront`、`SpotRadius`、`Spot_X`、`Spot_Y`和`StrehlRatio`。StrehlRatio要求明确单色波长；`GaussQuad`使用`rings`，`RectArray`使用`sampling`，通过原生`RayDensity`采用。原生拼写`StrehlRation`由适配器处理。设置逐项及最终组合回读，枚举值按本机原生枚举比较。网格每轴5至101点，支持偶数；小于5时原生会在计算时扩大网格，现由请求模型提前拒绝。`show_diffraction_limit=true`同样提前拒绝，该接口无辅助线属性。

网格以`values[y][x]`返回，`min_x/min_y`已加上参考视场的物理坐标；`native_axes`保留原生相对偏移，`field_center`保留中心。原生光斑值按镜头单位输出，适配器换算为micrometers，并返回`native_value_unit/native_to_value_scale`。波前为waves，Strehl无量纲。返回尺寸与请求不一致或原生网格缺失时报告具体结果错误。

2026-11-05完成原生验收，状态done。Cooke模型7×5网格中心(3,10)度、半宽(4,2)度；128×128采样下18组质心/主光线光斑参考和3组ChiefRay波前参考通过。容差分别为0.05µm+1%和1e-5waves+1%，最大差0.0488µm及0.00253waves。Centroid波前与Strehl采用原生设置及受控范围检查；GaussQuad、波长0、偏振和渐晕选项均执行。64采样波前超限及其收敛过程保留历史证据。8张PNG、分页、保存重载、模型保持、无效面/视场、运行中取消与后续复用通过。131项相关普通通过。接口证据为`.local/evidence/development/CV-01/rms-field-map031.json`；本轮汇总为`.local/evidence/development/CV-01/acceptance078.json`。

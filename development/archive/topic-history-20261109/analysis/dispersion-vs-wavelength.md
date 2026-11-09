# 色散随波长：dn/dλ

`run_analysis`的`dispersion_vs_wavelength`支持原生默认报告及可选择的数值导数路径。

```json
{"request":{"kind":"dispersion_vs_wavelength","method":"finite_difference","catalog":"SCHOTT","glasses":["N-BK7","N-F2"],"minimum_wavelength_um":0.4,"maximum_wavelength_um":0.8,"samples":101,"minimum_dispersion":-0.5,"maximum_dispersion":-0.001}}
```

`auto`且只传kind时保留原生报告；显式选择采用正式`ILDE.GetIndex`折射率的五点四阶数值导数，结果标识`finite_difference_of_native_ILDE_GetIndex`。所有节点、原生折射率和差分权重保存在native_queries，differentiation记录算法。`native`加显式选择返回设置限制。

catalog须已加载；glasses为1–4个不同材料名或原生Glasscat目录下的ZTG文件名。默认0.4–0.8µm、101节点；两个波长界限0表示采用资源范围并集。各材料范围外为空值和valid=false。`minimum_dispersion`/`maximum_dispersion`为显示范围，0分别表示自动。启用`use_temperature_pressure`后可选择温压，默认20°C/1atm。

五点差分的名义h为1e-4µm，受材料有效范围限制；内部采用中心公式，端点采用向内的四阶单侧公式。结果单位为`1/micrometer`；rows.dispersion、series、分页和PNG沿用任务机制。副本成功、失败或取消均关闭，关闭失败要求重连。

256项独立解析/热光/线性表格玻璃参考均通过5.1e-8 /µm门槛，最大差1.083e-11；重载、取消复用及主模型保持通过。原生默认专题内部算法尚未公开，历史四点解析偏差保留于默认报告诊断。两条计算路径的来源和数值证据见[验收记录](../../../development/evidence/MA-01/selected-derivative-20261109.md)。

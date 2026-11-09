# 色散图：折射率随波长

`run_analysis` 的 `dispersion_diagram` 返回最多四种材料的折射率曲线。`method=auto`且只传kind时沿用原生默认文本；显式选择采用正式`ILDE.GetIndex`在任务自有系统副本中计算，结果标注`native_ILDE_GetIndex`。`method=native`保留默认报告，显式选择会返回具体设置限制。

```json
{"request":{"kind":"dispersion_diagram","method":"index","catalog":"SCHOTT","glasses":["N-BK7","N-F2"],"minimum_wavelength_um":0.4,"maximum_wavelength_um":0.8,"samples":101}}
```

catalog须已加载，材料身份须唯一；glasses为1–4个不同名称，可使用原生Glasscat目录下的`TABLETEST.ZTG`等表格玻璃文件名。默认波长0.4–0.8 µm，101个含端点节点；两个界限同时0采用资源范围并集。各材料有效范围外返回null和valid=false，原生查询只使用有效波长。

`minimum_index`、`maximum_index`默认0，各自表示自动Y界限。`use_temperature_pressure`默认false；启用后可设`temperature_c`及`pressure_atm`，默认20°C/1atm。采样支持2–2001。范围、有限数值、资源和最终采用值均检查。

`series[0]`按请求材料顺序输出无量纲折射率；`rows`保留波长、有效掩码和各材料值。actual_settings、environment、native_queries记录实际资源、设置及副本身份；两种分页和PNG沿用现有入口。成功、失败和取消均关闭副本，主模型保持。

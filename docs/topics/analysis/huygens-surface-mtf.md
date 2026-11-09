# Huygens Surface MTF

`run_analysis` 的 `kind="huygens_surface_mtf"` 适配本机 `IAS_HuygensSurfaceMtf`。支持视场、波长、瞳面与像面采样、六种 coherent/incoherent 调制/实部/虚部、显示方式、偏振及 `image_delta`。波长与视场使用原生编号；默认均为1。`image_delta` 是像面点间距，单位微米，0采用原生自动值。配置使用当前配置。

设置写入并回读 `PupilSampleSize`、`ImageSampleSize`、`Type`、`ShowAs`、`UsePolarization`、`ImageDelta` 和 `Configuration`，实际采用值保留在任务设置中。有类型请求schema见 `tool-schemas.json`，完整调用序列见 `../examples/requests/huygens-surface-mtf287.json`。

```json
{"request":{"kind":"huygens_surface_mtf","field":3,"wavelength":1,"sampling":"S_256x256","image_sampling":"S_512x512","mtf_type":"MTF_Incoherent","show_as":"FalseColor","use_polarization":false,"image_delta":1}}
```

结果提供 `values[y][x]`、频率单位、零频点及原生轴元数据。本机v242的Huygens原生MinX/MinY将零频放到数组外；适配以shifted OTF的`nx//2,ny//2`为零频，保留原始`native_axes`和原生Dx/Dy。轴标题使用Spatial frequency X/Y，原生空标题另存`native_axis_labels`；数值保持原始结果。支持7×5等矩形区域分页、数据图像导出和现有报告链路。


- 官方Cooke样例，视场1/3、波长1、瞳256/像512、ImageDelta=1µm；独立PSF离散傅里叶参考20点，最大绝对差0.001883895，容差0.005。
- 受控抛物面镜，R=-200mm、K=-1、瞳径10mm、焦距100mm、波长0.55µm；圆瞳解析参考18点，最大绝对差0.003621468，容差0.005。
- 复用已通过的同条件单视场Huygens切片19点，以及六种OTF输出的复数模恒等式检查；历史出处逐项列在证据中。
- 真实stdio检查设置回读、7×5分页及PNG导出/查看；越界视场拒绝后复用、运行中取消、取消后重用、保存重载及曲面/solve/系统配置/MFE保持通过。所有相关会话正常断连关闭。

旧Paraxial圆瞳基线的0.006527误差仍保留在probe092，受控抛物面镜属于另一个明确模型。FFT Surface MTF的离轴PSF/OTF差异见 `fft-surface-mtf.md`。

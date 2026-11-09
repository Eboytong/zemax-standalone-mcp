# 衍射效率分析




## 离轴、DLL和生命周期

有限物距200 mm的受控 Hologram1 使用构造点(0,−100,−200)/(0,100,−200) mm、构造波长0.55 µm、厚度10 µm、平均折射率1.5、调制0.02；关闭Fresnel损失。三种分析分别使用S/P偏振，共384次独立比较通过，最大绝对差5.39e-11，预设容差1e-6+1e-5×|参考值|。曲线、网格区域分页、六张PNG及保存重载后的曲面/solve、配置、视场、波长和偏振保持通过。

独立参考由耦合波解析式及弹性衍射方向构建，见 [Ansys模型说明](https://optics.ansys.com/hc/en-us/articles/42661738883219-Simulating-diffraction-efficiency-of-a-volume-holographic-grating-using-Kogelnik-s-method) 和 [Kick等的原始论文](https://link.springer.com/article/10.1186/s41476-018-0082-z)。代码 tests/support/kogelnik.py；早期TM参考使用离壳耦合方向造成的差异已定位并保留历史记录，数值容差保持不变。

正式surface_files入口发现并采用顺序 us_hologram_kogelnik.dll，三种专题均可读取结果。其S偏振通过同一物理参考；P偏振192个比较点超限，最大绝对差0.44382345。Bragg点原生DLL给出0.24965069，参考为0.69347415。该差异与额外的外部入/出射单位方向内积平方吻合；根因需要DLL源码或供应方对Jones基底/效率语义的说明。结果保留原始数据，在任务evaluation_conditions中明确surface_file和numeric_limitations。DLL探查用例通过表示探查及已知偏差复现完成，P偏振物理验收仍失败。


`run_analysis` 提供 `diff_efficiency_2d`、`diff_efficiency_angular` 和 `diff_efficiency_chromatic`。三者使用本机 `DiffEfficiency2D`、`DiffEfficiencyAngular`、`DiffEfficiencyChromatic` 原生分析枚举，结果复用通用分析任务，收集原生文本、消息、曲线和网格，并使用现有任务查询、分页和关闭机制。

请求字段按本机 `IAS_DiffEfficiency*` 反射定义。二维分析采样范围为 `S_32x32` 至 `S_16384x16384`；角度和波长扫描采样范围为 `S_33` 至 `S_8193`。所有分析接受可选的曲面、光阑场、波长和原生设置中的物体/光源参数。未提供的可写设置保持原生默认值；任务记录保存可读取的实际设置。

二维请求可提供成对递增的 `min_wavelength`/`max_wavelength` 和 `min_angle`/`max_angle`。角度分析仅接受角度边界，色散分析仅接受波长边界。顺序分析要求角度视场和有效体全息参数；安装样例的体全息标志、厚度和折射率默认值需要先配置。角度使用 degrees，波长使用 micrometers，效率为无量纲比例。二维网格的列为角度、行为波长，保留原生轴信息。

0.1.53 原生验收使用 Transmission hologram 样例的 Hologram2 曲面，设置体全息厚度 0.01 mm、n1=n2=1、平均折射率1.5、调制0.02，并将视场改为 Angle。三种分析的专用设置写入及回读、数值结果、分页、PNG 导出、任务关闭、disconnect 和源模型保持均通过。本机 S_65 返回64个点，不包含扫描上边界；S_64x64 返回64×64网格。


原生空曲线及无结构数据返回 `NO_RESULT_DATA`，包含原生消息、文本路径和前导说明；原生结果无效返回 `ANALYSIS_FAILED` 并保留消息及头信息。

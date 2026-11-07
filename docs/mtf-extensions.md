# AN-02 MTF扩展

新增run_analysis请求：

```json
{"request":{"kind":"geometric_mtf_vs_field","frequencies":[50,10,30],"multiply_by_diffraction_limit":false,"scatter_rays":false}}
```

```json
{"request":{"kind":"huygens_mtf_vs_field","frequencies":[10,30,50],"image_delta":0}}
```

```json
{"request":{"kind":"fft_mtf_map","x_field_width":6,"y_field_width":4,"reference_field":2,"x_pixels":7,"y_pixels":5,"data_type":"Average"}}
```

```json
{"request":{"kind":"geometric_mtf_map","x_field_width":6,"y_field_width":4,"scatter_rays":false}}
```

随视场共用FFT随视场的波长、扫描方向、密度、采样、偏振和渐晕设置，频率按原生描述匹配，保留请求顺序与实际曲线对应。Huygens随视场使用本机SampleSize及ImageDelta设置。高采样Huygens计算需要较长时间，应持续轮询任务状态。

Map的宽度为总宽度，单位为角度视场的度数或其他视场的镜头单位。参考视场0以(0,0)为中心。默认频率50、波长1、64×64采样、11×11网格、Average数据、关闭偏振、移除渐晕因子。支持Average、Tangential、Sagittal，使用当前配置。

网格统一values[y][x]，min_x/min_y及dx/dy保留原生结果的物理采样坐标。本机7×5样例覆盖宽度端点，步长为总宽度/(采样数-1)；因此按原生坐标定位数据，而非人为移动半个像素。保留native_axes及原生文本。get_task_result沿用grid/x_start/y_start/width/height分页；export_analysis_image绘制已保存网格。

普通测试入口为tests/test_mtf_extensions.py，原生入口为tests/test_mtf_extensions_live.py。原生比较预设绝对差0.005，普通回归及实际原生验收范围记录在verification/mtf-extensions-summary.json。

本机Geometric MTF Map原生结果含衍射极限修正，与multiply_by_diffraction_limit=true的单视场几何MTF对应；原生Map未公开该开关。结果网格中明确记录此计算条件。

Map每方向采样数为3到100。本机2点网格未返回对应尺寸的数据，服务在原生执行前拒绝该设置。


2026-11-06 B003续探查090：FFT/Huygens曲面MTF设置、频率网格及单视场对照已执行。修复Huygens原生MinX/MinY将DC置于网格外的问题，保留native_axes，公开零频索引与频率单位。匹配显式ImageDelta1µm、瞳/像面256后，19次DC和弧矢/子午比较通过，固定绝对容差0.005，最大截面差0.0018245707674065526；普通25通过。FFT离轴子午差异在128到256采样仍超限，保持implemented。证据verification/development/CV-01/probe090.json。GE-01补五项后剩余159个去重条目；B0030/10，无全量或wheel，无活动原生会话。

二维曲面MTF网格返回frequency_unit、value_quantity、zero_frequency_index与native_axes；Huygens使用校准后的零频原点，保留原生Dx/Dy。FFT的rotation与scale_factor控制原生绘图视角及显示高度，频率数据保持系统坐标。涉及Huygens截面对照时，两端均须匹配image_sampling及image_delta；自动采样与显式采样分别记录。

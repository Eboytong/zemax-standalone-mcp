# 几何位图正常化强度与效率控制

2026-11-09，IM-01.GeometricBitmapImageAnalysis。源码0.1.62工作树，项目Python；OpticStudio24.2.0/build240529/PremiumEdition，Sequential/Millimeters，当前配置。状态implemented；完整验收新增0，累计4/10、剩余92组。

## 范围、正式依据和实现

计划先读取原报告已存在的正常化强度浮点表及效率，确认非方形方向，再对照独立几何参考并诊断效率超100%的来源。

本机手册833—835页确认源像素与瞳随机均匀采样、RGB分箱、Normalize的峰值/平均两种模式、Reference的chief/vertex选择、探测器范围外视为截光及效率的光线权重定义。摘录保留原始目录manual-833/834/835/836.txt。正式ModifySettings表仍只有原十个GBM键；Parity/Source/Normalize等尚未取得正式可写入口。

bitmap_image.py现读取“正常化强度值/Normalized intensity values”附表；要求Ny行、每行Nx有限非负浮点数，保留报告精度并将顶向下文本转为Y向上。缺表时normalized_intensity_available=false；存在但损坏返回INVALID_RESULT_DATA。未将高于1的报告值截断。

RGB仍为grids0/1/2，强度表新增grids3、channel=I、quantity=native_normalized_intensity，沿用网格区域分页与绘图。实际头部回读不重复保存整表。native_efficiency保存原生百分数及independently_verified=false，不截断超100%的值。公开请求未变化；示例bitmap-intensity.json与专题bitmap-image.md记录结果扩展。

## 独立强度参考与原始输入

沿用已保存的有限共轭控制：物距200mm、Paraxial焦距100mm、像距200mm，放大率−1；7×5非对称RGB，源高1mm，17×11输出、每像元0.1mm、每像素10000光线，0/90度。原始输入、模型、请求及报告位于`.local/evidence/development/D005/bitmap-reference-20261109/`。本轮离线读取，无新增原生执行。

独立参考为解析源矩形与探测器像元交叠面积，按原RGB能量求和并除以峰值。沿用前轮预设采样门槛`6/sqrt(N)+2/255=0.06784313725490196`。它覆盖本受控模型的归一化强度，不决定全部原生Normalize条件。

| 角度 | 最大绝对差 | 错误上下翻转的差 | 结论 |
| ---: | ---: | ---: | --- |
| 0° | 0.036677915662648664 | 0.399299 | 通过原门槛，正确方向可区分 |
| 90° | 0.04930800000000002 | 0.632233 | 通过原门槛，正确方向可区分 |

复现：

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/D005/bitmap_intensity_reference.py .local/evidence/development/D005/bitmap-reference-20261109/probe.json .local/evidence/development/D005/bitmap-intensity-20261109/retained-reference.json
```

## 普通与真实stdio检查

相关普通189通过、1.38秒：

```powershell
.venv/Scripts/python.exe -B -m pytest tests/unit/test_bitmap_image.py tests/unit/test_native_bitmap.py tests/unit/test_imaging.py tests/unit/test_image_viewers.py tests/unit/test_model_adaptation.py tests/unit/test_evaluation.py -q -p no:cacheprovider --basetemp=.local/tmp/bitmap-intensity-unit-r2-20261109 --junitxml=.local/evidence/development/D005/bitmap-intensity-20261109/unit-r2.xml
```

初次运行因新增代码多写一个右括号在收集阶段失败，已修正，原unit.xml保留。普通检查覆盖强度表缺行/坏尺寸/NaN/Inf/负数/坏数据、保留高于1数值、原生效率坏格式和受影响请求/消费者。

进程级COMPLUS_LoadFromRemoteSources=1：

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest tests/native/test_bitmap_image_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/bitmap-intensity-native-r2-20261109 --junitxml=.local/evidence/development/D005/bitmap-intensity-20261109/native-r2.xml
```

2通过，26.64秒；XML记录26.593秒。分别覆盖0/90度、黑图、RGB/BMP对应、强度7×5区域分页、item3 PNG导出及取消、损坏输入失败、复用、保存重载。两条stdio会话末调用disconnect，connected=false；终态任务close_attempted=true，无cleanup_warnings。相关系统/曲面/评价/配置保持。首轮仅第一个用例1通过/13.52秒，native.xml保留，不叠加计数。

最终原始目录：`.local/runs/runs/bitmap_cfg_rgb_b89590e19f/`及`bitmap_lifecycle_22957c84aa/`。intensity0.png已查看，坐标、强度色标、非方形布局正常。FRU__delta_init既有警告保留。

## 效率控制：亮度、通道与像素尺寸

同一有限共轭平面Paraxial模型，源图全高1mm、探测器1.7×1.1mm，解析像均位于探测器内。每源像素1000光线。预先诊断参考为几何通过率100%，差阈值0.1个百分点。

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/D005/bitmap_efficiency_controls.py .local/evidence/development/D005/bitmap-efficiency-controls-20261109
.venv/Scripts/python.exe -B -X utf8 scripts/probes/D005/bitmap_efficiency_controls.py .local/evidence/development/D005/bitmap-efficiency-pixels-20261109 --pixel-controls
```

第一轮7×5：red255/red128/green255/blue255/white255/grey128均报告291.667%，black为0%。排除了通道和亮度缩放。

第二轮白图：3×3为225%，4×4为400%，5×3为250%，6×4为400%，7×5为291.667%，8×6为400%。实际源宽为每case的source_width（W/H×1mm）；第二轮原始公共independent_geometry.source_width仍存首轮1.4，逐项source_width为本轮实际值，后续脚本已调整元数据。

六个观测符合`100*W*H/(ceil(W/2)*ceil(H/2))`到报告0.001个百分点精度；这是本控制的经验对应，原生效率计算与对称采样的正式关系仍待确认。13项诊断任务均成功并关闭；两轮四类模型状态保持true，cleanup_failures为空、正常断开。几何100%参考均超门槛，原值和原假设保留。

## 视场对称性控制与最终检查

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/D005/bitmap_efficiency_controls.py .local/evidence/development/D005/bitmap-efficiency-fields-20261109 --field-controls
```

固定4×4白图，仅改变唯一ObjectHeight视场：轴上(0,0)报告400%；X偏移(0.1,0)为100%；Y偏移(0,0.1)为200%；双偏移(0.1,0.1)为100%。报告实际位置与系统回读一致，输出按原生当前参考。两个X非零用例通过几何100%诊断门槛；轴上和Y偏移仍超限。四任务close_attempted=true，四类模型状态恢复true，cleanup_failures为空，断开成功。

观察支持原生效率计数与对称处理有关，区别于输入亮度和颜色。未经正式依据未对结果补倍率。下一控制应在非零X视场下重复奇偶尺寸及受控遮挡，区分对称归一化与实际透过损失；完整设置入口仍待取得。

最终相关普通检查292通过、1.99秒，覆盖光斑、RMS、评价、位图、图像查看器、能力、请求合同及开发状态工具：

```powershell
.venv/Scripts/python.exe -B -m pytest tests/unit/test_spot_configuration.py tests/unit/test_full_field_spot.py tests/unit/test_configuration_matrix_spot.py tests/unit/test_rms_analyses.py tests/unit/test_evaluation.py tests/unit/test_bitmap_image.py tests/unit/test_native_bitmap.py tests/unit/test_imaging.py tests/unit/test_image_viewers.py tests/unit/test_model_adaptation.py tests/unit/test_development_status_report.py tests/unit/test_contracts.py -q -p no:cacheprovider --basetemp=.local/tmp/spot-bitmap-final-20261109 --junitxml=.local/evidence/development/D005/bitmap-intensity-20261109/final-related.xml
```

## 非零X视场的尺寸与截光验收

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/D005/bitmap_efficiency_controls.py .local/evidence/development/D005/bitmap-efficiency-offaxis-20261109 --off-axis-controls
```

固定ObjectHeight视场(0.1,0)，依次使用3×3、4×4、5×3、6×4、7×5、8×6白图：全部报告100%，符合完整捕获参考100%及预设0.1个百分点诊断门槛。随后在4×4白图的光阑面加显式圆孔，半径0.5/0.25 mm，相对入口瞳半径1mm的均匀面积参考为25%/6.25%；原生报告24.635%/6.269%，差0.365/0.019个百分点，均低于执行前固定的2个百分点随机采样门槛。原生rays_per_pixel=1000。

八任务succeeded且close_attempted=true，无关闭警告；移除自有圆孔后settings/surfaces/merit/configurations均保持true，cleanup_failures为空，disconnect.connected=false。参数写入、最终回读、请求、报告和任务均保留probe.json。此结果支持非零X视场下的完整捕获与圆孔面积效率，轴上倍率仍保留为独立原生差异。

## 下一动作

非零X视场源尺寸及圆孔面积参考已通过；下一步取得原生对称效率计数的正式定义或修复依据。完整Parity/Source/Normalize/Wavelength/Reference入口及物理原点仍待取得，条目保持implemented。其他D005文件选择复用已明确的空接口证据，有新依据后继续。

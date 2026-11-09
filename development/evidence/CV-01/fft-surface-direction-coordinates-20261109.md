# FFT Surface MTF保留数据恢复与方向坐标控制

日期2026-11-09；条目CV-01.FftSurfaceMtf；源码0.1.62工作树，当前项目Python环境。全部运算离线执行，没有新建原生实例或原生任务。

## 输入与声明范围

保留原绝对差0.005。独立参考使用509原始Cooke40度模型、波长1=0.48 µm、视场1/3、256瞳网格的光线OPD/强度/像方方向。每视场50613条有效光线，错误/渐晕码均零，强度均1。输入.local/fixtures/surface_mtf509_pupil_3517781fe1/field*-rays.json和autocorrelation.json，其中包含原生结果、设置和上下文。

另用605原生复瞳三出口记录恢复既有基线。605使用波长2=0.55 µm，与509条件不同；两组分别复算，不进行同条件误差比较。输入.local/runs/runs/surface_mtf605_coherent_pupil_7d0d1a6c1d/coherent-pupil.json。

## 路径修复及既有参考复算

scripts/probes/CV-01/fft_surface_retained_controls.py原硬编码已移除的Zemax_MCP目录；改为从自身位置定位pyproject.toml根，输出改到本机CV-01证据目录，自动建立输出父目录。现有数据均已保留，无需重跑原生。

复现命令：

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/CV-01/fft_surface_retained_controls.py
.venv/Scripts/python.exe -B -X utf8 scripts/probes/CV-01/fft_surface_direction_coordinates.py
```

605轴上最大差6.661338147750939e-16，离轴0.00495019710934963，复现原记录。509原native_cutoff映射离轴仍约0.165461，独立参考未通过。

## 新单变量控制

假设：入口瞳均匀坐标至像方方向的非线性映射贡献离轴误差。保持原OPD和强度，将光线方向重采样为两个规则平面：像方(l,m)及主光线法向正交坐标。以原点集三角线性插值OPD/强度，凸包外零填充；按实际方向余弦步长除以波长建立频率轴，零滞后功率归一化。比较原来十个固定频率节点。无拟合尺度、额外相位校正或放宽门槛。

| 视场 | 坐标 | 网格 | 最大绝对差 | 原门槛 |
| --- | --- | --- | ---: | --- |
| 1 | image_xy | 256 | 0.005217775087105636 | 超限 |
| 1 | image_xy | 512 | 0.004872029636048936 | 通过 |
| 1 | chief_normal | 256 | 0.005217775087105636 | 超限 |
| 1 | chief_normal | 512 | 0.004872029636048936 | 通过 |
| 3 | image_xy | 256 | 0.07482757388305658 | 超限 |
| 3 | image_xy | 512 | 0.0751679842569637 | 超限 |
| 3 | chief_normal | 256 | 0.12100729453024411 | 超限 |
| 3 | chief_normal | 512 | 0.12112498571409008 | 超限 |

512网格image_xy最差点为fx=0、fy=49.27204316717331 cycles/mm。主光线法向映射在该视场fx方向误差小于0.0004，但fy方向仍超限。两档网格仅表明本次重采样加密未消除离轴残差；本实验未改变空间幅度权重和参考球相位。

## 结果、生命周期及下一步

原始复算输出.local/evidence/development/CV-01/retained-controls-20261109/controls.json；新控制输出.local/evidence/development/CV-01/direction-coordinates-20261109/result.json，含每个节点、坐标范围、频率步长、有效格点和实际误差。结果来自保留原生数据与离线数学变换，未修改产品适配器或原生设置；资源关闭沿用原运行证据。

保持implemented，完整计数增加0。下一控制需先明确坐标变换的空间幅度/Jacobian与参考球相位对应关系，分别保持另一个因素不变；取得正式定义或可区分实验后继续，不能以跨出口通过替代独立参考。其他D004条目按各自正式接口及定义条件继续推进。

## 本轮定向检查

命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_material_probe_requests.py tests/unit/test_athermal_reference.py tests/unit/test_material_model_reference.py tests/unit/test_gradium_profile.py tests/unit/test_grin_profile.py tests/unit/test_fft_surface_mtf.py tests/unit/test_surface_mtf.py -q -p no:cacheprovider --basetemp=.local/tmp/d002-d004-20261109 --junitxml=.local/evidence/development/CV-01/direction-coordinates-20261109/unit.xml`。

结果136 passed in 0.91s，覆盖材料请求、空气参考、MaterialModel参考、GRIN/Gradium及Surface MTF既有结果合同。方向坐标数值实验结果独立列于上表，其超限结论不由普通测试通过替代。status.py已生成当前统计，剩余99条源记录、92组共同功能、集中检查4/10保持。

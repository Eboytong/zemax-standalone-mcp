# D011：点状荧光共焦响应与有限针孔积分

2026-11-11，已完成。原生接口、双路径执行、有限针孔积分、独立参考、采样收敛、分页、图像导出、失败/取消、复用与资源关闭均已通过。

## 单项实施计划

1. 复用正式HuygensPsf、Normalize=false及ImageDelta/PupilSampleSize/ImageSampleSize设置，逐项写入回读；确认网格坐标、强度归一化和分析关闭。
2. 采用两个独立文件工作副本：照明模型以像面为样品平面；检测模型以有限物面为样品、像面为针孔。样品沿共同正Z偏移时，照明末端空气厚度增加z，检测物方空气厚度减小z，检测相机保持原共轭位置。波长可分别指定。
3. 在同一物理采样下计算照明轴上强度和检测PSF圆形针孔面积积分；以各自零离焦基准统一归一化，保留原始峰值、积分、网格总和和窗口截断信息。输出响应、插值FWHM、离焦点和各原生网格。
4. 先用低NA受控理想系统核对独立圆瞳标量衍射、点针孔极限、有限针孔单调关系及波长/倍率，再覆盖不同系统、采样收敛、失败/取消/副本关闭和源模型保持。
5. 数值门槛和实际合同在探查结果后固定，补有类型请求、定向普通/原生、schema/示例及状态后继续D012。

官方Ansys共焦荧光教程将系统分为激发和检测两部分，针孔位于共轭位置。本项使用原生顺序衍射PSF计算点状荧光的两路径响应。GitHub G5 confocal_tools.py固定commit参考分析组织，本项目加入有限针孔积分及独立检测光路。

## 首轮原生探查结果

原始记录.local/evidence/development/D011/psf-normalization-probe.json，脚本probe_psf.py。原生HuygensPsf确认PupilSampleSize、ImageSampleSize、Type=Linear、Normalize=false、UseCentroid=false、ImageDelta=2µm、Configuration=1均实际采用；128×128网格的首点坐标-128µm、步长2µm。两个50mm原生Paraxial透镜模型，照明为无限远物/50mm像距，检测为100mm物距/100mm像距；孔径直径2mm、550nm，轴向0/±1mm。

照明零焦移峰值0.999803、网格积分239.333µm²；+1mm为0.654828/248.698，-1mm为0.631032/229.719。检测零焦移峰值1/积分938.429；+1mm为0.973912/956.919，-1mm为0.973912/920.397。原生相对强度的积分随共轭变化，因此后续要将各平面转换到统一单位功率PSF密度，并用扩大视窗检查积分截断；直接相乘原生峰值会混入平面间的强度标度。有限物距的收集立体角因子还需正式近轴/光线入口确认后纳入。此次探查正常关闭分析并断开Standalone。

## 完整验收记录

源码：主仓 fc814ef 基线及当前工作区修改，源码版本1.0.0；Windows x64/Python3.14/OpticStudio24.2.0 build240529 Premium。输入模型由原生Paraxial面生成，照明无限远物方、检测100mm有限物距，焦距均50mm，孔径2mm，550nm；备用检测波长600nm。17个偏移为−2至+2mm、步长0.25mm，针孔直径4/60µm。

相关普通检查：`test_confocal.py`、`test_model_adaptation.py`、`test_protocol.py` 合计30 passed（3.53秒）。复合任务在独立工作副本中运行，原始命令、请求、设置、误差及关闭记录分别保存在下述运行目录的calls.json、checks.json和任务JSON中。独立参考采用192及256点瞳数值积分和8×8针孔像素积分。

执行命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_confocal_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d011-native --junitxml=.local/evidence/development/D011/native.xml
```

结果：`1 passed in 383.11s`，OpticStudio 2024 R2 Standalone 正常连接、执行、关闭并断开。原始输出见 `native.txt`、`native.xml`；运行记录见 `.local/runs/runs/confocal_native_ba02c8e6d6/`，图像为 `confocal.png`。

主要数值检查：

| 检查 | 实际值 | 容差 | 结果 |
|---|---:|---:|---|
| 独立 Fresnel 归一化响应最大差 | 0.00404497 | 0.005 | 通过 |
| 独立 FWHM 比值 | 1.00472978 | ±0.01 | 通过 |
| 轴向采样 FWHM 比值 | 1.00507683 | ±0.01 | 通过 |
| 独立瞳积分收敛差 | 0.00049749 | 0.002 | 通过 |
| 原生收集锥解析对照 | 最大约 5.55e-17 | 1e-12 | 通过 |

验收覆盖 4 µm 与 60 µm 针孔、17 个轴向偏移、512×512 瞳采样、128×128 像面采样、4 µm 像面步长、600 nm 备用波长、分页、PNG 导出、错误请求、预算失败、实际取消、工作副本恢复和全部分析对象关闭。源码模型、分析设置、模型修订和最终连接状态保持基线值。

结论：`run_analysis` 的 `confocal_response` 已达到 D011 声明范围，支持照明/检测独立模型、有限圆形针孔、物方收集立体角、单位功率归一化、轴向响应与 FWHM。D011 完成计数增加 1，下一项为 D012。

# 矩阵光斑创建方式和结果出口对照

2026-11-09，CV-01.MatrixSpot、CV-01.ConfigurationMatrixSpot。源码0.1.62工作树，项目Python；OpticStudio24.2.0/build240529/PremiumEdition，Sequential，Millimeters。直接Backend正式API诊断，非新增公开工具入口或完整功能验收。

## 计划、输入与正式定义

假设New_Analysis_SettingsFirst能取得New_Analysis缺失的专题出口。使用官方Cooke40度工作副本，复制当前配置建立两个配置；两种创建方式分别运行StandardSpot、MatrixSpot、ConfigurationMatrixSpot，共六个串行任务。

本机2024 R2手册720—722页确认：MatrixSpot按视场逐行、波长逐列；ConfigurationMatrixSpot按视场逐行、配置逐列。IgnoreLateralColor开启时，各视场/波长独立采用参考点。多配置视场定义改变时左列标签取最后配置。FullField的ChiefRay使用field1主光线，Centroid/Middle完整共同参考及Exaggerate具体坐标仍需对应。

手册文本摘录manual-719-722.txt保留于本次原始目录。上述分面定义已确认，剩余重点为有效输出和完整参考坐标/选项采用。

## 执行、设置回读及结果

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/CV-01/spot_factory_outlets.py .local/evidence/development/CV-01/spot-factory-outlets-20261109`，进程COMPLUS_LoadFromRemoteSources=1。

Field/Wavelength均0、目标像面、Hexapolar、Centroid、RayDensity6、偏振关闭、DirectionCosines/ScatterRays/IgnoreLateralColor关闭、DeltaFocus0；标准和波长矩阵Configuration1，配置矩阵保留正式配置设置。逐项写入并回读actual_settings。同一分析的两种factory最终设置字典完全相同。

| 分析 | 两种factory文本出口 | 两种factory SpotData | 八种结果集合 |
| --- | --- | --- | --- |
| StandardSpot | true，2206 bytes | 非空，3视场统计相同 | 全0 |
| MatrixSpot | false，0 bytes | null | 全0 |
| ConfigurationMatrixSpot | false，0 bytes | null | 全0 |

StandardSpot RMS半径分别4.987874340744222、16.08085519517151、12.030574615362944 µm，两种factory一致；仅用于确认会话与标准结果读取正常。未以其替代矩阵分面数据。

每项诊断任务succeeded表示设置/执行/结果探查完成；矩阵结果仍不可用，产品条目保持implemented。

## 资源关闭及检查

六任务close_attempted=true，无cleanup_warnings；检查点恢复后settings/surfaces/merit/configurations均true，disconnect.connected=false，cleanup_failures=[]。本轮所有原生任务及Python进程均已结束。原始stderr有既有FRU__delta_init警告，保留终端记录；实际断开响应已确认。

原始请求、实际设置、六任务、分页、结果计数、恢复及断开在.local/evidence/development/CV-01/spot-factory-outlets-20261109/probe.json及任务JSON。原生模型副本及检查点保留同目录。普通检查40项通过、0.62秒，覆盖坐标参考、Surface MTF及两种光斑已有请求/设置合同，unit.xml保留完整命令。

## 结论和解除条件

本次两种正式创建方式下矩阵均无有效出口，创建方式假设已排除。下一项验证正式StandardSpot按视场/波长或配置组合的替代路径：先确认IgnoreLateralColor、共同/独立参考点、统计/散点及所有原设置选项能对应，再决定接入；或取得矩阵专用结果/图形出口。仅有统计拼接仍不满足完整光斑声明范围。完整计数增加0。

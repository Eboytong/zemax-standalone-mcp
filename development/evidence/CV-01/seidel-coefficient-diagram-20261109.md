# D004 SeidelDiagram：正式系数重建条形图

2026-11-09。源码0.1.62工作树，Python3.14，OpticStudio24.2 build240529 PremiumEdition。

## 开工计划与声明范围

复用既有IAS_SeidelDiagram设置/空结果探查，先查原生手册图表定义，再从正式SeidelCoefficients取得未转换逐面系数。确认面号、光阑、像面及分区；补齐面范围/波长、色差/畸变显示、尺度及边框；以原生逐面数据、范围和及独立球面S1参考验收，覆盖分页/图像、取消、失败、重载和关闭。

本机手册p.746（.local/evidence/development/EXT-EXPORT/manual042.txt）规定：逐面未转换Seidel系数条形图，显示所选面范围总和，排除像面；PlotScale使用镜头单位，两个Ignore选项隐藏对应系数。该正式定义为系数重建路径的依据。所有系数来自SeidelCoefficients，不将waves/横向/纵向分区混入图表。

## 正式接口、请求与实际采用

`{"request":{"kind":"seidel_diagram","method":"coefficients","first_surface":2,"last_surface":5,"wavelength":2,"ignore_chromatic":true,"ignore_distortion":false,"plot_scale":0.5,"suppress_frame":false}}`

默认auto使用正式SeidelCoefficients子任务；method=coefficients显式选择同一路径；method=native保留原始IAS_SeidelDiagram调用及其本机出口限制，显式面范围/波长选择会返回UNSUPPORTED_SETTING。默认面范围1至像面前一面，波长1、两个Ignore关闭、plot_scale=0自动、边框显示。编号从1开始，末面不包含像面。

系数子任务正式写入并回读Wavelength，actual_settings保留其完整设置及所选面范围；依据原报告STOP/光阑和IMAGE/像面标签，使用当前原生LDE.StopSurface/NumberOfSurfaces归属面号。仅取同时含SPHA/COMA/ASTI/FCUR/DIST/CLA/CTR的唯一未转换分区；重复、缺面、非有限数据、分区冲突明确报错。逐面值保持原显示精度，范围总和使用这些原生值累加。native_totals保留原生全范围总和用于对照。

rows为逐面与Sum；series.plot_kind=bar，分组条形图及面号标签，y单位为镜头单位；IgnoreChromatic隐藏CLA/CTR，IgnoreDistortion隐藏DIST。plot_scale>0使用±scale；SuppressFrame控制绘图边框。computation_method=native_SeidelCoefficients_bar_chart，保留native_text、子任务编号、结果/关闭状态和适用性。分页与报告沿用现有结果链路。

## 检查与实际证据

定向普通检查覆盖tests/unit/test_seidel_diagram.py、test_basic_analyses.py、test_plotting_units.py、test_contracts.py、test_analysis_scenarios.py、test_task_artifact_metadata.py、test_development_status_report.py。首轮发现旧扩展衍射smoke缺必填source_width/display_width，将两种scene分析登记到已有专用原生测试；首轮XML seidel-diagram-unit-final-20261109.xml保留，修正后154 passed/1.57s，seidel-diagram-unit-fixed-20261109.xml。追加默认字段往返后最终155 passed/1.68s，XML为seidel-diagram-unit-delivery-20261109.xml。

原生命令：设置COMPLUS_LoadFromRemoteSources=1和主仓src的PYTHONPATH，执行`.venv/Scripts/python.exe -B -X utf8 -m pytest --run-zemax -q -p no:cacheprovider tests/native/test_seidel_diagram_live.py --junitxml=.local/evidence/development/CV-01/seidel-coefficient-diagram-r2-20261109.xml`，1 passed/16.27s。原始.local/runs/runs/seidel_diagram_coefficients_19f28e251b保存calls/checks及PNG；58项对照通过：逐面条形值对同波长原生系数完全相同；Cooke全范围总和最大差1.0000000000148779e-6，容差1e-5；受控N-BK7双球面独立近轴S1参考0.0004158669930389199，输出0.000416，误差1.33006961080088e-7，原容差1e-6。

Cooke面2–5/波长2、单光阑面4、各Ignore组合、固定尺度和隐藏边框均执行；图像已查看，条形、图例、范围及单位正确。分页、保存重载series一致、越界明确拒绝、实际取消终态及后续复用通过。模型设置、曲面/solve、配置、评价函数保持；各系数子任务成功并close_attempted=true，最终disconnect ok=true、connected=false。

显式native出口回归命令：`pytest --run-zemax -q -p no:cacheprovider tests/native/test_seidel_slopes_live.py::test_seidel_slopes_native_settings_results_and_close[seidel_diagram] --junitxml=.local/evidence/development/CV-01/seidel-native-outlet-regression-20261109.xml`，1 passed/10.76s。该通过为预期EXPORT_FAILED、四设置实际采用及关闭回执，不作为图表成功证据。

首轮图表用例因读取保存结果内的关闭前快照而失败，原始5b1370dd98及seidel-coefficient-diagram-20261109.xml保留；实现改为读取子任务最终状态，r2通过。原生FRU警告保留。图表成功证据由正式系数路径及手册定义证明。

最终原始文本附件已同时接入标准artifacts。重跑完整原生用例1 passed/15.99s，XML为seidel-coefficient-diagram-final-20261109.xml；最新原始目录.local/runs/runs/seidel_diagram_coefficients_eaa785239e，原r2逐点证据沿用。

## 完成判定

条形图完整范围通过正式等价路径交付，显式native限制保留。CV-01.SeidelDiagram标记done，首次完成计数增加一次。集中检查达到十项时再执行全量与发行；后续继续D004的FullField/Matrix正式逐光线路径。

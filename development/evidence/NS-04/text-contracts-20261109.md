# D008默认文本报告续验及双面光焦解析修复

2026-11-09本机执行，原始事件UTC 2026-11-08。主仓源码0.1.62；原生24.2.0 build240529 PremiumEdition，项目内venv，COMPLUS_LoadFromRemoteSources=1。

范围：Prescription章节与Surface面号选择、采用回读、有效文本及生命周期。现有请求为`{"kind":"prescription_data"}`和`{"kind":"surface_data"}`；正式选择接口未取得，完整范围保持implemented。

## 接口及默认出口

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/NS-04/text_contracts.py .local/evidence/development/NS-04/text-contracts-20261109`。

输入为官方Cooke工作副本。两种设置均AS_Default，只有Analysis/TheDataID/IsValid/IsActiveWindow/Parent等基类属性；未发现章节或面号选择属性。本轮未取得文档化CFG选择键。

两任务succeeded、有效文本出口、工具关闭成功；系统设置和曲面保持。会话b4a71369f5d5443e880530a0e805676f实际shutdown回执closed=true、forced=false、error=null，checkpoint成功。原始结果和文本在上述目录。

## 实际失败与修复

真实stdio首轮：`.venv/Scripts/python.exe -B -m pytest tests/native/test_native_text_reports_live.py --run-zemax -q -p no:cacheprovider --basetemp=.local/tmp/text-native-20261109 --junitxml=.local/evidence/development/NS-04/text-native-20261109.xml`，1通过、1失败，26.37秒。

Prescription返回14章、385行；实际请求、设置、标题、行数据、曲面保持与正常disconnect记录见`.local/runs/runs/d008r1_ac009b0db6/`。

Surface失败原始数据见`.local/runs/runs/d008r2_6db1d266b4/`：标题面1，光焦块同时包含面1和面2。旧解析器以后一行覆盖前一行，造成INVALID_RESULT_DATA身份冲突。原生任务关闭成功，失败文本与XML保留。

修复：每块全部面光焦行存入surface_power_components，surface_power按标题面选取；缺少对应面时继续保留身份错误与部分数据。请求契约保持。新增标题为面1/面2的双面普通用例；既有单面及身份冲突用例继续通过。

普通命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_native_text_reports.py tests/unit/test_native_text_report_lifecycle.py -q -p no:cacheprovider --basetemp=.local/tmp/text-parser-20261109 --junitxml=.local/evidence/development/NS-04/text-unit-20261109.xml`，48通过，0.64秒。

失败项重验：`.venv/Scripts/python.exe -B -m pytest tests/native/test_native_text_reports_live.py::test_surface_default_report_identity --run-zemax -q -p no:cacheprovider --basetemp=.local/tmp/text-native-20261109-r2 --junitxml=.local/evidence/development/NS-04/text-native-20261109-r2.xml`，1通过，15.83秒。数据位于`.local/runs/runs/d008r2_5cf80af519/`。

重验报告面1、41行，两个光焦块均保留面1/2；选取值属于标题面，任务succeeded且close_attempted=true，曲面保持，disconnect成功、stdio正常退出。两个stdio用例的应用关闭以实际disconnect成功和正常进程退出记录；直接探针另有匹配会话的关闭回执。FRU警告仍出现，原因未确定。

## 结论与下一动作

默认文本调用及双面报告修复通过；章节/面号选择、采用回读及多配置选择范围继续待验。两条状态implemented，完整计数3/10、剩余93组保持。后续需正式选择成员或有文档依据的CFG键及可靠回读。下一项D008 TestPlate目录选择，然后SagTable制造偏移/面型和反向摘要。

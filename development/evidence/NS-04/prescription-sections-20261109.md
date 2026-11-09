# D008 处方报告导出章节选择

2026-11-09，NS-04.PrescriptionDataSettings；源码0.1.62工作树，发行包未变。项目Python3.14；OpticStudio24.2.0/build240529/PremiumEdition，当前配置1、Sequential、Millimeters。本轮新增功能为原生报告导出后的章节选择；原生设置页选择的完整声明范围保持implemented。

## 计划与输入

复用正式PrescriptionDataSettings导出与已有报告解析器；增加有类型sections、逐章原文行区间选择、所选文本文件和rows分页。参考采用原生完整报告中的相应原文行，要求字符与次序一致，无浮点容差；缺章和重章明确失败。定向检查覆盖请求、设置来源、导出错误、取消/关闭、失败复用、重载和模型保持。

输入为官方`Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos`的项目工作副本。请求为`{"kind":"prescription_data","sections":["files_used","general_data","index_data"]}`；乱序请求用于确认输出按原文顺序。单配置模型请求multi_config_data用于实际失败路径。

## 正式接口与实现

沿用已探查的AS_Default/空IAS_合同，原生实际回读IsValid=true、IsActiveWindow=true；未写入虚构的原生章节设置。原生GetTextFile完整文本通过身份解析后，选取有唯一标题的原文行区间，保留文档头、标题、空行和原换行；输出UTF-8所选文件，完整UTF-16原文保留。

sections有15个文档章节标识，1至15个且不重复。selection记录source=native_report_section_selection、请求/实际章节、native_settings_modified=false及一基原文行号。任务settings.output_selection在收集成功后记录actual。selected_sections/selected_text/rows给出结果，原sections/lines/native_text继续保留完整报告。省略sections兼容原默认输出。

缺失/歧义章节为INVALID_RESULT_DATA，保留原始报告、原生消息和可用章节；写出失败为EXPORT_FAILED。原生设置页的章节选择缺口继续单列selection_scope.status=blocked；输出范围为acceptance_scope=exported_report_sections。

## 命令与结果

最终普通命令：`.venv/Scripts/python.exe -B -X utf8 -m pytest tests/unit/test_native_text_reports.py tests/unit/test_native_text_report_lifecycle.py tests/unit/test_prescription_sections.py tests/unit/test_basic_analyses.py tests/unit/test_contracts.py tests/unit/test_task_artifact_metadata.py tests/unit/test_development_status_report.py -q --junitxml=.local/evidence/development/NS-04/sections-consumers-20261109.xml`。

134 passed/2.47s。覆盖15章英文标题、真实中文报告、乱序/重复/缺章/重章、CRLF、全部章节重建、导出错误、默认兼容、共用任务取消与停止确认、关闭失败及requires_reconnect。首轮有一个测试因read_text规范化CRLF导致断言失败，修正参考读取后通过；生产导出保持原始换行。最初XML仍保留。

原生串行命令（进程设置COMPLUS_LoadFromRemoteSources=1，PYTHONPATH指向主仓src）：`.venv/Scripts/python.exe -B -X utf8 -m pytest tests/native/test_native_text_reports_live.py -q --run-zemax --junitxml=.local/evidence/development/NS-04/sections-native-20261109.xml`。3 passed/34.38s，含默认处方、默认曲面和所选章节。

追加实际章节写回任务元数据后，定向复验：同命令选`::test_prescription_selected_sections_paging_reload_failure_and_close`，XML为sections-native-final-20261109.xml；1 passed/15.49s。最终原始目录`.local/runs/runs/prescription_sections_1deaf22c78/`，calls.json/checks.json及所有原生/所选文本与模型工作副本保留；前一轮原始目录prescription_sections_7163b045fb另保留。

实际章节general_data/index_data/files_used，共118行，7行一页遍历无缺失/重复；所选文件内容与相应原生行逐字相同。实际multi_config_data缺章任务failed、INVALID_RESULT_DATA、close_attempted=true。随后保存重载并再次运行成功，折射率章节相同；系统设置、全部曲面（含solve）和评价函数保持。正式实际章节记录通过最终断言。

## 生命周期、结论与下一步

成功及失败任务均查询实时终态和close_attempted，失败后无需重连即可复用；最终disconnect.connected=false、warnings=[]、requires_reconnect=false。取消/关闭失败由真实共用任务状态机的普通测试覆盖，本轮未宣称实际原生取消已经运行。无本轮活动原生会话。

本轮新增可用的导出章节选择与分页；共同功能完整计数增加0，累计7/10，89组剩余。原生设置页章节选择仍须正式可写/回读入口；SurfaceData面号选择仍独立待办。下一步继续D008原生报告选择/制造定义的新依据；已有空接口合同复用，随后推进D009及数值待匹配条目的可区分实验。

# 复用任务：D008处方与曲面文本报告

负责人复用`zemax-p01-gradium`及其现有会话、分支和工作区；Gradium交付继续保留。条目为`NS-04.PrescriptionDataSettings`、`NS-04.SurfaceDataSettings`。

当前正式设置对象为AS_Default，没有已确认的章节或面号选择入口；默认原生报告已输出且关闭。完整选择范围保持blocked。先读取主项目原始报告，交计划并完成审查后补齐默认报告的有类型调用和文本结果。

真实输入位于主项目`.local/evidence/development/NS-04/prescription-20261108/native/87f78e6437c045a3af07ba73ec433e30/68ace1bed8d14c1cb569d97dbc5bfb09_native.txt`和`surface-runtime-20261107/native/31555643fd4a440db72f92b425b47e18/48596bf64aa34056a25e744999a48f20_native.txt`；工作区内不存在这些本机数据时，使用主项目绝对路径。

请求先提供kind-only的`prescription_data`和`surface_data`。正式选择未知时拒绝额外选择字段。结果保留原始报告、实际章节、面号、单位、字段和来源；未知章节原样保留，按实际报告判断缺失或格式错误。文本解析不能把默认输出解释为请求选择已采用。

专题模块使用`native_text_reports.py`，复用AnalysisJob。`analysis_models.py`、`analyses.py`接入作为最小共享补丁单列。定向检查覆盖真实样本、严格请求、空/截断文本、中文与英文、单位、面号和章节归属；原生作业待启动条件恢复后串行执行。

交付`.local/coordination/d008-reports-plan.md`、实现报告、普通结果和原生作业单。完整条目完成仍需正式选择及可靠采用回读证据。

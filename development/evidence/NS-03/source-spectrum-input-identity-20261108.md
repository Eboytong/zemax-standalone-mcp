# 源光谱输入身份与结果解析审计

2026-11-08；源码0.1.61工作区；OpticStudio24.2.0 build240529 PremiumEdition，Python3.14。

计划：核对原始报告输入身份，增强损坏行/非有限值处理，补分页与关闭，再在同一会话更换为空NSC系统观察结果。原有默认报告参考保留：20点0.44-0.64微米、峰值1、XYZ输入/拟合均[1,1,1]、CRI70.1766、CCT5188K。

发现：原始报告明确写“由XYZ三色值输入”。此前将其称为聚合源光谱缺少依据。现返回input_definition=native XYZ tristimulus fitting input、source_object_binding=not exposed by installed analysis settings，保留文本及原始字段。输入选择合同仍未公开，未加入猜测参数。

实现：科学计数法元数据与光谱行可读；坏行、负/非有限/超范围权重、非正波长及非有限XYZ/CRI/CCT整体拒绝，不静默输出部分曲线。移除解析器人为0.1-10微米筛选，按原生报告正波长返回。新增8个边界检查，含溢出和坏行。

普通命令`.venv/Scripts/python.exe -B -m pytest tests/unit/test_yni_contributions.py tests/unit/test_contracts.py tests/unit/test_basic_analyses.py -q -p no:cacheprovider`：66通过。

原生命令`.venv/Scripts/python.exe -B -m pytest tests/native/test_source_spectrum_live.py --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/NS-03/source-spectrum-nsc-identity-audit-20261108.xml`：1通过，9.86秒。文件`.local/runs/runs/source_spectrum_6e9adc87bc/input-identity.json`保存对照，calls.json保存实际请求/结果/状态。

两色混光样例的20点光谱、XYZ、CRI、CCT与新建空NSC系统全部相同。默认报告输出不能归属为本样例光源叠加结果。首任务succeeded、close_attempted=true，分页start3/count2返回索引3/4，模型保持，最终断连通过。初始化FRU警告保留。最初误用默认Sequential空系统得到ANALYSIS_FAILED（close_attempted=true），随后改为NonSequential完成同模式对照；两份XML与原始调用均保留。

状态：NS-03.SourceSpectrumViewer保留implemented，默认报告解析可用，完整选择/归属尚未验收。解除条件为正式输入模式/XYZ或文件选择及采用回读，并对受控可变输入建立色度/光谱参考；不计B006新增完成数。下一项方向性图输入文件身份与独立IES参考。

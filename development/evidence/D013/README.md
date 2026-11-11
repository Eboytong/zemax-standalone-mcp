# D013：System Drawing接口探查历史

2026-11-11，本项已按用户要求退出当前开发计划。以下保留实际探查结果。未创建OpticStudio应用，未占用API许可。复查本机2024R2的ZOSAPI_Interfaces.dll及ZOSAPI.dll全部类型/公开成员，查询SystemDrawing、Unfold、ExportAsPNG、ExportAsPDF、ExportAsEMF；匹配数为0。OpticStudio.exe文件版本24.05.29。详细程序集身份、类型数量及布局/结果接口成员保存在`.local/evidence/development/D013/interface-recheck.json`。

## 可重复命令

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/D013/system_drawing_interfaces.py
```

该探针只读取本机正式程序集；已有普通光路图导出入口为ICrossSectionExport与I3DViewerExport。

## 外部源码和正式定义复核

Atto固定commit790345d67060a1b20fe46f9cba3ec5d2007f6921的tools/tolerance_tools.py确实调用New_SystemDrawing，并依次尝试UnfoldSystem/Unfold/UseUnfoldedSystem。该文件展示了调用代码，未提供本机所需正式成员。官方2024R1 I_Analyses成员索引及类文档检索未取得SystemDrawing/Unfold同名入口。原始四功能探查继续见[2026-11-10记录](../native-feature-portability-20261110.md)。

来源：
- https://github.com/attoyuan/zemax-opticstudio-mcp/blob/790345d67060a1b20fe46f9cba3ec5d2007f6921/tools/tolerance_tools.py
- https://developer.ansys.com/docs/zos-api-interface-2024-r1/namespace_z_o_s_a_p_i_1_1_analysis.xhtml
- https://developer.ansys.com/docs/zos-api-interface-2024-r1/interface_z_o_s_a_p_i_1_1_analysis_1_1_i___analyses.xhtml

## 资料状态

本记录用于解释正式接口探查结果，当前计划已移除此项。原有编号和探针路径作为历史检索入口保留。

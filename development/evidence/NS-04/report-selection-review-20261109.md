# D008 原生报告选择入口复核

2026-11-09，OpticStudio24.2/build240529/Premium，Python3.14，主仓 `C:/Users/tonge/Desktop/mcp`。本记录复用正式程序集反射、原生报告和配置证据，对 SurfaceData、PrescriptionData 与 SystemData 的原生选择入口作边界确认。

SurfaceData 与 PrescriptionData 的设置工厂在顺序系统返回 `AS_Default`；公开接口仅有基础 `IAS_` 成员，没有专用 `IAS_SurfaceData/IAS_PrescriptionData`，也未找到手册/反射中可确认的面号或章节键。SurfaceData原生报告实际标题为“表面1数据概要”，其面号来自默认原生报告。多面光焦解析可识别面1、2，但属于完整报告内容读取，不能代替原生面号设置。原生会话、报告对象关闭通过既有证据 `surface-data-settings-20261108.md`、`outlets068/summary.json` 及 `native_text_reports_live.py`。

PrescriptionData 已支持 `sections` 的结果章节筛选、原文行号、分页和所选文本导出；请求及结果均明确标记 `native_settings_modified=false`。它是报告产物筛选，不能作为原生章节开关采用证据。最终所选章节stdio验收见 `prescription-sections-20261109.md`。SystemData请求为 kind-only，运行时采用 `AS_Default/base IAS_`，原生全文默认导出；章节筛选及原生章节开关均未确认，见 `src/zemax_mcp/system_check.py` 和 `development/evidence/NS-04/outlets068/summary.json`。

结论：当前官方接口证据不足以完成三个专题的原生选择设置契约。保持已有默认原生报告和导出结果筛选能力；三个原生设置范围不标记完成。若获得官方设置窗口配置、正式键说明或具有可回读面号/章节的专题接口，再按任务指定模型及章节逐项实施。当前转入D001相位收尾及D002材料图表项。

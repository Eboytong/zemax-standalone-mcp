# Zemax Standalone MCP 能力说明

发行与源码0.1.61，100工具/110分析；B005已完成10/10并发行。B006仍5/10，目标0.1.62。剩余130条源记录、122个不同编号、120组共同功能；38条历史范围另列。

系统与文件、顺序建模、编辑器与配置、设计优化、光斑/MTF/波前/RMS、成像/偏振/镀膜/材料、非序列、POP、公差、几何与交付能力见[工具清单](reference/tools.md)、[请求模型](reference/tool-schemas.json)及[专题索引](reference/capabilities.md)。

任务支持查询、取消、分页、文件与报告；修改沿用工作副本、检查点及修订机制。

B006已完成POP/制造交付工作流、FFT线边扩散、NSC几何MTF及QuickYield。其适用条件和历史误差见各专题。

637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。

640普通45项、641正负原生2项通过；新增1001节点径向加权斜率摘要。继续制造偏移符号/基准、面型拟合适用性及反向制造摘要，保持implemented。

其他待处理能力见[全部剩余排序](../development/remaining-ranked.md)。当前证据和下一动作见[交接](../development/handoff.md)；历史见[归档索引](../development/archive/README.md)。


文档分区：guides为调用指南，reference为接口参考，topics为业务专题。开发入口为[development/README](../development/README.md)。

# 工具自主性与披露研究证据

日期：2026-11-11。产品1.3.0、源码`83b5ea783efa7dec5f57c225bda01e422ab881b0`。实际导入`C:/Users/tonge/Desktop/mcp/src/zemax_mcp/__init__.py`。本次只读分析和stdio目录测量，OpticStudio应用未创建。

## 输入与命令

输入为正式tools/list、capability_index索引和当前请求模型。使用项目Python3.14、MCP2.3.0，子进程显式设置PYTHONPATH为主仓src。

```powershell
.\.venv\Scripts\python.exe -B -X utf8 development/evidence/PLAN-20261111-DISCLOSURE/measure.py
```

原始工具描述和测量JSON写入`.local/evidence/development/PLAN-20261111-DISCLOSURE/`；摘要为[metrics.json](metrics.json)。stdio上下文正常结束，命令exit_code=0；没有模型修改或原生应用资源。

## 方法与结果

紧凑JSON、UTF-8、ensure_ascii=False；分别统计完整描述、输入、输出及单能力详情。详情裁剪实验仅计算$ref可达类型，产品保持1.3.0原状。

- 107工具、146分析kind；完整工具描述1,431,740字节，输入schema映射1,340,906字节。
- 最大7项输入合计1,185,606字节，占88.4183%；排行和每kind大小见JSON。
- wavefront详情151,046字节，裁剪实验1,247字节；独立kind包装schema830字节。
- 9个现有引导/控制工具10,275字节；两个执行入口待实现，compact总量按真实stdio验收。
- 搜索示例Top-5结果3,744字节。详情携带整套分析定义，Evaluation在多个接口中重复嵌套AnalysisRequest。

模型token、宿主实际注入、任务完成率和延迟由D023/D027取得；本次保留字节指标。

## 源码与资料

审查server、models、capability_index、bridge、backend、glass_trials、joint_glass、merit_program、desensitization、sequential_energy及相应指南。

一手资料与具体取舍见[调研报告](../../tool-disclosure-research.md)，任务D023—D027见[计划](../../plan.md)。研究不计功能完成。

## 本轮检查

- 重跑stdio测量成功，107工具、146分析，命令exit_code=0，服务正常关闭。
- 状态脚本生成5项、完成0项、下一项D023，派生视图已刷新。
- 定向命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-roadmap-disclosure`，4 passed，0.09 s。
- 产品源码、请求合同和发行wheel保持1.3.0。本轮变更为开发文档、测量程序和研究证据。

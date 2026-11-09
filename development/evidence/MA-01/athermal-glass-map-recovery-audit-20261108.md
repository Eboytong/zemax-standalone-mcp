# 消热差玻璃图恢复后审计

日期：2026-11-08；源码0.1.61及未发行工作区修改；OpticStudio24.2.0 build240529 PremiumEdition，Python3.14。

计划：核对有类型请求、实际设置、原生文本转换、波长与单位、分页/PNG、模型保持和断连。数值参考沿用原生报告的显示值与xE-3/xE-6标尺；本次没有独立热光焦公式验收。

执行：
- `.venv/Scripts/python.exe -B -m pytest tests/unit/test_glass_map.py tests/unit/test_contracts.py -q -p no:cacheprovider`：39通过。
- `.venv/Scripts/python.exe -B -m pytest tests/native/test_athermal_glass_map_live.py --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/MA-01/athermal-recovery-audit-20261108.xml`：1通过，11.04秒。
- 原始调用：`.local/runs/runs/athermal_glass_map_native_631ddbd7f5/calls.json`。

有类型kind-only请求成功；实际AS_Default的IsValid/IsActiveWindow为true。波长0.55/0.55/0.55微米，原生数据转换、非空玻璃散点、3行分页和PNG输出断言通过；系统设置前后相同。任务bdac39c78d9e47bc9df0e06667d6de4b为succeeded，close_attempted=true，模型修订4；disconnect返回connected=false，stdio子进程正常结束。

启动输出出现`FRU__delta_init(): Attempt to start when running!`，本次任务仍通过。将此作为BASE-04生命周期问题的新复现线索保留，未宣称根因已解决。

结论：当前报告适配合同重测通过；完整材料/目录筛选与独立热光焦参考仍待与原声明范围核对。条目保持implemented，本次重测不增加B006完成数。下一项审计色散图的原范围与选择条件。

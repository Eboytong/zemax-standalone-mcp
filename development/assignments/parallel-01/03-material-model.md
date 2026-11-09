# Agent 3任务书：D002临时材料模型

范围仅`ED-02.MaterialModel.Material`一组。与材料图表、Gradium无新增实现依赖，可并行诊断。它是D003的solve聚合前置，结果交审查负责人统一收口。

## 开工计划与基线

阅读`development/evidence/ED-02/material-model-repeat20261108.md`、`progress598-formal-fit-audit.json`、`src/zemax_mcp/solve_support.py`、`tests/native/test_extended_solves_live.py`及`tests/support/material_reference.py`。

现有请求Nd=1.6、Vd=60、dPgF=0.001；Nd在`1e-6`内，Vd实际`59.99988524798844`，超原`1e-5 + 1e-7×参考值`门槛。接口回读及重载已通过；公开接口尚无临时ModelGlass的系数出口。

发布本项计划，先列出标准谱线/波长精度、空气/真空约定、dPgF定义、原生拟合与取整等可区分假设，写明各控制实验预期。

## 可立即执行的工作

1. 逐项核对当前谱线与数值参考，复核Nd/Vd定义、单位和波长；保留原始请求及六波长数据。
2. 审查正式MaterialModel接口与本机文档的模型色散定义；区分目录材料系数与临时模型材料，记录可用公开成员及选择能力。
3. 用独立数学推导分析误差随谱线、Nd/Vd/dPgF和取整变化的量级，提出最小单变量矩阵。先完成离线参考测试。
4. 若确认实现或参考有具体错误，提交最小修改及依据；参考变化需同时保留原定义、原误差和新定义依据。

## 原生矩阵与完成条件

Agent 0排队执行现有`tests/native/test_extended_solves_live.py::test_material_solves_numeric_stdio[model]`及必要的新控制用例。先复现Nd=1.6/Vd=60/dPgF=0.001基线，再每次只变一个量。

至少覆盖两入射角的独立Snell求折射率、正式直接折射率出口对照、solve回读、保存重载、配置/模型恢复和资源关闭。保持原Nd、Vd门槛；接口定义与数值参考一致后再判断完成。

正式模型定义或系数仍缺失时，提交能够区分解释的结果和确切解除条件，保留`implemented`。接口拒绝或模型计算异常保留原始阶段与原因。

## 文件归属与普通测试

本任务拥有MaterialModel相关solve适配、独立参考/诊断、新增材料模型测试。`models.py`、`modeling.py`及总solve注册的变更单列共享补丁；`tests/native/test_extended_solves_live.py`中已有模型数值用例如需改动，也单列符号范围。

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_extended_solves.py tests/unit/test_solve_support.py -q -p no:cacheprovider
```

新建任务专用参考文件，现有共同数学辅助按[并行安排](../../parallel-development.md)交集成处理。最终交回完整误差表、接口结论、代码补丁、定向测试、原生作业与状态建议。

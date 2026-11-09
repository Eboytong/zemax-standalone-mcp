# Agent 4任务书：D002 Gradium完整剖面

范围为`MA-01.GradiumProfile`，别名`CV-02.GradiumProfile`，合计一组。每个子实验先写计划和可区分假设。与材料图表/临时材料模型可独立推进，保持各自文件所有权。

## 先读取的材料

- `development/evidence/MA-01/gradium-capping-boundary-repeat20261108.md`和637—639原记录及保留数据。
- `scripts/probes/MA-01/gradium_basis637.py`、`gradium_dispersion624.py`、`gradium_snell630.py`。
- `analyses.py`的`configure_grin_profile`、`grin_source_context`、`label_grin_profile`及`GrinProfile`请求。
- `tests/unit/test_grin_profile.py`、`tests/native/test_grin_profile_live.py`、`tests/native/test_gradium_extent_live.py`。

已知0—9阶为浮点精度；10/11阶单位幅度最大误差约`5.104e-9/6.124e-10`。相同归一化坐标下zmax=1和5.8结果一致。两材料负向偏移-0.2的capping2/3共四个组合仍返回ray error 2，与当前预测不同。专题正式选择/回读尚待确认。

## 实施计划

1. 读取GRD配置、系数顺序、材料参考波长与系统波长、zmax、偏移和capping定义。形成可手算的低阶/单项式参考，并提取原高阶验收门槛与单位。
2. 离线重算637—639逐点结果，分离坐标转换、系数顺序、求值算法、文本精度和色散因素。保留原始高阶误差，列出能区分各解释的新实验。
3. 边界实验分别控制偏移符号、曲面传播方向、前后顶点和GRD左右端，复核负厚度/反向配置的适用条件。每轮只改一个因素，用独立公式给出预期索引和光线状态。
4. 探查Gradium专题正式选择与设置出口。若使用现有GrinProfile取得曲线，记录专题窗口与正式替代计算各自覆盖范围；工作副本保留配置、厚度、偏移、材料和实际参数。
5. 基于已确认的定义修复适配或参考，补必要有类型参数/结果来源及专用测试。完整范围通过后提交两个别名同步建议。

## 检查与原生排期

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_grin_profile.py -q -p no:cacheprovider
```

向Agent 0提交现有原生用例和新增单变量用例的精确命令；输入GRD及模型使用任务自有文件。已有轴向方向绝对差`1e-10`、顶点参考`atol=1e-10, rtol=1e-9`沿适用范围保留。高阶剖面比较沿637—639的原门槛，新增指标在运行前说明依据。

检查配置、曲面/波长归属、capping和范围边界、文件清理、成功/失败/取消、保存重载、模型/solve/评价函数恢复及关闭。现有边界诊断测试通过与其中`boundary_acceptance`数值分别报告。

## 文件与交付

Gradium/GRIN专题模块、新增参考和测试归本任务。`analyses.py`三类GRIN函数、`analysis_models.py`及调度接入的修改单列共享补丁。资源副本与报告进入任务独立目录。

交回正式定义/接口、单变量结果、逐点高阶误差和边界状态矩阵、实际设置、代码及测试、原生生命周期和状态建议。未解决问题分别写出缺口和解除条件，保持原有数值门槛与别名计数。

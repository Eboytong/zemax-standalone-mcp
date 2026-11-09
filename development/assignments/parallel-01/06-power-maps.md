# D004 两种屈光力 Map：后续任务书

日期：2026-11-08。分派给已有 `zemax-p01-material-model`，保留会话、工作区和分支。MaterialModel控制探针保留为待原生作业，结果返回后仍由该worker处理。

## 声明范围与已知缺口

处理 `CV-02.PowerFieldMapSettings` 与 `CV-02.PowerPupilMapSettings`。现有 `power_field_map/power_pupil_map` 已通过正式POWF/POWP查询返回屈光力/EFL、坐标、原始值、分页和图像。当前关键缺口为内部环采样的状态出口及零EFL定义。

先读 `development/plan.md` 第7节、`development/current.md`、`development/remaining-ranked.md`、两份台账对应行、`src/zemax_mcp/power_maps.py`、`tests/unit/test_power_maps.py`、五份相关原生用例及 `development/evidence/CV-02/power-maps-value-state-repeat20261108.md`。本机历史原件从主项目的 `.local/runs/runs/power596_value_states_77609bd128` 与 `power593_aperture_ring_12774d2086` 只读取得。

## 首阶段计划

1. 核对公开请求、POWF/POWP参数编号和数据类型定义、原生设置/结果出口、中心参考光线有效性及环状态。按实际成员和正式手册列结论。
2. 审查历史实验已排除的假设，区分数学零、无穷焦距、原生失败返回零及未执行查询。保留当前 `raw_value_state/native_zero_semantics/native_ring_validity` 的事实。
3. 针对剩余定义列最多三类可区分控制实验，说明哪些可由原始结果离线完成，哪些需新正式原生出口。原参考与容差逐项引用原测试，先固定再执行。
4. 若形成实现依据，提出独立模块/最小共享补丁、普通测试、适用文档和原生作业；若正式出口不足，给具体缺项及解除条件。

第一阶段只交计划与离线审查，不改产品代码。保存 `.local/coordination/power-maps-plan.md`，报告具体下一步。数值无依据时保留原始状态；外部阻塞条目继续挂起，工作计数按完整声明范围决定。

## 原生排期与交付

所有新原生作业由runtime维护单队列，协调者在常规执行器运行。当前受控连接在 `application_create` 超时，后续原生等待具体新条件。功能worker提供精确命令、环境、输入、独立输出、时限及关闭判据。共享入口修改由runtime依审查结论集成，全局台账/批次由协调者更新。

原生申请、实现和第7节证据分别交付；保留MaterialModel文件与结论。后续任务优先继续复用本worker。


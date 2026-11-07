# 当前批次交付规则

自0.1.56之后采用每十项集中验收，记录见development-batches.json。逐项保留相关普通/原生/数值/资源关闭及文档验收；累计十个去重完成条目再执行全量普通回归、跨模块原生回归、wheel构建、独立安装和stdio冒烟。首批目标0.1.57。阻塞不计完成，批次失败先修复，最后不足十项在整体收口时检查。以下旧版本记录保留历史归属。

0.1.44补充：CAD交付采用扩展设置回读和关闭后文件检查；安装目录为`.local/evidence/development/RL-01/wheel-install044`。原生CAD格式设置用例支持ZEMAX_TEST_WHEEL_DIR；全量普通1666通过，538项原生待执行，详见release044.json。六条联动的原生状态沿用下表。

# 六类发行验收流程

0.1.43 为六类流程补齐六条同会话阶段传递入口，见 `tests/test_release_handoffs_live.py`。机器可读清单为 `.local/evidence/development/RL-01/workflows043.json`，包含输入、固定判据、组件测试及handoff_node。状态均为 implemented，实际原生运行待恢复。

| 流程 | 同会话传递 | 固定检查与当前范围 |
| --- | --- | --- |
| 顺序优化与全视场评价 | 优化后镜头→光斑/MTF评价→直接光斑→保存重载 | native480通过；优化值<=原值*1.001+1e-10；光斑对照abs1e-8+rel1e-7；扫描恢复和solve保持 |
| 非球面与偏心建模 | EvenAspheric+偏心倾斜→局部sag/全局矩阵→光线→重载 | 已通过原生用例：面前变换读取前一LDE矩阵索引；重载光线坐标/方向abs1e-8+rel1e-7；证据native479-modeling-workflow.xml |
| 图像与偏振镀膜 | 原生可编辑膜层→0.9倍厚度→偏振成像→保存重载 | native481通过；膜层系数abs1e-12+rel1e-12；UsePolarization回读、图像分页/导出；Fresnel数值由组件用例提供 |
| NSC照明与路径 | 同次追迹→探测器和ZRD→路径→联合报告 | native482通过；1W受控输入；路径通量与探测器abs1e-8+rel1e-7；对象状态保持 |
| POP耦合 | 输出ZBF→同一模型文件接收器→分页/图像/报告 | 同场重叠=1，功率与耦合abs5e-4；高斯传播等独立参考由组件用例提供 |
| 公差与制造交付 | 灵敏度→同一模型STEP/可视化→联合报告和镜头保存 | 两次导出前后模型设置保持；文件/三角网格及报告可读；Monte Carlo样本到制造文件的关联仍待扩展 |

29个组件及联动用例收集通过，记录 `.local/evidence/development/RL-01/collection053.txt`。本轮实际原生运行0项。已有隔离初始化在180.578秒超时；环境或授权变化后先完成连接诊断，再串行运行。

恢复后可直接运行六条联动：

```powershell
.venv/Scripts/python.exe -B -m pytest -q tests/test_release_handoffs_live.py --junitxml=.local/evidence/development/RL-01/native-handoffs.xml
```

在独立安装包上运行六条联动时，先设置已安装目录：

```powershell
$env:ZEMAX_TEST_WHEEL_DIR = (Resolve-Path '.local/evidence/development/RL-01/wheel-install043').Path
.venv/Scripts/python.exe -B -m pytest -q tests/test_release_handoffs_live.py --junitxml=.local/evidence/development/RL-01/installed-native-handoffs.xml
Remove-Item Env:ZEMAX_TEST_WHEEL_DIR
```

support.native使用隔离Python入口选择该目录并检查实际导入位置，worker沿用该目录。已通过实际stdio的断连能力查询和正常退出，证据installed-launcher053.json。其他历史组件测试保留各自启动方式；完整清单中的测试须按其实际来源记录。

每条用例输出calls/checks，阶段任务编号通过联合报告关联。finished辅助函数查询最终任务状态，核对cleanup_warnings、可取得的close_attempted、活动任务与运行列表。关闭尝试字段在调用发生后才出现；纯复合任务的资源释放须查看子任务。图像临时资源在finally清理；缺少可编辑膜层时写出resource-condition.json并报告具体资源条件。

2026-11-07：RL-01.modeling/sequential/imaging/nsc.Workflow 原生验收完成，分别见 `native479-modeling-workflow.xml` 至 `native482-nsc-workflow.xml`。建模矩阵探查确认面前坐标变换由前一LDE索引返回。POP与公差制造流程仍待原生运行。

原有基线与完成项的历史证据关联补充见acceptance-review043.json、baseline-review043.json、solve-done-review043.json及property-done-review043.json。234个implemented/blocked操作和分析条目的原始条件汇总于remaining-gates043.json，当前六条原生联动仍待执行。


2026-11-05：B001十个去重功能条目集中验收完成，交付0.1.57。全量普通1843通过、587原生跳过；独立安装wheel上的串行原生14通过；真实stdio公开100工具、94分析类型。原生用例覆盖本批设置、数值、分页、图像、保存重载、失败/取消及关闭。证据.local/evidence/development/BASE-04/release057.json及batch-B001.json。FRU警告和FullFieldSpot结果出口限制保留原状态。B002从0/10继续，每项定向检查，满十项再集中验收。


2026-11-06：B002十项集中验收完成，发行0.1.58。全量普通1889通过、605原生跳过；独立安装wheel原生17项通过，真实stdio100工具/96分析类型，正常关闭。证据.local/evidence/development/BASE-04/release058.json、batch-B002.json。QuickYield偏差、矩阵光斑出口、高阶Annular运行预算及既有阻塞保留具体状态。B003从0/10继续；每项定向检查，满十项集中验收。

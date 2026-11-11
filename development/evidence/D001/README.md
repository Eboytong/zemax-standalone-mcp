# D001 Gradient2/Gradient3交付记录

日期：2026-11-10。源码基线`fc814ef`及当前未提交工作区；产品版本1.0.0。解释器为主仓`.venv/Scripts/python.exe`，导入主仓`src/zemax_mcp`，原生24.2.0/build 240529。

## 实现和请求

复用`update_surfaces/get_surfaces/run_analysis:grin_profile/run_batch_ray_trace`。能力清单登记两种面型，`grin_surfaces`和曲面结果`grin`返回系数名称、编号、单位与公式。新增写前检查：参数1至8、正积分步长及正原点项；面型切换后重新取得曲面对象。请求schema保持原字段。

参数说明及工具请求见[用户指南](../../../docs/topics/modeling/grin.md)。当前工具名称与返回结构继续可用，`grin`为新增结果元数据。

## 输入和计算

独立新建毫米模型：物距10、GRIN厚度2、出射空气厚度2、半口径0.5，波长0.55/0.635 µm。八参数、实际值、solve、保存路径、每次请求和返回在原始记录中。Gradient2常数项2.25，Gradient3常数项1.5；完整高次项和轴向项在测试中固定，局部修改Nr2后保存重载。Variable回读并由原生优化器确认恰好1个变量，优化器在finally关闭。

剖面采用X从−0.5至0.5、Y=0、Z=1，每波长101点，独立按原生多项式计算。Gradient2比较平方根，Gradient3比较直接多项式。步长0.02/0.01/0.005，每次追迹5条归一化瞳光线，比较后两档位置和方向。

| 面型 | 最大折射率误差 | 最大位置差（mm） | 最大方向分量差 |
| --- | --- | --- | --- |
| Gradient2 | 4.440892098500626e-16 | 4.163336342344337e-16 | 5.551115123125783e-17 |
| Gradient3 | 2.220446049250313e-16 | 3.6637359812630166e-15 | 6.418476861114186e-16 |

门槛：折射率`1e-10+1e-9*abs(reference)`，位置`1e-5 mm`，方向`1e-7`。两种面型均通过。每档5条光线均成功，剖面和批量追迹任务均succeeded。

## 检查与生命周期

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_grin_specialized.py tests/unit/test_modeling.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d001-final
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_grin_specialized_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d001-native-final
```

结果51项普通检查通过，1项原生综合检查通过（20.24秒）。覆盖局部修改保持、有限数、非法编号/步长/原点项、面型切换solve保护、保存重载、变量数、两波长剖面、光线收敛和断开。首两轮测试分别发现测试模型退出面未确认替换Automatic solve、测试调用遗漏request包装；修正测试后通过。早期失败记录保留。

最终原始证据：`.local/runs/runs/grin_specialized_f72a7026d1/evidence.json`，含调用、实际参数、全量光线、模型及`application_closed=true`。分析和批量追迹使用既有任务关闭机制；原生优化器直接关闭，最后disconnect。通用任务的取消/恢复沿用已有测试，本项专属回归未新增取消用例。

## 来源与结论

参考G4 `50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3` 的`grin_surface.py`，核对n²/n和系数身份；按本项目已有通用单元格接口独立实现元数据与检查，未复制外部源码。原生公式和成员探查复用[四项记录](../native-feature-portability-20261110.md)。D001声明范围完成，下一项D002。

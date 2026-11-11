# D002 双向曲面镀膜R/T/A

日期2026-11-10；主仓`C:/Users/tonge/Desktop/mcp`，基线`fc814ef`及当前修改，Python为主仓`.venv`，源码来自主仓`src`。原生24.2.0/build 240529，PremiumEdition。新增同步工具`get_coating_rta`，当前源码102工具、132分析请求；发行包仍为1.0.0。

## 合同、成员和输入

顺序曲面编号正整数，1至120个条件，波长编号/微米波长互斥，省略采用主波长，角度0至89.9度，方向inward/outward。使用`ILDERow.GetCoatingPerformanceData()`、`ICoatingPerformanceData.GetCoatingPerformance(AOI,wavelen,DirectionOfRayTravel)`；核对SurfaceNumber。曲面持有对象，无独立分析工具和关闭入口。输出原生S/P、等权非偏振系数、能量残差、介质身份、单位和配置。错误保留失败条件与已完成结果，非有限值标记状态。

裸界面：平面空气/N-BK7，SCHOTT，两个波长0.55/0.635 µm、两个角度0/30度、两个传播方向。另用自有随机名称DAT构造n=1.38、物理膜厚0.1 µm的无损膜，以及消光系数−0.02的吸收膜。自有文件在测试结束删除，副本随运行记录保留。独立Fresnel及单层复振幅参考见`tests/native/test_coating_rta_live.py::reference`，采用输入侧介质及Snell角、S/P导纳、复相位和功率系数。

## 结果

真实stdio执行三类模型共24个条件，额外覆盖outward 60度全反射、显式波长、非法波长拒绝后复用、当前主波长默认选择。196项数值断言全部通过，最大误差`8.881784197001252e-16`，最大闭合残差`4.440892098500626e-16`；系数门槛`1e-8+1e-6*abs(reference)`，闭合`1e-8`。三种模型查询前后曲面、系统设置和修订号一致。guarded_work及常规收尾两次disconnect均成功。

原始记录：`.local/runs/runs/direct_coating_rta_004fb54565/{calls.json,checks.json}`，内含全部请求、配置、资源、原生返回、参考和误差。同步查询无长任务取消状态；现有dispatch串行和忙状态保护继续适用。

## 检查与异常定位

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_coating_rta.py tests/unit/test_coatings.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d002-unit
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_coating_rta_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d002-native-absorption
```

普通111 passed，原生1 passed（20.97秒）。普通检查覆盖参数范围、主波长、明确波长、方向、接口缺失、归属不符、原始异常和部分结果。

首轮自有资源名称未被原生接受，缩短为大写标识后成功。第二轮MATE消光项+0.02导致T=1.0343692292302569、R=0.012495559292503254、A=0及残差−0.046864788522760215；独立复数参考复现同一增益结果。改用−0.02后完成吸收参考。两轮失败原始结果分别保留于`direct_coating_rta_ca9dab7d7d`、`direct_coating_rta_ccc170a48c`。最终结论沿实际输入和数值结果判定。

参考G3 commit `a7375ba48235b2db71ae40766dbc1969c0671401`的`GetCoatingRtaTool.cs`，读取其条件、双向接口及S/P处理方法；本项目独立实现Python适配和参考，未复制外部源码。用户参数、结果及例子见[镀膜指南](../../../docs/topics/imaging/coatings.md)。D002完成，下一项D003。

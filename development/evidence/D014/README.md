# D014：多目标候选搜索

2026-11-11，已完成。扩展既有 `run_multistart_optimization` 的有类型 `pareto` 设置，保留普通多起点调用。

## 计划与实现

对显式MFE目标行指定目标、尺度、误差上限及正权重组合，枚举起点×权重网格。原生优化行权重为weight/scale²；以abs(native value−target)/scale为各维目标，计算可行性、违反量、非支配集合和支配关系。每个候选保存ZOS，结束或失败/取消均恢复基线。时间预算传入当前原生任务；候选上限200。

## 环境、输入与执行

主仓fc814ef及当前工作区修改，源码版本1.0.0；Windows x64/Python3.14/OpticStudio24.2.0 build240529 Premium。参考既有D008候选结构和原生多起点优化模块。

受控输入为原生Paraxial面，初始焦距50mm，参数1为Variable；瞳径2mm、550nm、像距50mm。MFE两行EFFL分别以40/60mm为目标，scale均20mm，权重9:1、1:1、1:9；10轮原生DLS。解析加权平方差最优值为42/50/58mm。第一项目标最大误差12mm，使58mm候选不可行。

最终命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_pareto_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d014-close --junitxml=.local/evidence/development/D014/close.xml
```

结果：1 passed/19.26秒。相关普通测试95 passed/3.84秒，含解析支配/重复/约束筛选、请求边界和缩放溢出、既有多起点/评估/协议/台账回归。

## 数值与生命周期

原生折中值41.9999999997263、50、58.0000000000684mm；12次数值对照最大差2.74e−10mm，沿用绝对1e−5+相对1e−7的解析最优值门槛，重载复算沿用1e−8+1e−7×参考值。三个候选逐一重载复算；可行前沿编号[0,1]，第三项归一化违反量0.3000000000034。

原生设置目标/权重/操作数身份回读、每个优化子任务succeeded及close_attempted、分页、PNG导出并查看、实际取消、微小预算失败、越界候选失败、基线曲面/变量/MFE恢复、应用正常disconnect全部通过。

原始证据：`.local/runs/runs/pareto_search_61b17c421e` 的calls.json/checks.json/pareto-result.json/pareto.png及候选ZOS；测试输出`.local/evidence/development/D014/close.xml`和`close.txt`。早期通过记录native/final保留。当前前沿为已评估可行候选的结果。

用户说明：[多目标候选搜索](../../../docs/topics/analysis/pareto-search.md)，请求例子`examples/requests/pareto-search.json`。D015成本预算和D016闭环控制已完成，参见对应交付记录。

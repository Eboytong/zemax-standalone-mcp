# D006 固定膜系多条件原生优化

2026-11-11，主仓`C:/Users/tonge/Desktop/mcp`，源码fc814ef及工作区修改。发行1.0.0；源码102工具/136分析请求。主仓.venv、Python3.14，pytest/conftest与真实stdio均显式导入主仓src。OpticStudio24.2.0/build240529、PremiumEdition。

## 交付范围与正式接口

新增`run_analysis:coating_optimization`，固定材料/层数，空气—目录玻璃单界面，两方向、系统或显式微米波长、0—89.9度入射、S/P的R/T/A目标、权重、膜厚倍率边界、有限周期及时间预算。使用独立CopySystem副本，源曲面、配置、solve、系统设置和修订保持。最佳候选另存ZOS。

正式路径：ILDECoatingData.SetLayerSettings/ThicknessMultiplier/SetThicknessStatusVariable；MCE.GLSS/YFIE建立介质和入射角配置；MFE.CONF/CODA建立目标及六通道性能，CMGT/CMLT施加边界；Tools.OpenLocalOptimization使用DLS或OrthogonalDescent。设置逐项写入并回读，最终倍率严格核对边界，目标与原生终态分别记录。

基础探查的单层Variable使优化器Variables从0变为1。双向30°控制中，CODA正向S反射0.020736121404307115，反向0.05130782749266879，介质实际回读为空气→N-BK7及N-BK7→空气。MCE字符串通过正式Value属性设置；Python侧StringValue附加属性不改变原生单元格，探查改用项目已有的写入和回读方法。

## 输入、参考、容差与实际结果

自有短大写DAT材料：L折射率1.38，H折射率2.1，0.4—0.8µm常数；SCHOTT N-BK7基底。三个膜系：ONE绝对厚度L=0.1µm；REL相对厚度L=0.25波长、系统主波长0.55µm；TWO为L=0.1µm/H=0.08µm。L起始倍率0.6，H为1；倍率范围0.2—1.8。输入DAT副本与完整请求保存在原始目录。

独立复数2×2特征矩阵逐层相乘，按横向波矢计算S/P光学导纳；反向反转介质和层序，N-BK7采用独立Sellmeier计算。原生系数对照容差沿D002：`1e-8 + 1e-6×|参考值|`。最终116次数值比较，系数最大绝对误差`5.928590951498336e-14`。

| 模型 | 条件与优化 | 结果 |
| --- | --- | --- |
| ONE | 550nm、法向S反射，DLS 10周期 | 倍率0.9963767226131133；四分之一波参考0.9963768115942031，差8.8981e-8；MSE 0.0005322711049174306→0.00016151398143708718 |
| REL | 主波长550nm、目标650nm，OrthogonalDescent 50周期 | 倍率1.1818181839498647；参考1.1818181818181817，差2.1317e-9；MSE 0.0007454035920914252→0.00016910893046449244 |
| TWO | 500/550/650nm、0/20/25/30°、双向、S/P、R/T/A，DLS 10周期 | MSE 0.003935795954692698→0.0005335458823261465；原生Succeeded=true，边界全部满足 |

附加最优倍率检查容差预设为`1e-5 + 1e-5×|参考值|`。REL的DLS10周期先得到1.1817682812766843，与参考差4.9901e-5，超限；改用正式OrthogonalDescent50周期达到上述误差，保留原失败记录。公开调用仍按请求预算和算法执行，结果记录改善幅度及终态。

## 相对膜厚出口差异与处理

REL起始倍率0.6、主波长550nm、查询650nm时，GetCoatingPerformance反射率0.023171422067367373；CODA为0.027302080361969218。独立计算分别对应按查询波长和系统主波长换算的相对膜厚。本机ICoatingPerformanceData只有角度、波长、方向三个参数，没有另设参考波长成员。

最终工作流统一使用CODA的固定主波长物理膜厚评价，保留直接API原值及逐条件差异。绝对膜厚的两个出口在数值精度内一致。已补充get_coating_rta的参考约定元数据及用户说明。REL最佳模型保存重载后，用同一原生工作流的基线性能复算，六通道保持一致。

## 检查与生命周期

- 最终定向普通检查155 passed/0.76s：类型边界、目标定义、膜层保护、设置失败关闭、原错误保留、MCE精度、已有镀膜/直接查询、优化及台账。
- 最终真实stdio原生检查1 passed/25.64s：三个膜系、两算法、两方向、三个波长、多角度、三类强度指标、候选保存重载和相对厚度重算。
- rows分页与PNG导出通过，ONE/REL/TWO图已生成，TWO图已查看。
- 无效波长99返回INDEX_OUT_OF_RANGE，原曲面保持，随后有效调用成功。
- 实际取消任务`1c91b65fabbc4852b8bfbc779b2a4898`终态cancelled；当时已创建的bench关闭，candidate尚未创建；cleanup_errors为空。源曲面、层值/状态及系统设置完整保持，取消后直接查询成功。
- 所有成功优化的bench/candidate关闭，子优化工具close_attempted记录随native_task保存，末尾disconnect成功。原生退出偶见FRU__delta_init提示，显式关闭/断开结果为成功。

最终回读补测：`.local/runs/runs/coating_optimization_native_b7845c66a6`；同样116次数值比较通过，包含候选UpdateStatus后全部膜层数值回读。

原始主证据：`.local/runs/runs/coating_optimization_native_17fb4db0af/{calls.json,checks.json}`及会话`46abdbb94c1444a6a94767ca18b2e5f2/`的任务JSON、ZOS、PNG。绝对膜厚前轮成功证据为`coating_optimization_native_c657ffdea3`。相对厚度差异与DLS精度失败分别保存在`coating_optimization_native_6f5b85bf2e`、`coating_optimization_native_d3f1fc236f`。

正式成员探查及官方手册摘录：`.local/evidence/development/D006/native-probe.json`、`probe_native.py`、`optimizing-coatings-manual.txt`。官方2024R2手册1389页确认倍率上限10及CODA/CMGT/CMLT。早期探查误用while清空MFE，原生保留最后空行导致循环；仅终止已确认归属的自有Python及子OpticStudio进程，后改为单次RemoveOperandsAt，后续会话正常关闭。

复现命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_coating_optimization.py tests/unit/test_coatings.py tests/unit/test_coating_rta.py tests/unit/test_configuration_cell_precision.py tests/unit/test_standalone_optimization.py tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d006-affected
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_coating_optimization_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d006-relative-descent
```

## 参考与完成结论

复用G3固定commit `a7375ba48235b2db71ae40766dbc1969c0671401`中GetCoatingRtaTool.cs的角度/波长/方向思路及本项目D002适配，优化目标和配置组装依据本机正式接口与官方手册独立编写。本项未复制外部源码。用户说明在docs/topics/imaging/coating-optimization.md，请求示例在examples/requests/coating-optimization.json。

D006本合同完成。玻璃—玻璃、镜面基底、自动增删层和材料排列保留独立后续范围；当前介质条件不符时返回UNSUPPORTED_COATING_MEDIA并关闭副本。下一项D007：先确认纯NSC的NCE变量、原生优化器及探测器目标，再实现效率/ROI均匀性工作流。

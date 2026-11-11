# D007：纯NSC效率、均匀性、扫描与原生优化

2026-11-11；主仓`C:/Users/tonge/Desktop/mcp`，源码fc814ef及当前修改。发行1.0.0：101工具/132分析；当前源码102工具/137分析。主仓.venv、Python3.14，pytest和真实stdio显式导入主仓src。原生OpticStudio24.2.0/build240529、PremiumEdition；原生执行串行。

## 声明范围与实现

新增`run_analysis:nsc_efficiency`。纯NSC、选定光源、空间矩形探测器ROI、无前缀W；源功率、ROI功率/效率、总体CV（含零像素）、热点/无效像素、物理面积/辐照度；NCE位置、角度、源功率的1—3轴扫描与原生局部优化；最佳候选加密、多种子复算、排名、分页、曲线/网格、ZOS保存重载。

所有写入和探测器清空在CopySystem自有副本中执行。源系统、源探测器缓冲区、配置、原有solve、修订保持。副本的原Variable先固定，仅本次指定变量参与优化。未选光源分析光线数设0，保存候选保留该选择及最后一次加密采样。多探测器分别相对同一源功率计算，返回重复计数标志；排名取各ROI效率或CV均值。

正式接口：NCE.ObjectColumn/MakeSolveVariable；源ObjectData.Power、NumberOfAnalysisRays；Tools.OpenNSCRayTrace、SetRandomSeed、ClearDetectors；MFE.NSDD/NSTR/OSUM；NPGT/NPLT、NPXG/NPXL及对应Y/Z和角度约束；Tools.OpenLocalOptimization；GetDetectorData、SaveAs、Close。

局部优化目标为ROI总功率目标及逐像素均匀目标残差的加权平方平均，CV独立返回。原生NSDD(-4/-5)只统计非零像素，故采用逐像素读取计算包含零值的CV。每个原生设置按活动条件写入和回读；副本更新后再次核对候选变量。原生优化最终严格检查边界，保留原生merit及工作流目标的不同归一化。

## 输入、参考、门槛与结果

输入由测试自建，无外部模型依赖。四个SourceRay位于`(±0.5,±0.5,0) mm`、沿+Z，每源0.25W；探测器Z=10mm、半宽1mm、2×2像素。基础10光线/源，复算40光线/源、种子42/43/44。SourceRectangle另用1W、半宽1mm、8×6探测器，1000→4000光线、种子42/43。

1. 四源总功率1W、每像素0.25W、效率1、CV0；1×2非方形ROI功率0.5W。功率门槛`1e-8 W + 1e-6×参考值`。
2. X位置`[-2,-0.5,2] mm`、TiltY`[0,2] deg`、源功率`[0.125,0.25] W`产生12个扫描节点，加初始共13候选；最佳效率1。两条rows分页通过。
3. 单源目标接收0.4W，X位置/TiltY/Power三变量、OrthogonalDescent50轮：功率`0.399999999983486 W`，误差`1.6514e-11 W`，目标误差`0.0225→2.72705e-22`。最终几何值`X=-0.200792769167938 mm`、TiltY`=-0.381695960830458 deg`，均在请求边界内。
4. 单源、4像素、目标0.4W，像素均匀性权重1，总功率权重1。独立最优值由`(P-0.4)^2+(P-0.1)^2+3×0.1²`求导得`P=0.25 W`，原生/保留候选为0.25W；工作流加权误差0.015。零像素包含在CV中，CV与导出的网格独立计算一致。
5. 两种优化候选保存并重载后，源功率与接收功率复算通过。规则模型17次数值对照最大误差`1.6514e-11`；矩形源4次对照最大误差`3.33e-16`。各项容差保存在checks.json，未放宽。
6. SourceRectangle同一设置/种子的两次执行像素完全相同；本机确定性源在种子42/43下输出也相同，功率波动0。源功率及接收均为1W；记录1000/4000光线的网格与CV。

## 探查与失败定位

- 原始功率探针：纯NSC源Power(Par3)可设Variable，优化器变量数1，目标0.4W得到`0.3999999999314121 W`，误差`6.86e-11 W`。工具关闭和应用断开成功。
- NSC的MFE Surf列由模式固定，写入会拒绝；保留原生模式固定值，实际参数从Det#/Src#等活动列写入。
- NCE角度枚举是TiltX/Y/Z。首轮把行属性名TiltAboutY用于列枚举失败，已修正，失败原始结果保留在`nsc_efficiency_native_faa964272a`。
- SourceRay.RandomSeed暴露为Boolean，正式RandomSeedCell支持整数。NSTR对支持该参数的源使用正整数种子（请求0时映射1）；独立追迹先清除该局部种子，再用工具SetRandomSeed。SourceRectangle无RandomSeedCell，采用原生NSTR确定性采样；三次MFE像素差0。每次优化前两次MFE复算差大于1e-12W即停止并报告。
- 三变量DLS10轮保留0.25W，未达到0.4W参考；改用正式OrthogonalDescent50轮达到既定门槛。失败证据`nsc_efficiency_native_a4bbae23f8`。原生优化收敛随算法/周期报告实际值。
- 源Rectangle不同种子输出相同的观察保存在`nsc_efficiency_random_80af3741ce`；后续检查按确定性采样记录实际波动，种子差异不作为强制随机性假设。
- 通用网格绘图以min_x/min_y表示第一个像素中心；已按该约定修正ROI绘图元数据，并通过独立原生补测和网格导出。

## 生命周期、检查与原始证据

定向普通测试180通过，涵盖请求边界、类型、目标、CV、无效像素、候选排名、副本关闭及关闭失败时原始错误保留。真实stdio三项原生用例通过：规则光线/扫描/优化（含保存重载、原模型及探测器保持、失败/取消/复用）、矩形源采样、预算及最终回读/网格导出。

- 主验收：`.local/runs/runs/nsc_efficiency_native_d9a02f9bbe`，与矩形源`.local/runs/runs/nsc_efficiency_random_e67143a83e`，2项共144.32秒。calls.json末尾disconnect均ok，所有copy_closed=true；实际取消终态cancelled、cleanup_errors空；越界ROI为INDEX_OUT_OF_RANGE，副本关闭，后续复用成功。
- 预算及更新回读：`.local/runs/runs/nsc_efficiency_budget_a0e9aa0208`，1项20.72秒；0.0001秒总预算返回BUDGET_EXCEEDED，副本关闭。TiltX扫描随后正常运行，源模型保持。
- 最后像素中心/ROI图像补测：`.local/runs/runs/nsc_efficiency_budget_6d86fd16f4`，1项21.38秒通过；roi.png已查看，坐标范围与物理ROI一致。
- 探针及官方手册摘录：`.local/evidence/development/D007/{probe_native.py,probe_random.py,native-probe.json,native-random-probe.json,nstr-manual.txt,source-random-seed-manual.txt}`。首探错误被后续原地修订的JSON覆盖，先前失败原因保留本记录；实际命令来自本轮工具记录。

命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_nsc_efficiency.py tests/unit/test_nsc_analyses.py tests/unit/test_nsc_provenance.py tests/unit/test_detector_regions.py tests/unit/test_detector_adapters.py tests/unit/test_standalone_optimization.py tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d007-affected-final
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_nsc_efficiency_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d007-native3
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_nsc_efficiency_live.py::test_nsc_efficiency_budget_and_final_readback --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d007-grid
```

参考：本机OpticStudio2024R2英文手册1119—1129页（NSC约束、NSDD/NSTR）、572页（SourceRay随机种子）；G2固定commit`193598e4ca6224dfa8615565d5e3b6f3cfa6d149`的nsc.py，参考其OpenNSCRayTrace、探测器读取和finally关闭组织；本项优化和指标独立编写，未复制外部代码。

结论：D007声明范围完成。下一项D008玻璃贡献与自动替换试验；累计7/16，集中检查仍按10项或阶段收尾执行。

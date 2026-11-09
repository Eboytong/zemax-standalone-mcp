# D008 SagTable：等价表示与DSAG采样控制

2026-11-09本机执行；源码0.1.62，101工具/132分析；OpticStudio24.2.0 build240529 PremiumEdition。主仓.venv，进程COMPLUS_LoadFromRemoteSources=1；原生串行。MF-01.SagTable及MA-01.SagTable别名共享本证据与状态。

## 声明范围、正式依据和实验计划

完整范围仍包括三种BFS准则、制造偏移/面型适用性及反向制造摘要。本轮定位等形Zernike面带偏移RMS半径超限。

手册3.4.2.1/906页渲染后确认只有工具提示；详细制造定义在7.5.3/1307—1309页。最小RMS可固定顶点或允许偏移；MinimumVolume按空气侧选取材料去除方向；反向改变选取侧；去除深度/体积摘要仅适用MinimumVolume。DSAG的Data9/10为球面半径/局部坐标Z偏移，Samp1—5为33、65、129、257、513方格。详细摘录在`.local/evidence/development/MF-01/sag-manual-20261109/`。本轮没有取得报告章节、面号或TestPlate目录的新选择依据，沿用既有明确接口记录。

假设一：原生拟合初值受基底曲率影响。固定解析z=.0126r²，半口径5 mm，conic=-1，使用R40、R80、Infinity及补偿二次项.0001、.00635、.0126，分别构造EvenAspheric/ZernikeFringeSag。Zernike保留1项、归一化半径5、piston0。每个模型先检查17个解析矢高，再以四点SSAG BFS2重建球面并读DSAG9/10。

假设二：DSAG的网格采样改变BFS或随后SSAG的缓存。固定各面型R40，逐次改变Samp1—5，比较DSAG9与随后同点SSAG。其余条件保持。

## 参考、容差与结果

独立参考沿用256节点Gauss-Legendre径向面积积分及独立曲率优化：半径39.84003968804416 mm。原半径绝对容差5e-6 mm；解析矢高容差1e-8 mm+1e-6×绝对参考值。

本轮另计算目标方差和对曲率的梯度作为定位信息：delta=z-sphere−weighted_mean(z-sphere)，d(sphere)/dc=r²/[sqrt(1−c²r²)*(1+sqrt(1−c²r²))]，目标梯度为−2*weighted_mean(delta*d(sphere)/dc)。该信息不替换原半径门槛。

| 面型 | 基底半径mm | 原生拟合半径mm | 绝对误差mm | 原门槛 |
| --- | --- | ---: | ---: | --- |
| EvenAspheric | 40 | 39.840039682554824 | 5.48933e-9 | 通过 |
| EvenAspheric | 80 | 39.84003968257937 | 5.46478e-9 | 通过 |
| EvenAspheric | Infinity | 39.84003968259844 | 5.44572e-9 | 通过 |
| ZernikeFringeSag | 40 | 39.84000130347164 | 3.83846e-5 | 超限 |
| ZernikeFringeSag | 80 | 39.84000130345247 | 3.83846e-5 | 超限 |
| ZernikeFringeSag | Infinity | 39.84000129913844 | 3.83889e-5 | 超限 |

102个矢高点全部通过。EvenAspheric梯度约−2.5e-13至−9.9e-13；Zernike约6.45e-7。两个面型在五档网格下半径和随后SSAG值各自完全相同。所测基底表示、33至513网格及此前归一化半径/零系数项数均未解除差异；内部拟合算法和面型相关数值误差尚无正式解释。独立参考方向与原门槛保持。

## 命令、检查与生命周期

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/MF-01/sag_fit_initialization.py .local/evidence/development/MF-01/fit-initialization-20261109
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/MF-01/sag_fit_initialization.py .local/evidence/development/MF-01/fit-sampling-20261109 --sampling
```

原始目录各有完整probe.json，含请求、实际曲面、模型条件、原生值、独立参考、误差、保持和关闭。直接查询没有创建分析工具或任务，不填写不存在的task_id；后端会话生命周期有实际关闭回执。第一轮会话4f6d2244ec5247feb8a3f761ff008930，第二轮79edffea3a3846668c1158361e3f6a5a。八模型的曲面、系统设置和评价函数前后保持；两轮shutdown检查点成功、native.closed=true、forced=false、error=null，进程退出码0。原生既有FRU警告出现。

定向普通命令：`.venv/Scripts/python.exe -B -X utf8 -m pytest tests/unit/test_sag_table.py tests/unit/test_sag_fit.py tests/unit/test_contracts.py tests/unit/test_development_status_report.py -q -p no:cacheprovider --basetemp=.local/tmp/sag-fit-controls-20261109 --junitxml=.local/evidence/development/MF-01/fit-initialization-20261109/unit.xml`；92 passed，0.90秒。

本轮更新get_capabilities的受控模型拟合验收范围，工具请求schema保持。有类型请求、分页、取消、恢复、保存重载和图像沿用现有测试；本轮直接诊断不重复宣称这些范围已新验收。

## 结论与下一动作

SagTable保持implemented。下一步需要正式面型相关BFS算法/精度依据或修复，再按原参考复验；制造偏移局部坐标基准及反向摘要继续保留为独立缺口。取得新依据前继续D009实际格式/版本及配置分层。完整验收4/10，剩余92组。

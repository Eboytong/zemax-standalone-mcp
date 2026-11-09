# 相位像差：离轴、Jones与波长控制

2026-11-09；条目PO-01.PhaseAberration、D001。源码0.1.62主仓`C:/Users/tonge/Desktop/mcp`，101工具/132分析；本轮未构建安装包。原生OpticStudio24.2.0/build240529、PremiumEdition，项目venv，COMPLUS_LoadFromRemoteSources=1。

## 本项计划与声明范围

在[轴上相邻参考](phase-neighbor-reference-20261109.md)之后，分别改变Jones、Y视场及波长，检验参考插值与固定相位符号。先运行有类型模型及几何算法普通检查，再串行执行四组受控输入；原误差门槛保持1e-6度，即2.7777777777777776e-9 waves。

四组均从官方Cooke工作副本开始，通过正式SystemPatch改变模型字段和波长、设置Jones，再从原生报告读取实际输入。这是受控模型实验，公开PhaseAberration请求仍为kind-only；专题本身的选择器范围继续保留。

## 实际输入与原生结果

各组将系统设为单波长、主波长1；保留三个视场，首视场Y为0或5度，其他字段沿用。Jones X初相位0度，Y初相位如下。原生表头实际采用视场、Jones及波长；0.4861327µm在四位小数表头显示0.4861，批量和GetIndex使用实际单波长全精度值。

| 受控输入 | 首视场Y/度 | 波长/µm | Jx/Jy/Y相位 | 非中心比较数 | 沿光线起始参考最大误差/waves |
| --- | ---: | ---: | --- | ---: | ---: |
| axis_circular | 0 | 0.55 | 1/1/90° | 1600 | 5.826789593356418e-10 |
| offaxis_y | 5 | 0.55 | 0/1/0° | 800 | 5.984475137665868e-10 |
| offaxis_circular | 5 | 0.55 | 1/1/90° | 1600 | 6.074477522551025e-10 |
| offaxis_second_wave | 5 | 0.4861327 | 1/1/90° | 1600 | 6.44428983049769e-10 |

14个中心零值单独记录。offaxis_y的X分量共802点因主分量零振幅保留indeterminate；其余5600个非中心点均通过原门槛。

## 参考假设与首轮超限

批量追迹的几何位置通过GetGlobalMatrix转到全局坐标，段光程按前一介质GetIndex与逐段距离计算。受控系统物方为无限远、Angle视场、无镜面；Y-Z平面入射方向为(0,sinθ,cosθ)。

首轮沿用波面投影起始项`n0*(direction dot r_first)`。离轴弧矢方向通过，子午方向残差约0.499 waves；原始结果保留。该项为波面相位参考，而本次比较需要分离批量电场的沿光线传播相位。

后续可区分假设为从共同Z平面到首交点的沿光线起始项`n0*z_first/direction_z`，常数起始Z在减主光线时抵消。两种假设差值由独立几何与方向直接计算，不使用native表值拟合。保留`raw + propagation + native`符号，并以独立±0.005瞳点相位的圆周平均作参考。离线重放后四组全部通过原门槛。

正式资料：2024 R2手册Phase Aberration、p.904描述相邻光线插值；IRayTraceNormPolData、p.1704–1705说明Jones、电场与归一化追迹；Field vs. Ray Phase Conventions、p.128讨论沿光线相位。API章节未明确无限远归一化追迹的共同起始Z平面，本轮将其作为四组控制支持的起始相位模型，继续保留其他对象共轭、坐标变换及镜面条件的适用性验收。

## 命令与产物

原生入口`scripts/probes/PO-01/phase_conditions_reference.py`；离线参考入口`phase_conditions_replay.py`。`phase_propagation_reference.py`新增显式起始参考参数，默认原算法保持；探针并列保留两种预测。后续重跑新入口会同时计算两种参考。

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/PO-01/phase_conditions_reference.py .local/evidence/development/PO-01/phase-conditions-native-20261109
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/PO-01/phase_conditions_replay.py .local/evidence/development/PO-01/phase-conditions-native-20261109/probe.json .local/evidence/development/PO-01/phase-conditions-native-20261109/launch-reference-replay.json
```

原生命令执行时探针尚未加入第二种起始参考；probe.json因此保存首轮预测，launch-reference-replay.json保存后续离线预测。第二条命令没有创建新原生会话。

## 终态、恢复与关闭

原生36个任务均succeeded，每组一项专题、一次偏振追迹和七次逐面几何追迹；各有分页回执。四组各自执行前后系统设置和曲面一致；每组结束重开官方输入、核对原系统设置和完整曲面回读，四次恢复均通过。主仓及官方输入文件均由既有工作副本机制使用。

会话c41fb161b2a34141830ada959e5ddf7e完成shutdown检查点，native.closed=true、native.error=null、forced=false，进程exit_code=0。FRU__delta_init警告仍原样保留。当前无活动原生任务。本轮未新增取消、原生失败后复用或保存重载检查。

## 普通检查

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_phase_conditions_reference.py tests/unit/test_phase_conditions_replay.py tests/unit/test_phase_propagation_reference.py tests/unit/test_phase_reference_diagnostics.py tests/unit/test_phase_aberration.py tests/unit/test_native_controls.py -q -p no:cacheprovider --basetemp=.local/tmp/phase-conditions-final-20261109 --junitxml=.local/evidence/development/PO-01/phase-conditions-20261109/unit-final.xml
```

最终98 passed in1.80s，初轮89项另存unit.xml，集合重叠。覆盖正式请求构造、视场归一化、入射方向、两种光程基准、跨周期插值、分页数据归属、错误几何以及参考不随native数据拟合。

## 状态与下一步

四组控制扩展了轴上结果，支持当前固定符号和沿光线起始参考的数值对应。PO-01.PhaseAberration保持in_progress；还需正式专题输入选择或覆盖声明范围的正式替代路径，并验任意模型适用性和完整生命周期。不得据此把工作副本中的模型改动当作已交付的分析选择器。

下一项依D001组内顺序检查偏振光线/光纤正式输入依据；已有相同AS_Default缺口沿用，取得新路径再验。D002及后续有新依据的条目继续领取。完整验收累计4/10、剩余92组保持。

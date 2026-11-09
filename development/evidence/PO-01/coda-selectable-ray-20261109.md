# CODA可选偏振光线数据

日期：2026-11-09。条目PO-01.PolarizationRayTrace，D001。源码0.1.62工作树；OpticStudio24.2.0 build240529 PremiumEdition；Python3.14。

## 计划和正式接口

目标为补充专题原生AS_Default缺少的场、波长、曲面及瞳点选择，同时保留默认报告。先核对正式参数、实际列类型及结果映射，再对照批量偏振追迹。

2024 R2手册印刷页1130列出CODA，字段含场、曲面、波长、归一化瞳坐标及Data。手册规定Data负值在涂层数据1—7时表示S偏振，正值表示P。公开调用为MFE.GetOperandValue(CODA,... )。本机临时行回读列顺序为Surf、Wave、Field、Data、Px、Py，前四Integer、后两Double，其余槽位无效。证据摘录位于`.local/evidence/development/EXT-EXPORT/manual042.txt`；探针为`scripts/probes/PO-01/polarization_operand_contract.py`。

60次控制查询覆盖默认场/瞳、第二视场、中心瞳、像面/第一面及Data=101—106、110—113；无原生调用错误。实际设置、评价函数、曲面保持，临时行移除。原始记录：`.local/evidence/development/PO-01/polarization-operand-contract-r2-20261109/probe.json`。

## 实现和检查

新增`method=auto/native/operand`。默认kind-only沿用原生逐面文本；显式选择参数时auto转CODA，operand强制调用，native与选择器并用时拒绝。参数包括正整数field/wavelength、surface（0像面，正数顺序面）及[-1,1]内瞳坐标。结果返回24种CODA量、实际场/波长/曲面/瞳点、系统Jones、原生参数及rows分页。

定向普通测试：`tests/unit/test_polarization_ray_trace.py`、fiber operand与fiber耦合设置，共66通过。原生检查命令：

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
& ./.venv/Scripts/python.exe -B -X utf8 -m pytest --run-zemax -q tests/native/test_polarization_topic_reference_live.py::test_polarization_ray_coda_selects_field_wave_surface_and_matches_batch_field --junitxml=.local/evidence/development/PO-01/polarization-coda-native-r2-20261109.xml
```

1项通过，18个实数比较覆盖表面1、表面2和像面三个E复分量。容差为`1e-6 + 1e-6×|reference|`，实测最大误差0。输入为自建平板、空气、N-BK7材料模型Nd=1.5/Vd=60/dPgF=0，波长0.5876µm、中心场、瞳点(0,1)、系统Jones(0,1)。CODA E复值与同设置正式批量偏振追迹完全一致。页`start=14,count=3`与完整结果一致，任务succeeded且无cleanup warnings；系统设置和曲面不变。

真实stdio记录位于`.local/runs/runs/polarization_coda_7409105054`；disconnect返回connected=false，`close_receipt.json`记录native.closed=true、forced=false、error=null。早期失败复现也保留在`.local/evidence/development/PO-01/polarization-coda-native-20261109.xml`。schema通过`scripts/development/export_tool_schemas.py`重新导出。

## 当前范围与后续

默认专题、CODA选定曲面的偏振量及对应输入选择现可调用。该操作数一次选择一个曲面；批量覆盖全部逐面专题表仍沿用原生默认报告。任意偏振光线的相位参考独立于本次复电场对照，沿用PhaseAberration剩余状态。整组完整验收计数不变，须完成声明范围和相位/生命周期条件后再更新。

## 逐面字段对照与相位单位修复

2026-11-09追加：同一平板模型的原生逐面报告与CODA在面1、面2及像面完成63项比较，包含S/P反射率、透射率、吸收、场振幅反射/透射实虚部、Ex/Ey/Ez复分量及非零分量相位。系数采用1e-9+1e-8×参考值，吸收1e-9，复场沿用1e-6+1e-6×参考值，相位包裹差采用1e-6度。63项全部通过；相位最大包裹差2.00089e-11度。

本轮发现CODA的110—113原生值为弧度，而原适配标记为度；已在输出的_deg字段转换，native_queries继续保留原值，并增加native_phase_unit=radians。失败证据polarization_coda_0b3fde0947及coda-topic-fields-20261109.xml保留。修复后普通66项通过，真实stdio用例1项通过(11.88秒)，XML为.local/evidence/development/PO-01/coda-topic-fields-fixed-20261109.xml；调用记录.local/runs/runs/polarization_coda_b4e186b9dc。关闭回执native.closed=true、forced=false、error=null。

生产字段名称与请求保持，新增单位转换普通断言检查原生值未被覆盖。完整状态继续in_progress；下一项覆盖非中心选择、非零Jones相位、失败/取消及复用。


## 选择矩阵、相对相位及取消复用

2026-11-09追加。源码0.1.62工作树、项目内Python3.14、OpticStudio24.2.0 build240529 PremiumEdition。用例为`tests/native/test_polarization_topic_reference_live.py::test_polarization_coda_selection_matrix_reload_and_cancel`。命令沿用上节COMPLUS_LoadFromRemoteSources=1及项目src的PYTHONPATH，pytest加`--run-zemax -q -p no:cacheprovider`；最终XML为`.local/evidence/development/PO-01/coda-selection-matrix-relative-20261109.xml`，1 passed，16.33秒。

输入为自建半径20 mm、厚5 mm的折射面及平面出射面，材料模型Nd=1.5/Vd=60/dPgF=0；视场0/5度，波长0.4861/0.6563 µm，Jones幅度(1,1)、Y相位37/90度，归一化瞳点(0.25,0.4)，像面CODA Surf=0。八个组合逐一与正式批量偏振追迹的三个复电场分量对照，另以atan2核对XYZ相位；110相对相位符合X相位减Y相位，按360度包裹后比较。复场门槛1e-6+1e-6×参考值，相位1e-6度，保存重载24个量门槛1e-10+1e-10×参考值。104项比较全部通过，最大绝对差5.684341886080802e-14（相位度）；首轮未含XY补充的96项比较误差为0。

原始记录`.local/runs/runs/polarization_coda_selection_matrix_df76bb13f4`含calls.json、checks.json、请求与工作模型。场/波长实际编号通过；越界场3返回INDEX_OUT_OF_RANGE；取消请求时进度8%，轮询到终态后再次运行及保存重载成功。系统设置及曲面保持；disconnect为ok=true/connected=false，关闭回执native.closed=true、forced=false、error=null。早先矩阵记录f18d7ba26d及XML保留。

补充普通检查覆盖第二个查询非有限值、原生异常及首个查询后取消：均立即停止后续查询，保留已完成行；非有限值归属到s_transmittance，原生异常文本保留。相关普通69项通过（0.53秒）。生产适配改用已导入math.isfinite，公开请求保持。

当前完整状态仍in_progress。剩余条件缩减为：任意选择下完整逐面几何/基底/传播字段及全局坐标的正式结果路径，和该完整路径的失败恢复。CODA目前覆盖24种选定面偏振量，默认专题覆盖原生默认光线完整逐面报告；已有选择矩阵、相位单位及取消复用无需同条件重跑。后续取得专题正式选择键或覆盖全部字段的正式替代路径后继续；先推进D002现有独立波长归属用例。


## 补齐正式CODA全部数据码

2026-11-09续。重新核对本机2024 R2手册印刷页1131（完整CODA说明，另见1140页同义列表），发现0、8、121—123共五个正式结果尚未接入。新增polarized_transmitted_intensity、unpolarized_transmitted_intensity、ellipse_major_axis、ellipse_minor_axis、ellipse_angle_deg，保留原24行顺序并追加五行。共有29种结果；0/8为累计透射相对强度，121/122为投影XY电场椭圆半轴，123原生单位为度。110—113继续从弧度转换；原始查询值保持。native_ellipse_angle_unit=degrees明确标注，get_capabilities同步结果与单位。

普通69项通过（0.52秒），包含123不被重复角度转换的断言。默认逐面报告对照1 passed（12.04秒），XML为.local/evidence/development/PO-01/coda-complete-codes-20261109.xml，输入及原门槛沿前述同一平板；补充累计强度、长短轴及周期180度方向角。

扩展选择矩阵原生1 passed（17.88秒），XML为.local/evidence/development/PO-01/coda-ellipse-intensity-20261109.xml。原始目录.local/runs/runs/polarization_coda_selection_matrix_324ad63df1。八组条件与前节相同，增加：累计偏振功率与正式批量偏振追迹；非偏振功率与两正交单位Jones追迹强度平均；椭圆由独立复场矩阵解析求解。Ex/Ey取批量追迹结果，S0=|Ex|²+|Ey|²，S1=|Ex|²-|Ey|²，S2=2Re(Ex conjugate(Ey))，两半轴为sqrt((S0±hypot(S1,S2))/2)，方向角为atan2(S2,S1)/2。退化圆形按特征值差判定方向是否可定义。轴长门槛1e-8+1e-7×参考值；方向角1e-6度；功率1e-9+1e-8×参考值。

149项比较全通过；16项功率最大误差0，27项名称含ellipse的比较最大误差6.59383658785373e-12（含角度），36项相位最大5.684341886080802e-14度；29项重载结果误差0。取消实际到达cancelled，随后复用成功。模型设置/曲面保持，disconnect ok=true、connected=false，关闭回执保留。完整专题选择与全局坐标缺口保持，未增加完整功能计数。schema请求无变化。

最终定向普通检查：test_polarization_ray_trace.py、test_fiber_operand.py、test_fiber_coupling_settings.py及test_development_status_report.py共89 passed（0.71秒）。按手册p.131的局部XY投影定义，修正默认报告units.ellipse此前“相对于较大分量”的错误描述；数值保留原生值。新增单测固定该定义。

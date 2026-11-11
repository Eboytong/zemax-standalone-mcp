# D010：鬼像与杂散光路径诊断

2026-11-11，完成。源码基于fc814ef及当前未提交工作区，102工具/140分析请求；发行1.0.0保留101工具/132请求。Python3.14、OpticStudio24.2.0/build240529、PremiumEdition。执行解释器为主仓.venv，stdio子进程显式导入主仓src，原生串行。

## 范围与正式接口

run_analysis:ghost_diagnostics使用CopySystem独立副本、OpenNSCRayTrace偏振分光、GetDetectorData和OpenRayDatabaseReader。逐源设置分析光线数；原生追迹设置写入回读；候选材料、位置及逐面镀膜检查solve，UpdateStatus后再次回读最终组合。每个候选保留自有ZOS/ZRD，源对象、修订和探测器缓冲保持。

ZRD按SegmentParent重建到达探测器的祖先树。由父段入射/子段出射方向与法线点积符号判反射，定位有序反射面组合。期望序列优先，再分散射关联、鬼像、允许及其他；原生RayError、缺失祖先、筛选、段数/路径上限及阈值单独保留。总探测器功率与ZRD单精度残差按原值返回。原生MinimumRelativeRayIntensity等追迹条件保存在native_trace_limits。

候选保留至少基线期望功率的minimum_expected_fraction（默认0.9），然后最小化非期望探测器功率。单候选资源错误保留，基线必须成功。成功/失败/取消均关闭工具、数据库和副本。

## 输入、参考和容差

自建1W偏振SourceRay，2条分析光线，种子42；z=5mm处2mm厚N-BK7平板，半宽10mm；z=12mm处3×3像素、半宽2mm吸收探测器。SCHOTT.AGF的400nm Sellmeier系数和IT透射率记录独立读取；IT参考厚度25mm，按T=T25^(2/25)转换。

独立公式R=((n-1)/(n+1))²，主路径=(1-R)²T，代表双次内反射鬼像=(1-R)²R²T³。预设容差1e-8W+1e-6×|参考|。期望序列2.1→2.2→3.0；鬼像反射面顺序2.2、2.1。

## 结果与生命周期

- 定向普通94 passed/0.64s：请求边界、有限值、父树、功率分账、原生错误段、最终回读拒绝，及PathAnalysis/NSC效率/台账消费者。
- 最终真实stdio原生1 passed/27.50s；14数值比较全部通过，最大绝对差1.8968e-8W。
- 主路径0.9133573770523071W，参考0.9133573835024565W；鬼像0.0017656332347542048W，参考0.0017656332328456576W。
- 探测器0.915123015401945W，ZRD到达和0.9151230102870613W；原生PathAnalysis两条到达路径与ZRD汇总相同。
- N-F2材料替换、探测器移开、缺失镀膜及理想高透镀膜候选分别验收。I.99999999采用后主路径0.9553903341293335W，代表鬼像为0，满足通量保留条件并选为最佳。镀膜定义来自本机COATING.DAT的I.transmission说明。
- max_paths、相对功率阈值、max_segments、H3筛选、rows分页、PNG导出及查看、最佳模型保存重载通过。原始模型/修订和探测器缓冲保持；failed/cancelled实际终态后副本全部关闭；末次disconnect ok=true。

最终原始记录：.local/runs/runs/ghost_diagnostics_native_7849ab0e1d，含calls.json、checks.json、fresnel-reference.json、ghost-powers.png和ZOS/ZRD。探查材料位于.local/evidence/development/D010：slab-probe.json、workflow-probe.json、native-limits-probe.json、coatings-probe.json及对应脚本。

## 诊断过程保留

300nm目录透射率为25mm厚度0.05，代表鬼像被原生默认最小相对强度0.001截断；初次6946c60e55及0db7aafe42保留。正式400nm精确IT节点工况通过。I.0按本机目录定义是零透射，46391b8028记录通量资格拒绝；改用正式高透I.99999999完成候选复算。上述均保持原容差。

## 复跑与参考

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_ghost_diagnostics.py tests/unit/test_path_analysis.py tests/unit/test_nsc_efficiency.py tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d010-affected
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_ghost_diagnostics_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d010-native5
```

GitHub参考G2的NSC追迹组织、G5固定commit6a197e467c7fceeb51ab651b3dbea21d9781d94e的杂散光诊断组织；本模块独立实现实际ZRD到达分账，Fresnel及吸收参考由本机AGF系数独立计算。正式面设置和关闭路径由本机DLL及探查确认。后续先执行D001—D010十项集中检查，随后D011。

十项集中检查已完成：[检查汇总](concentrated-checks.md)。3662普通、14原生及安装包1原生通过；原生会话已结束，继续D011。

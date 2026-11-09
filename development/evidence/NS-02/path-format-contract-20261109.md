# D007路径分析：ZRD/PAF实际设置采用

日期2026-11-09（本机）；源码0.1.62，101工具/132分析；原生24.2.0 build240529 PremiumEdition。主仓.venv，进程COMPLUS_LoadFromRemoteSources=1，原生与stdio串行。

## 范围、正式依据与输入

NS-02.PathAnalysis声明范围为ZRD/PAF路径、范围、过滤、阈值、功率分类及生命周期。本轮确认两种数据库对阈值/光线范围的实际采用，修复设置回读成功但结果未采用的请求处理。

本机手册1023页定义低于相对阈值及超过10000唯一路径的部分进入uncategorized；阈值为支路末端/该支路发射能量。摘录在`.local/evidence/development/D007/path-semantics-20261109/manual-1023.txt`。正式INSCRayTrace具有SavePaths/SavePathsFile和SaveRays/SaveRaysFile。本轮在自有工作模型同一次追迹同时生成PAF和ZRD，避免分别追迹导致输入差异。

单路径：1 W、10-ray SourceRay，.55 µm，Jx=1/Jy=0；N-BK7 RectangularVolume z5、厚2 mm；DetectorRectangle z12、7×5。多路径：第一源.8 W穿过X半宽1 mm玻璃，第二源.2 W位于x3直接命中同一探测器。偏振true、split/scatter false、单核、seed42，Filter为空。完整请求和实际设置在两份probe.json。

## 原生结果

| 输入 | 设置 | ZRD | PAF |
| --- | --- | --- | --- |
| 单路径 | 默认 | 1条，.9167180210351944 W | 1条，.9167180036560986 W |
| 单路径 | 阈值1 | 0条；原生TotalFluxOut=1 W | 仍1条，功率同默认 |
| 多路径 | 默认/阈值.5 | 2条，.9333744272589684 W | 2条，.933374402925266 W |
| 多路径 | 阈值1 | 仅直达路径，.19999999552965164 W | 仍2条，功率同默认 |
| 多路径 | 光线1—10 | 仅源1，.7333744317293167 W | 仍2条 |
| 多路径 | 光线11—20 | 仅源4，.19999999552965164 W | 仍2条 |

PAF各项写入及最终回读均成功，结果未随所测阈值或范围变化。两格式所有案例GetPathUncategorized均报There are no uncategorized paths。ZRD TotalRays保留原始值，例如范围1—10时为11；不重新解释为命中数。

独立参考为正式read_zrd返回的HitObject=3段Intensity求和。单路径功率差1.73791e-8 W，多路径差2.43337e-8 W，均通过既有1e-8 W + 1e-7×绝对参考值。筛除功率未取得原生未分类出口，完整范围继续implemented。

## 实现与请求

path_models.py对PAF仅接受默认first_ray=1、last_ray=-1、relative_minimum_flux=0和空filter；其他组合修改前给出具体条件错误。ZRD原请求及阈值行为保留。请求字段的schema说明、能力查询及路径专题已同步。默认例子及拒绝例子见examples/requests/path-database-controls.json。

探针保留原生独立调用分支，用于复现被公共合同拒绝的PAF设置；执行路由写入新记录。公开调用沿既有run_analysis链路。未分类异常、原生总计及分类行保留其来源。

## 命令和检查

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/NS-02/path_format_contract.py .local/evidence/development/D007/path-format-multipath-20261109 --multipath
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_path_analysis.py tests/unit/test_remaining_adapters.py tests/unit/test_contracts.py tests/unit/test_task_artifact_metadata.py -q -p no:cacheprovider --basetemp=.local/tmp/path-paf-20261109 --junitxml=.local/evidence/development/D007/path-format-multipath-20261109/unit.xml
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/NS-02/path_paf_stdio.py .local/evidence/development/D007/path-format-multipath-20261109/probe.json
```

普通101 passed，1.64秒。受影响ZRD真实stdio回归test_path_sources_threshold_reload_and_recovery为1 passed，13.13秒；XML为path-format-multipath-20261109/native.xml，调用记录为`.local/runs/runs/paths063_threshold_1e9ed69e43/`。真实stdio成功记录`.local/runs/runs/path_paf_adoption_5b6703db24/`：五个非法请求返回协议错误，默认两路径功率两次通过独立参考，1行分页连续，保存重载后保持，任务succeeded且close_attempted=true；设置、对象及评价函数前后相同，disconnect成功。前两轮脚本错误分别为get_nsc_objects漏request包装、误将协议校验错误当structured_content；原始目录653fabba29和5c5a83ebd8保留。

## 终态、关闭与下一步

原始单路径记录`.local/evidence/development/D007/path-format-contract-20261109/probe.json`：会话d69d947d9a674bd6a35dfe42a1c30309、修订4；四任务及ZRD读取成功。多路径记录`path-format-multipath-20261109/probe.json`：会话629c6b3ad6f4498d8b0ccc032ad3ff9b、修订4；十任务及读取成功。两轮设置、对象、评价函数及配置保持，shutdown检查点成功、native.closed=true、forced=false、error=null。原生退出既有FRU警告出现，进程退出码0。

本轮完成PAF静默忽略处理和默认读取验收。完整条目保持implemented，下一步取得阈值排除后的未分类有效出口或正式修复依据，并以原独立功率门槛复验。完整计数仍4/10、剩余92组。随后推进D007散射正式选择对照。

# D009 IGES实际层号采用修复

2026-11-09，源码0.1.62，101工具/132分析；OpticStudio24.2.0 build240529 PremiumEdition，主仓.venv，COMPLUS_LoadFromRemoteSources=1。原生与stdio串行。

## 声明范围与实施计划

EXT-EXPORT.CadMultipleConfigurations要求配置选择、几何、实际层号、模型保持和关闭；CadSettings包含可用格式、设置和实际版本。本轮修复显式顺序透镜层号未采用却成功返回的结果处理，完整分层支持仍需原生实际采用。

正式IExportCAD的LensLayer、RayLayer、SetConfigurationAllByLayer/AllAtOnce/AllByFile及Close沿现有实现。手册46—47页规定首配置使用请求层，后续配置递增；摘录保存于`.local/evidence/development/EXT-EXPORT/iges-adoption-20261109/manual-cad-layers.txt`。没有新增ACIS版本、ASAT/ASAB、线框/ZBB/ZEC工厂的正式依据，沿用此前实际拒绝与公开类型探查。

先保持既有双配置平面圆柱模型，层10/11与合层10分别比较；另用官方Cooke工作副本请求层10，验证明确拒绝、保留输出、随后的STEP复用及模型保持。

## 实现与结果定义

exports.py新增iges_layer_metadata：在原生导出器确认关闭后，读取IGES首个Directory Entry记录的第5字段（33—40列），保留原始层号集合、条目数和负数间接层引用。作用范围为Sequential、显式lens_layer、number_of_rays=0。NSC的布局光线由光源控制，不根据其请求number_of_rays=0推断无光线。

- 单文件all_by_layer预期为lens_layer至lens_layer+配置数−1，其余单文件模式预期为指定层。
- all_by_file逐个输出读取指定层，保留每文件metadata。
- 非零请求层比较时排除辅助层0，全部原始层号仍保留。
- 直接层号不符返回SETTING_REJECTED，包含请求、实际、输出path；文件保留。
- 负数间接层引用返回SETTING_UNAVAILABLE及原始指针；无DE或损坏字段返回INVALID_RESULT_DATA。
- 省略lens_layer、含光线或NSC场景沿用既有回读范围。

公开请求字段保持；能力说明和示例已更新。没有将IGES文件重新分层，也没有用getter替代输出实际采用。

## 命令与检查

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_cad_multiple_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/iges-adoption-native-20261109 --junitxml=.local/evidence/development/EXT-EXPORT/iges-adoption-20261109/native.xml
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_cad_multiple_live.py::test_iges_layer_rejection_and_reuse --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/iges-adoption-native-r2-20261109 --junitxml=.local/evidence/development/EXT-EXPORT/iges-adoption-20261109/native-r2.xml
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_cad_adoption.py tests/unit/test_contracts.py tests/unit/test_task_artifact_metadata.py tests/unit/test_development_status_report.py -q -p no:cacheprovider --basetemp=.local/tmp/iges-adoption-final-20261109 --junitxml=.local/evidence/development/EXT-EXPORT/iges-adoption-20261109/unit-final.xml
```

普通首轮69 passed，最终121 passed、1.06秒。覆盖直接层号、0辅助层、间接引用、空目录、关闭后读取、逐文件成功/拒绝以及既有CAD/任务/状态消费者。

原生首轮1 failed、1 xfailed，24.62秒。双配置STEP current/single/all_by_layer/all_at_once/all_by_file五种几何、配置及关闭断言执行通过；两项IGES输出仍65535，任务已明确拒绝，原有完整分层数值断言保持xfail。原始`.local/runs/runs/cad169_multiple_8129181a1a/`。

新增拒绝/复用测试首轮失败原因：测试直接比较原始层集合[0,65535]与[65535]，未排除已定义的辅助层0；产品已按同一规则明确拒绝。修正测试后重验1 passed，11.74秒。成功目录`.local/runs/runs/cad_iges_adoption_18fa3c1fa1/`：显式层10返回SETTING_REJECTED，输出文件保留；随后STEP成功；曲面、系统设置及评价函数保持，失败任务close_attempted=true、无cleanup_warnings，正常disconnect。初轮目录cad_iges_adoption_7dfc182322及失败XML保留。

各实际设置、请求、任务、错误和输出文件位置均在上述calls.json。源模型采用自有工作副本；原生退出仍有既有FRU警告，成功重验进程退出码0。

## 结论与下一步

完成显式顺序IGES透镜层号的静默忽略处理。原生配置分层仍blocked，解除条件为正式导出器输出请求的层号；ACIS版本及特殊格式沿原缺口分别记录。完整验收4/10、剩余92组。

下一步按D009后续正式协议、D011/D012 STAR与D013 HPC实际条件安排；前序有新接口或可区分控制时按D00x返回。已确认的同条件阻塞沿用原记录。

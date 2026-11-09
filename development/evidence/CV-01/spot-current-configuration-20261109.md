# 标准光斑参考合同与当前配置修复

2026-11-09。涉及CV-01.FullFieldSpot、CV-01.MatrixSpot、CV-01.ConfigurationMatrixSpot及既有标准/ThroughFocus光斑消费者。源码0.1.62工作树、项目Python；OpticStudio24.2.0/build240529/PremiumEdition，Sequential、Millimeters。完整验收计数增加0，当前4/10、剩余92组。

## 输入、请求与计划

官方Cooke 40 degree field工作副本；系统波长0.48/0.65 µm、权重1/3、主波长1。两配置使用MCE THIC面6，配置2厚度比配置1增加0.2 mm。原文件通过既有工作副本机制使用。

标准光斑合同18项：Centroid/ChiefRay/Middle/Vertex各配波长0/1/2；另测IgnoreLateralColor、多色方向余弦、配置选择2、Dithered和偏振。Field3、像面、RayDensity6、默认Hexapolar、DeltaFocus0；每项实际设置及模型修订保留probe.json。另运行活动配置1/2与原生Configuration选择器1/2的四组合，分离选择器与物理编号。

## 正式结果与缺口

StandardSpot文本及SpotData可读。两波长槽的15个统计getter均重复当前分析聚合值；单色统计需分别设置并执行。Get_X/Y/Z/L/M/N、Detector坐标和半径/参考点接口均无逐光线第三索引；八类通用结果集合为0。

Centroid RMS：多色13.593903200295003 µm、波长1为12.536889776665994 µm、波长2为13.821711738957097 µm。IgnoreLateralColor开启后该多色统计不变。DirectionCosines半径0.06643232012159338，无量纲。这些值用于合同和配置回归，未作为独立光学参考。

矩阵手册分面定义沿用[factory证据](spot-factory-outlets-20261109.md)。标准统计出口尚未覆盖逐光线散点、矩阵独立参考及全部原选项；两矩阵条目保持implemented。FullField共同参考/Exaggerate坐标同样继续等待可验证出口。

## 配置对照、原因与修复

| 活动物理配置 | 写入原生Configuration | RMS µm | 对应输出配置 |
| ---: | ---: | ---: | ---: |
| 1 | 1 | 13.593903200295003 | 1 |
| 1 | 2 | 13.593903200295003 | 1 |
| 2 | 1 | 19.57687223704524 | 2 |
| 2 | 2 | 13.593903200295003 | 1 |

选择器1在本受控模型中表示当前配置。选择器2的完整语义尚未确认；本次实际返回配置1。旧代码直接写物理配置编号，配置2因此被错算为配置1。

spot_topics.py统一CURRENT_CONFIGURATION_SELECTOR=1；backend.py标准光斑、FullField和analyses.py ThroughFocus采用该选择器并回读。标准光斑settings.configuration保留物理编号，新增native_configuration_selector；专题原生任务settings.resolved_configuration保留物理编号。公开请求未变化，设置拒绝路径关闭原生对象。

## 命令、检查与数值结果

直接合同命令：

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/CV-01/spot_reference_contract.py .local/evidence/development/CV-01/spot-reference-contract-20261109
.venv/Scripts/python.exe -B -X utf8 scripts/probes/CV-01/spot_reference_contract.py .local/evidence/development/CV-01/spot-configuration-contract-20261109 --configuration-only
```

两次原生均使用进程级COMPLUS_LoadFromRemoteSources=1。18项及4项任务均succeeded、close_attempted=true，无cleanup_failures；settings/surfaces/merit/configurations四类恢复true，两会话disconnect.connected=false。

修复相关普通56项通过；新增评价消费者后，以下92项通过，0.67秒：

```powershell
.venv/Scripts/python.exe -B -m pytest tests/unit/test_spot_configuration.py tests/unit/test_full_field_spot.py tests/unit/test_configuration_matrix_spot.py tests/unit/test_rms_analyses.py tests/unit/test_evaluation.py -q -p no:cacheprovider --basetemp=.local/tmp/spot-config-consumers-20261109 --junitxml=.local/evidence/development/CV-01/spot-configuration-contract-20261109/consumers.xml
```

真实stdio原生命令：

```powershell
.venv/Scripts/python.exe -B -m pytest tests/native/test_spot_configuration_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/spot-configuration-native-r2-20261109 --junitxml=.local/evidence/development/CV-01/spot-configuration-contract-20261109/native-r2.xml
```

修复后1项通过，终端14.09秒；XML suite记录14.050秒。四个数值比较分别为两配置原始对照、配置2重载、配置2零焦移，实际差均0，门槛atol=rtol=1e-6。此门槛用于配置回归一致性。原ThroughFocus任务实际selector1、resolved_configuration2；五面结果按−200/−100/0/100/200 µm返回，零面RMS19.57687223704524 µm。

首轮真实stdio测试因get_configurations遗漏必填request失败；修正为request={}后重跑。原native.xml及首次运行目录保留，未计为功能失败。fake首次缺New_Analysis方法的普通失败记录亦保留。

## 分页、图像、模型及关闭

真实stdio覆盖五面rows切片、PNG导出、配置2保存重载；焦移后系统设置、曲面、MFE和配置与基线相同。标准及ThroughFocus原生任务close_attempted且无cleanup_warnings；正常断开。PNG已查看，RMS/GEO图例、五点焦移轴和µm单位显示正常。既有FRU__delta_init警告保留原终端记录。

原始合同目录：`.local/evidence/development/CV-01/spot-reference-contract-20261109/`及`spot-configuration-contract-20261109/`。真实stdio最终目录`.local/runs/runs/spot-current-configuration_e8a83470c1/`，含configuration-reference.json、请求/任务、模型、图像和断开结果；首次目录`spot-current-configuration_e9d692f568/`。

下一步：矩阵/FullField取得正式散点或经完整参考定义验证的替代路径后继续；当前产品配置修复收口，转D005完整设置与输入身份。

后续位图实现共用能力入口后，最终相关普通292项通过，包含本次光斑92项及状态/请求合同。XML与完整命令见[D005证据](../D005/bitmap-intensity-20261109.md)；此前92和56项集合不累加为独立覆盖数。

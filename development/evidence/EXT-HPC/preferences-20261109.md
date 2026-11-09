# HPC preferences成功路径复测

2026-11-09；主仓源码0.1.62，主仓Python虚拟环境，进程设置COMPLUS_LoadFromRemoteSources=1。OpticStudio24.2.0 build240529 PremiumEdition。

计划：通过真实stdio读取非空正式IHPCSettings、六项实际字段及来源，审查查询只调用GetHPCSettingsFromPrefs且无工具factory；检查任务索引、断开及关闭证据。

普通命令：`python -B -m pytest tests/unit/test_hpc.py tests/unit/test_hpc_execution.py tests/unit/test_hpc_success_driver.py -q -p no:cacheprovider --basetemp=.local/tmp/hpc-unit-20261109`，45 passed。

原生命令：`python -B -m pytest tests/native/test_hpc_live.py::test_hpc_native_preferences_success_readback --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/hpc-native-20261109 --junitxml=.local/evidence/development/EXT-HPC/preferences-20261109.xml`，1 skipped in13.60s。

原始调用：`.local/runs/runs/hpc_settings_success_2dc65efdfc/calls.json`。原生GetHPCSettingsFromPrefs返回null，适配器返回HPC_SETTINGS_UNAVAILABLE；成功字段未取得。查询前后无新增任务、running_tasks为空。断开返回connected=false、requires_reconnect=false。该回执证明会话断开，独立原生关闭事件需从该次state目录读取。

源码路径hpc.prepare_hpc只访问Tools.GetHPCSettingsFromPrefs，不打开SystemTool；空对象不进入字段读取。FRU重复启动警告仍出现，原始终端保留。

EXT-HPC.Settings保持implemented，成功验收缺非空正式对象。解除条件：在可用配置下preferences工厂返回IHPCSettings；随后重跑同一成功用例，即使is_configured=false也可验收配置读取。节点作业单独依据配置与许可处理。本次新增完整验收0。

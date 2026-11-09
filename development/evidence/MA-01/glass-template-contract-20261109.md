# D002 玻璃图/消热差图替代模板正式合同探查

2026-11-09。计划：复用既有AS_Default和目录身份结果，补查所有导出公共类型及其成员，寻找替代模板、图表边界和参考玻璃选择；有正式入口才应用并回读，缺少入口时保留原生默认图及已有数值参考。

命令：COMPLUS_LoadFromRemoteSources=1，`.venv/Scripts/python.exe -B -X utf8 scripts/probes/MA-01/glass_template_contract.py .local/evidence/development/MA-01/glass-template-contract-20261109`，exit0。只加载已安装ZOSAPI_Interfaces.dll和ZOSAPI.dll，未创建应用；版本身份和完整匹配结果见同目录contracts.json。

导出成员扫描仅发现IMaterialsCatalog.ExcludeSubstitution、MaterialSubstitute求解接口及GlassMap/AthermalGlassMap分析枚举；未取得图表模板的参数、应用入口、ReferenceGlass或专用设置类型。ExcludeSubstitution属于材料记录的排除属性，不能据此认定已取得图表模板。

结论：两个图表默认调用、SCHOTT346/OHARA410身份、独立热光参考沿用已有证据；完整条目仍缺正式图表边界/替代模板和消热差ReferenceGlass设置。解除条件：提供正式文档/API设置或可可靠写入并回读的正式配置键；替代路径需取得模板条件并逐点证明同义后才能关闭条目。此次不重复创建空专题、未修改模型或资源，不增加完成数。

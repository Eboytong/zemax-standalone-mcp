# D009及STAR/HPC当前条件

2026-11-09本机执行；原始事件UTC 2026-11-08。源码0.1.62，原生24.2.0 build240529 PremiumEdition，主仓项目venv，COMPLUS_LoadFromRemoteSources=1。

## D009正式创建接口

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/PO-01/official_settings_inventory.py .local/evidence/development/EXT-EXPORT/export-contracts-20261109.json IOpticalSystemTools ExportCAD BlackBox ZBB Encrypt ZEC Linework`。

当前ZOSAPI_Interfaces导出908类型、137设置类型，命名匹配IOpticalSystemTools、IExportCAD、ISurfaceBlackBoxLens。公开方法和属性完整保存于JSON；BlackBoxLens用于已有黑盒面，当前扫描未取得线框、ZBB、ZEC创建工厂。本轮保留既有手册与接口探查，不据名称缺失排除全部可能的正式协议。三个条目保持blocked；需正式创建协议、参数、文件出口及生命周期依据后才能实施。

## D009实际导出

命令：`.venv/Scripts/python.exe -B -m pytest tests/native/test_cad_advanced_acis_live.py tests/native/test_cad_acis_live.py::test_native_acis_version_refusal_and_reuse tests/native/test_cad_layer_modes_live.py -q --run-zemax -p no:cacheprovider --basetemp=.local/tmp/cad-targeted-20261109 --junitxml=.local/evidence/development/EXT-EXPORT/cad-targeted-20261109.xml`。

3项诊断通过，51.50秒；诊断通过和格式/版本/层采用结果分别记录：

- 自建N-BK7双平面模型，ASAT/ASAB均TASK_START_FAILED / Unsupported export format，任务关闭且模型保持。原始`.local/runs/runs/cad521_advanced_acis_cf7fd22f7a/`。
- Cooke工作副本，SAT/SAB的V30 getter可接受，但文件头version_code=500，适配器返回SETTING_REJECTED；Current随后成功、实际500。失败关闭和复用、曲面与系统设置保持通过。原始`.local/runs/runs/cad185_acis_readback_5a3a8396db/`。
- 自建双配置模型，IGES实体/曲面两种模式分别对照all_by_layer与all_at_once；正式LensLayer等设置回读保留，四种组合实际均为[65535]，请求分别为[10,11]或[10]。每项任务关闭、配置/曲面/系统/MFE保持和保存重载通过。原始`.local/runs/runs/cad585_solid_surface_layers_a11176231b/`。

三会话均完成正常disconnect并退出stdio；实际失败和文件元数据保留。未改变原格式、版本或配置层声明，CadSettings保持implemented，CadMultipleConfigurations保持blocked。

## D011/D012当前许可与D013设置对象

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/BASE-04/native_scope_conditions.py .local/evidence/development/BASE-04/scope-conditions-20261109-r2`。

新建自有顺序系统。当前IsSTARModuleEnabled=false，get_star_data(surface1,deformation)返回FEATURE_UNAVAILABLE，partial_changes_possible=false。STAR各项的设置、受控FEA导入/拟合、组件和性能数值验收需启用该模块后执行；既有实现及各自独立参考缺口保留。

HPC分别请求preferences及custom(node_count1,Default)，GetHPCSettingsFromPrefs和GetHPCSettingsCustom均null；两项HPC_SETTINGS_UNAVAILABLE，partial_changes_possible=false。自定义配置查询不提交作业，本轮jobs_submitted=0；配置、许可、服务或版本各自对null的原因仍未区分。配置查询需要正式非空对象，四类作业还需节点条件及各自生命周期验收。

系统设置、曲面、评价函数保持，修订号保持1；未创建SystemTool或提交节点作业。会话4335cafa22eb437d8e735ee4adc2427f正常shutdown，native.closed=true、forced=false、error=null，checkpoint成功。首轮scope-conditions-20261109已采得相同原生条件，但探针末尾误用Backend.model_revision而报AttributeError，原始记录保留；修正为revision后重验完成。

原生启动已可用。STAR与HPC的条件分别作用于对应条目；不能继续使用旧application_create超时作为当前队列阻塞。反复FRU警告原样保留，原因未定位。

## 下一步

本轮D008/D009及条件查询没有新增完整验收，仍3/10、剩余93组。按D001—D006原优先级返回可区分假设的数值/正式接口工作；STAR30项等待模块，HPC5项等待非空配置及适用节点条件，D009缺口按上述具体输出及正式协议记录。每项条件变更后执行定向验收，累计10项后集中检查。

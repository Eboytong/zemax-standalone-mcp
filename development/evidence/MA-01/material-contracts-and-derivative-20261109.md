# 材料报告正式合同、目录身份及全精度色散控制

日期2026-11-09。D002：GlassMap、DispersionDiagram、DispersionvsWavelength。源码0.1.62工作树；本机Python3.14；OpticStudio24.2.0 build240529 PremiumEdition。

## 接口合同与来源

本机OpticStudio_UserManual_en.pdf的1349—1355页摘录及接口反射位于.local/evidence/development/MA-01/material-contracts-20261109。GlassMap固定使用d线Nd/Vd并搜索已加载目录；专题设置为折射率和Abbe上下限及替代模板。Athermal使用系统最小/中心/最大波长和材料参考温度，压力为1atm；专题设置含色/热功率边界、替代模板、参考玻璃。色散两专题支持最多四材料、波长范围、Y范围和温压选项。

本机AS_Default仍未提供上述专题设置，系统加载目录已能正式写入和回读。玻璃图不再要求不存在的专题波长选择。IMaterialsCatalog未提供任意波长求值；本轮通过正式ILDE.GetIndex读取全精度折射率。

## GlassMap目录复验

命令：设置COMPLUS_LoadFromRemoteSources=1，执行`.venv/Scripts/python.exe -m pytest --run-zemax -q tests/native/test_glass_map_live.py::test_glass_map_selected_catalog_identity --junitxml=.local/evidence/development/MA-01/glass-catalog-identity-20261109.xml`。1项通过，10.89秒。

原始目录.local/runs/runs/glass_map_catalog_identity_e7f5c5c62b含catalog-identity.json和calls.json。SCHOTT346/346、OHARA410/410均按AGF大小写归一匹配；七项旧缺口均为名称大小写差异。Nd/Vd沿显示精度原门槛5e-6/0.005。两次任务succeeded、close_attempted=true，系统设置保持，实际disconnect见calls.json。

## 色散全精度控制

输入SCHOTT/BK7G18，关闭环境修正，独立模型；101个原报告波长节点，各以中心及三组正负偏移取得7个原生折射率。固定半步长5e-5、1e-4、2e-4 µm，执行前写入探针；独立参考为SCHOTT AGF Sellmeier及解析导数。原解析/文本门槛5.1e-8不变。

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/MA-01/dispersion_step_identity.py .local/evidence/development/MA-01/dispersion-step-20261109-r2`，COMPLUS_LoadFromRemoteSources=1。

707个折射率对独立参考最大差2.220446049250313e-16。解析导数4点超限，最大5.9190213202997555e-8；波长0.408/0.416/0.432/0.488 µm。固定h=1e-4时101/101文本差分对应通过，最大4.921866580617773e-8；h=5e-5为98/101，h=2e-4为89/101。原生与独立差分的最大差为4.44e-12。有限差分对应提供算法诊断，正式导数定义仍待依据。

probe.json保存输入、系数、实际设置、707折射率、逐点误差、分页及任务终态。error为空，settings_restored=true、surfaces_restored=true、cleanup_failures=[]、disconnect.connected=false。首轮请求将primary置于波长项而被schema拒绝，已修正为系统级primary_wavelength；原失败保留于dispersion-step-20261109，恢复成功。r2成功后补充GetIndex返回数检查，已有101次返回均为7。

相关普通71项通过，XML：.local/evidence/development/MA-01/material-contracts-unit-20261109.xml。接口反射未创建应用。原生FRU警告继续保留原始输出。

## 状态及下一步

各条实现状态保持；完整验收4/10。GlassMap继续专题边界/模板的正式选择及回读；色散继续最多四材料、波长/温压选择与正式导数定义。下一项消热差缺CD/TD语义与受控温度对照。

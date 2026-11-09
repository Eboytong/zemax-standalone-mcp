# D002 DispersionDiagram 完整验收：可选择折射率曲线

2026-11-09，源码0.1.62工作树，Python3.14，OpticStudio24.2 build240529 PremiumEdition。声明范围为原生色散图的折射率随波长曲线，包括最多四种目录/表格玻璃、波长与显示范围、温压选择、有效结果和生命周期。

## 计划与正式定义

先复用默认专题及手册探查，再以正式ILDE.GetIndex补齐选择入口；以独立Sellmeier、热光/空气修正、ZTG节点及默认原生文本分别对照，最后验证分页、PNG、保存重载、取消和关闭。本机手册1347–1350页，摘录.local/evidence/development/EXT-EXPORT/manual042.txt，明确DispersionDiagram输出折射率；DispersionvsWavelength的导数属于独立条目。

AS_Default设置仅有IsValid/IsActiveWindow，保留kind-only原生文本入口。选择路径使用任务自有CopySystem，New(False)建立独立模型，正式写入/回读目录、材料、波长及Environment，分块调用ILDE.GetIndex，Close(False)释放副本。查询和副本SystemID完整保存在结果actual_settings/native_queries；源模型不修改。ZTG文件只读，插值由原生完成。

## 请求和结果

`{"request":{"kind":"dispersion_diagram","method":"index","catalog":"SCHOTT","glasses":["N-BK7","N-F2"],"minimum_wavelength_um":0.4,"maximum_wavelength_um":0.8,"samples":101}}`

温压关闭时默认20°C/1atm，启用后允许显式设置；折射率无量纲，波长µm。两个波长界限为0时采用所选资源范围的并集；每材料范围外返回null和valid=false。Y界限0表示该侧自动；采样2–2001含两端。表格玻璃使用Glasscat中的含扩展名ZTG文件名，例如TABLETEST.ZTG。rows/series均使用既有分页和结果文件；PNG支持Y显示范围。

## 最终原生与数值证据

命令：设置COMPLUS_LoadFromRemoteSources=1、PYTHONPATH为主仓src，执行`.venv/Scripts/python.exe -B -X utf8 -m pytest --run-zemax -q -p no:cacheprovider tests/native/test_material_index_live.py --junitxml=.local/evidence/development/MA-01/selected-index-table-20261109.xml`。

1 passed，16.03s；原始记录.local/runs/runs/material_index_selected_cfcac35d20，calls.json/checks.json包含请求、实际设置、修订、任务和关闭回执。550项对照全部通过：N-BK7/N-F2共202节点，独立SCHOTT AGF Sellmeier，绝对容差1e-12；原生默认BK7G18报告101节点，容差5.1e-8，最大4.966168343223387e-8；四材料30°C/0.8atm共28节点，独立热光/空气公式，容差1e-12；自动范围17个有效点同门槛、一个无效点为null；TABLETEST.ZTG波长与折射率各101节点，容差1e-12，折射率误差0。原331点核心验收的Sellmeier最大2.22e-16、热光最大6.66e-16。

series分页和Y范围PNG通过，既有图像已查看；主模型设置、曲面及评价函数保持。保存重载结果一致；2001节点任务实际cancelled、副本关闭，后续复用结果一致；缺材料/超范围返回具体资源错误。最终disconnect返回ok=true、connected=false、requires_reconnect=false。副本原生异常及关闭失败由普通测试覆盖，关闭失败要求重连。

## 发现及修复

自动范围首轮在N-F2范围外返回1.0；第二轮发现同批有效波长亦为1.0。现按每材料有效波长单独写入，再取得原生折射率；范围外不送入查询，公开结果为空值并保留资源范围。失败XML selected-index-auto-range-20261109.xml、selected-index-auto-range-fixed-20261109.xml和原始1d21c41bb7/2602442e90保留。修复后r3为1 passed/15.40s，最终表格玻璃版本通过如上。原始打印FRU警告保留。

最终定向普通检查105 passed/1.38s；命令为pytest -q -p no:cacheprovider tests/unit/test_material_index.py tests/unit/test_dispersion_diagram.py tests/unit/test_materials.py tests/unit/test_plotting_units.py tests/unit/test_development_status_report.py，XML位于.local/evidence/development/MA-01/selected-index-unit-final-20261109.xml。此前100项、自动范围版本101项通过。本条完成。独立导数专题仍需正式微分语义与完整选择验收，沿用原容差。

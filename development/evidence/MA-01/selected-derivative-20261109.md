# D002 DispersionvsWavelength：可选择色散导数完整验收

2026-11-09。源码0.1.62工作树，Python3.14，OpticStudio24.2 build240529 PremiumEdition。声明范围为最多四种目录/表格玻璃的dn/dλ、波长与显示范围、温压条件、分页输出及任务生命周期。

## 计划、定义与正式接口

复用手册1347–1355页、既有AS_Default反射和707点GetIndex控制，保留默认原生报告。新增可选择路径在任务自有CopySystem中写入并回读材料、目录、波长及Environment，用正式ILDE.GetIndex取得折射率，明确计算其数值导数。手册定义为dn/dλ；默认专题内部差分步长未公开。新路径采用预先固定的五点四阶差分，h=min(1e-4 µm,材料范围/8)，内部点中心差分，范围端点采用向内的五点单侧公式；各节点及权重随native_queries返回。

该路径是正式原生折射率的显式数值导数，computation_method=finite_difference_of_native_ILDE_GetIndex。默认原生报告的四点解析超限历史继续保留；新计算按同一5.1e-8 /µm解析门槛验收，使用独立定义覆盖材料选择范围。

## 请求、设置和结果

`{"request":{"kind":"dispersion_vs_wavelength","method":"finite_difference","catalog":"SCHOTT","glasses":["N-BK7","N-F2"],"minimum_wavelength_um":0.4,"maximum_wavelength_um":0.8,"samples":101,"minimum_dispersion":-0.5,"maximum_dispersion":-0.001}}`

kind-only auto保持原生文本路径；带选择的auto采用数值导数，native加选择明确拒绝。默认波长0.4–0.8µm、采样101、温压关闭、20°C/1atm。两个波长界限0采用资源并集；每材料范围外为null/valid=false。显示上下限0分别自动。单位1/micrometer，rows.dispersion及series保持材料请求顺序。ZTG资源身份和上下限从只读文件取得，折射率与插值由原生计算。

actual_settings记录资源、配置、源及副本SystemID、实际目录与环境；differentiation记录算法及边界规则，native_queries记录实际所有波长、折射率和差分权重。共享副本关闭和重连处理沿用色散图；原模型、solve、配置和评价函数保持。

## 定向检查及数值结果

普通命令：`.venv/Scripts/python.exe -B -X utf8 -m pytest -q -p no:cacheprovider tests/unit/test_material_derivative.py tests/unit/test_material_index.py tests/unit/test_dispersion_diagram.py tests/unit/test_materials.py tests/unit/test_plotting_units.py tests/unit/test_development_status_report.py tests/unit/test_contracts.py --junitxml=.local/evidence/development/MA-01/selected-derivative-unit-20261109.xml`，171 passed/1.74s。覆盖请求边界、类型专属参数、默认往返、0–4阶多项式及边界差分、两条路径取消/异常/关闭失败。

设置COMPLUS_LoadFromRemoteSources=1、PYTHONPATH为主仓src，串行执行`pytest --run-zemax -q -p no:cacheprovider tests/native/test_material_derivative_live.py tests/native/test_material_index_live.py --junitxml=.local/evidence/development/MA-01/selected-derivative-and-index-20261109.xml`，2 passed/32.74s。导数原始记录.local/runs/runs/material_derivative_selected_7eb8df98d1，calls.json/checks.json完整保存256项对照和关闭回执。

全部采用原绝对门槛5.1e-8 /µm、rtol=0：

| 参考 | 点数 | 最大绝对差 |
| --- | ---: | ---: |
| N-BK7/N-F2独立AGF Sellmeier解析导数 | 202 | 3.6807917824788206e-12 |
| 四材料30°C/0.8atm独立热光公式六阶差分，h=3e-4µm | 28 | 4.216876847706885e-12 |
| 自动全范围及单侧边界的独立解析导数 | 17 | 2.2526529253052985e-12 |
| 自有线性ZTG，解析导数−0.1 /µm | 9 | 1.0822981399982723e-11 |

线性ZTG为测试自有MD*.ZTG，5节点0.4–0.8µm、n=1.54−0.1λ，finally删除；本机已有资源保持。rows/series分页、Y范围PNG、保存重载一致、2001节点实际取消、副本关闭及取消后复用通过。系统设置、曲面和评价函数保持，最终disconnect ok=true、connected=false。PNG已查看，曲线、材料图例和单位正确。受影响色散图同轮回归550项对照通过。

默认报告回归：`pytest --run-zemax -q -p no:cacheprovider tests/native/test_dispersion_vs_wavelength_live.py --junitxml=.local/evidence/development/MA-01/derivative-default-regression-20261109.xml`，1 passed/10.97s。该用例保留原始解析诊断而使用既有5e-5有限差分验收；四点5.1e-8解析诊断超限并未被该通过覆盖。完整数值声明由上述显式导数路径的独立严格参考证明，原生默认报告继续按实际来源返回。

## 结论

条目通过显式正式原生折射率路径完成。台账两个入口同步done；计数新增一次。原生默认专题内部差分语义作为历史诊断保留，原始差异及文件均可追溯。下一项按D002剩余四项的设置与资源条件推进。

# 玻璃图目录身份及完整参考审计

日期2026-11-08；源码0.1.61工作区；OpticStudio24.2.0 build240529 PremiumEdition，Python3.14。

计划：同一受控会话将material_catalogs从SCHOTT切换OHARA，回读设置、执行kind-only glass_map、对照全部返回材料名和AGF的Nd/Vd。沿用Nd绝对5e-6、Vd绝对0.005门槛；显示舍入边界用Decimal比较，避免1.591965与1.59196的二进制相减误判。模型保持、终态、关闭及失败断连均记录。

结果：SCHOTT返回346项，339项在本机SCHOTT.AGF有同名记录，339项Nd/Vd全部通过。7项在该AGF未找到：LF5HTI、LLF1HTI、N-BK7HTI、N-SF57HTULTRA、N-SF6HTULTRA、N-SK5HTI、SF57HTULTRA。OHARA返回410项，410项材料名和Nd/Vd全部匹配本机OHARA.AGF。两次任务succeeded、close_attempted=true，系统设置前后保持。finally中disconnect成功；最后stdio正常结束。

结论：报告会随系统加载目录改变，已用正式update_system_settings入口验证；SCHOTT原生数据库与当前AGF存在7项身份差异，完整目录独立验收保持未完成。需要取得原生活动数据库对应的可读目录或确认数据库更新/重建流程，再对这7项核对。历史N-BK7单点通过范围继续有效，不扩展为完整目录通过。

检查：普通test_glass_map.py + test_contracts.py共39通过。目录身份原生新增用例最终为1 xfailed，原因明确为上述7项参考缺失，不计作通过。首次用例close_attempted从序列化结果读取错误已改为get_task_status；随后修正精确舍入边界。中间实际失败XML与调用均保留。pytest.xfail需在asyncio/std io异常组之外上报，该位置已经修正。

命令：`.venv/Scripts/python.exe -B -m pytest tests/native/test_glass_map_live.py::test_glass_map_selected_catalog_identity --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/MA-01/glass-map-catalog-identity-final-20261108.xml`。

逐目录观察/未知材料/数值差异保存在.local/runs/runs/glass_map_catalog_identity_a8b3965697/catalog-identity.json，全部请求、任务和断连在calls.json。FRU初始化警告仍出现，归入BASE-04。

MA-01.GlassMap保持implemented，B006不增计。继续YNI条目审计。

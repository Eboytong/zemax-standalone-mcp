# D007/D012 主仓集成审查

2026-11-08。来源为 `zemax-p01-gradium` 固定工作区，集成由原 `zemax-p01-runtime` worker 执行。主仓为 `C:/Users/tonge/Desktop/Zemax_MCP`，源码版本标识0.1.62，登记101工具/130分析；发行0.1.62保持101/118。

## 合入范围

新增 `star_analyses.py`、`scatter_capabilities.py` 及相应两份unit测试和STAR原生准备用例。`analyses.py`、`analysis_models.py`、`tests/support/analysis_scenarios.py` 采用六kind注册/分派、请求联合和专用场景小改动；保留主仓偏振和文本报告。`plotting.py`过滤空散点图项。`scattering_pages.py`合入已观察占位值过滤、写前资源拒绝和原生精确名称采用，保留已有BSDF资源诊断及User序列化错误归属。

六个STAR请求只接受kind；实际设置单次取得并回读。模块可用性实时读取。曲线、完整网格和散点独立采集，文本导出状态单独记录。原生致命消息返回失败并保留已取得的部分数据。网格区域和散点行分页调用真实Backend；图像调用真实plotting。

三类卸载为此前独立合入，见[D011](D011/integration-star-unload.md)。本组未增加工具数。文档与例子位于 `docs/topics/extensions/star.md`、`examples/requests/star-analyses.json`。

## 实际定向检查

命令：

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest tests/unit/test_star_analyses.py tests/unit/test_analysis_scenarios.py tests/unit/test_scatter_capabilities.py tests/unit/test_property_pages_adoption.py tests/unit/test_scatter_report.py tests/unit/test_path_analysis.py tests/unit/test_plotting_units.py tests/unit/test_imaging.py tests/unit/test_star.py tests/unit/test_star_controls.py tests/unit/test_star_materials.py tests/unit/test_model_adaptation.py tests/unit/test_contracts.py tests/unit/test_extended_contracts.py -q -p no:cacheprovider --basetemp=.local/tmp/pytest-star-integration-20261108-review --junitxml=.local/evidence/development/BASE-04/parallel-01/review-star-analyses-scattering.xml
```

结果：**421 passed，0 failed/error/skipped**。构成为74场景、27契约、30扩展契约、56成像、16模型适配、36路径、3绘图单位、19属性页、33散射能力、1散射报告、47STAR、43STAR专题、25STAR控制、11STAR材料。XML副本见 `review-star-analyses-scattering.xml`。

worker最终定向集合为225项，原XML保留在 `D012/worker-targeted.xml`，与主仓421项分别记录。新增原生文件仅收集：一个测试函数顺序覆盖六种分析；原生执行未开始。

最终审查修正了原生准备用例的旧 `scatter_points` 字段与宽泛异常捕获。共用 `tests/support/star_analysis_probe.py` 读取公开失败响应，只有明确 `FEATURE_UNAVAILABLE` 且实时 `availability.enabled=false` 才记模块不可用；其余错误保留响应并失败，成功需有效结构数据。新增 `tests/unit/test_star_analysis_probe.py` 的6项检查通过，原生用例收集1项。实际工具调用和结果见 `star-native-probe-check.json`，汇总见 `final-checks.json`。

## 审查结论与剩余条件

D007六项、D012十四项完成本轮审查；完整原生范围继续保留各自状态。D012六专题需应用实例、实时可用的STAR模块、受控FEA、输入/设置归属及数值/生命周期验收；系统查看器另需原生图像出口。组件和坐标控制沿用原独立参考、持久性和恢复要求。

D007仍需真实BSDF选择及匹配ISX；ScatterFunction缺有效正式出口，ScatterPolar已有181×90常数1/π网格而角度、单位及模型归属待确认。PathAnalysis缺分类剔除功率的正式定义或出口。User扩展已移出当前开发计划，历史序列化异常保留为诊断材料。

成员事实修正：本机 `IAR_DataGrid.Z(Int32,Int32)`、`GetDataScatterPoint` 与 `GetPoint` 均为正式成员。worker早期材料中的“未按正式成员”说法撤回；当前采集优先使用 `Values/ValueData` 和 `Points`，根据实际尺寸读取完整数据。成员来源见 `D012/pass-d012-member-sources.md`。

本轮原生共同条件见 `development/evidence/BASE-04/runtime-phase-environment-20261108.md`。application_create三次180秒超时后，本组只执行普通检查与准备用例收集。完整功能首次验收数未增加，集中检查仍为3/10。

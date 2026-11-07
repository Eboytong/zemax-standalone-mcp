# 0.1.11 镜头目录与候选评价

更新日期：2026-11-05。ED-05分为目录发现、筛选、加载、插入和候选评价五项，状态为`implemented`。新增27项普通检查；全量926项通过，450项原生未执行。原生设置、目录资源、计算、保存重载和关闭验收待连接恢复。

## 接口与单位

| 工具 | 请求 | 结果 |
| --- | --- | --- |
| `get_lens_catalogs` | 无参数 | 原生厂商名称和当前搜索设置；读取后关闭工具 |
| `run_lens_catalog_search` | `request.vendor`必填，EFL/EPD范围、元件数、四类形状及四类面型开关可选 | 任务、实际设置、完整匹配数、已读取镜头行及截断状态 |
| `run_catalog_lens` | `request.vendor/lens_name`必填，`action=load/insert` | 按唯一名称加载或插入，返回选中身份、原生尺寸及前后模型状态 |
| `run_catalog_evaluation` | `request.candidates/evaluation`必填，`common_settings`可选 | 从独立基线评价各候选，返回逐项结果、失败、汇总及恢复状态 |

目录EFL、EPD和搜索范围均使用毫米，与当前镜头单位分别记录。范围包含`minimum/maximum`，支持负焦距，EPD必须非负。`number_of_elements`省略时调用原生Any选项；形状/类型默认全部选择。厂商名称通过原生列表核对后采用实际名称。`max_results=10000`，范围1–100000；匹配超限时保留`total_matches`和`truncated=true`，完整已读取行保存JSON并使用既有任务分页。

镜头通过厂商和原生`lens_name`选择，名称不唯一时返回具体错误。结果保留原生getter索引及厂商、名称、EFL、EPD、形状、类型、元件数和远心标志。当前GetResult从0开始调用，其实际编号规则仍需原生用例确认。

## 加载、插入与恢复

`action=load`调用正式`LoadLens(saveIfNeeded=false)`，操作前已有检查点；完成后关闭目录工具、创建新的工作副本并读取实际系统。原生厂商镜头身份单独保存。load拒绝插入专属参数。

`action=insert`需要`at_surface`，位置从1开始且位于像面之前；`ignore_object=true`、`reverse_surface_geometry=false`。正式接口为`InsertLensSeq(atSurface,ignoreObject,reverseSurfGeom)`。检查返回值并读取最终模型。插入光学方向、对象忽略规则和save/load持久状态仍待原生验收。

两种修改均沿用检查点及修订号。任务启动、计算或设置失败保留具体原生原因；资源关闭由既有单工具任务机制完成，关闭失败进入重连处理。

## 候选评价

每个候选包含唯一的业务名称`name`，可设置目录`lens`和材料替换列表`materials`。材料项使用`surface/material/replace_solve`，同一候选的曲面编号不得重复。材料写入复用现有曲面修改及solve保护。每个候选均先重载同一基线，再加载/插入镜头或替换材料，然后执行同一`evaluation`。

`common_settings`使用现有有类型SystemPatch，在候选修改后、分析前应用。评价记录实际单位、孔径、视场及权重、波长及权重、环境、偏振和Ray Aiming条件。后续候选与首个已评价候选条件不一致时，记录`CONDITION_MISMATCH`及具体差异；可通过common_settings统一分析条件。系统单位设置与物理尺寸缩放使用各自现有入口。

`save_candidates=true`默认保存每个成功候选的实际设计；逐项记录保存路径和分析任务。一个候选失败后继续其他候选；取消、失败和完成均进入原有基线恢复流程。恢复失败需要重连并保留恢复检查点。已处理行通过`get_task_result(start,count)`分页。已有图表和评价报告入口继续使用相关分析结果。

请求例子：`examples/requests/lens_catalogs021_requests.json`。完整schema：`docs/reference/tool-schemas.json`。

## 探查、检查和后续原生验收

本机DLL方法参数及继承探查：`.local/evidence/development/ED-05/probe/methods.json`；声明摘录：同目录`interfaces.json`。本机手册第1363–1366页摘录保存于同目录，明确目录文件来自Stockcat，EFL/EPD单位为毫米。

普通检查：`tests/unit/test_catalogs.py`，覆盖请求边界、厂商和资源、最终回读、空/截断结果、名称歧义、原生失败、加载/插入参数、独立基线、条件差异、失败继续及取消恢复。全量结果为`.local/evidence/development/ED-05/ordinary021-final.xml`：926通过，450原生未执行，14.99秒。

新增原生用例`tests/native/test_catalogs_live.py`覆盖真实stdio目录发现、查询、选择、插入、分页、设计重载及重复材料候选的可重复性。代表性目录插入的光线/光焦度参考、目录镜头候选的独立数值评价以及原生取消/关闭仍需补测。缺少Stockcat或匹配镜头时，原生用例记录具体输入条件。

原生连接沿用既有180秒初始化超时证据`.local/evidence/development/BASE-04/connection019/supervisor.json`，本批未重复启动。批次汇总及安装包结果见`development/evidence/lens-catalogs021-summary.json`。

# ED-02 顺序 solve 扩展（0.1.8）

## 2026-11-06 MaterialOffset 完成

MaterialOffset 已按本机手册第333页的定义完成验收：在目录色散上叠加两组模型玻璃的折射率差，模型输入保留目录的 `Nd/Vd/dPgF`。参考的基底色散独立按目录 Sellmeier1 系数计算，模型差通过独立设置的 Model 光学基线和双入射角 Snell 反算取得。十五组零、正、负偏移组合覆盖可见光、最短波长0.3µm及0.29µm分支；四个原生用例共399次数值检查通过，120项相关普通检查通过。逐组最终设置、保存重载后的单元格/配置/评价函数、光线结果及关闭通过，证据 `verification/development/ED-02/acceptance275.json`，例子 `examples/material-offset275.json`。

原有折射率容差 `1e-6 + 1e-7×参考绝对值`、阿贝数容差 `1e-5 + 1e-7×参考绝对值` 保持。旧测试把输入 `vd_offset` 直接当作最终反算阿贝数的增量；参考已改为文档定义的模型差分，旧失败及实际增量0.9992435881404731保留。目录 `dPgF=-0.0009` 是 N-BK7 独立参考的一部分，省略它会改变模型差。

本机在最短波长恰为0.3µm时仍采用模型差分分支；使用目录有效范围覆盖0.29µm的 LITHOSIL-Q 时，逐波长采用恒定折射率偏移，阿贝数偏移不活动。最初0.29µm用例选用了最短有效波长0.3µm的 N-BK7，参考基线无效；改用有效资源并增加目录范围前置检查，原始结果保留。

MaterialModel 仍为 implemented。直接 `LDE.GetIndex` 已重现物理谱线阿贝数60.02418808120307、舍入谱线59.99988524798575及物理d线折射率1.6000019888117303；这些结果定位到原生模型拟合，原容差仍待满足。原始设置、环境与三组 Model/四组 Offset/两组 `dPgF` 对照见 `material-diagnostic270/271/anchors.json`。下文保留早期版本的历史状态。

## 2026-11-05 独立材料、编辑器与设计工具验收

本轮新增17项完成：MaterialSubstitute、ED-03的14项操作、Scale与非球面转换。六波长双入射角Substitute比较18项通过，保存重载及关闭通过。编辑器覆盖通用TDE插入及MFE/MCE/TDE最终状态重载；Scale两种路径及转换sag、曲面参数重载通过。163项相关普通检查通过。首次测试响应字段读取错误与修正后结果分别保留。

Model与Offset已拆成独立基线执行，原生舍入谱线阿贝数分别为59.99988524798844（目标60）和增量0.9992435881404731（目标1），仍超原容差1e-5+1e-7×参考值，继续implemented。下一步定位原生色散定义，继续ED-04剩余七项与ED-05；MCE独立文件正式入口仍缺失。

证据 verification/development/ED-03/acceptance048/summary.json，JUnit native048-final.xml及ED-04/native048.xml。本轮只修改测试、证据、文档与台账，版本保留0.1.46，全量目标继续进行。


## 2026-11-05 solve 与编辑器原生验收

本轮完成 Automatic/Maximum 光学半口径、GridSag 参数9/10宏 solve 四项验收，逐项状态转为 done。矩阵保存重载和数值检查通过；四项原生不采用路径保留失败记录。证据 verification/development/ED-02/acceptance047/summary.json，原始 JUnit native047.xml；100项相关普通检查通过。

材料六波长、两入射角 Snell 检查已执行。舍入d线采用通过，舍入谱线阿贝数59.99988524798844仍超原容差1e-5+1e-7×60。保持材料三项 implemented；下一步拆开独立执行 Offset/Substitute，定位 Model 色散参考，保留原始失败。

编辑器首次重载比较失败源于THIC将厚度从0改到1后，测试仍使用修改前的TTHI Nominal。测试改为保存前刷新并检查最终Nominal=1，复测通过，报告 verification/development/ED-03/native047.xml。剩余补充通用TDE插入、MFE/MCE完整持久状态断言后再关闭对应条目。

本轮仅修改测试、台账及证据；代码版本保留0.1.46。下一步为独立材料用例、编辑器验收补齐，再继续ED-04/05。全量目标继续进行。


基线：本机 OpticStudio 2024 R2 / 24.2.0、PremiumEdition、Python 3.14.6。入口仍为 `update_surfaces`、`get_surfaces`、`get_system_resources`、`get_capabilities`。旧九类请求保持可用。

## 请求与单位

`changes[].solves.<cell>` 按 `mode` 选择有类型请求。新增模式拒绝其他模式的字段；数值必须有限。曲面从0编号；`source_surface` 使用同一编号。除专门说明外，长度使用当前镜头单位。

| mode | 参数 | 定义与条件 |
| --- | --- | --- |
| marginal_ray_angle / chief_ray_angle | angle，必填 | 出射近轴边缘/主光线斜率，无量纲；批量追迹的方向余弦须取 m/n 后比较 |
| marginal_ray_normal / chief_ray_normal | 无 | 使球面法线与近轴边缘/主光线一致 |
| aplanatic | 无 | 原生消球差求解；受控模型按近轴消球差共轭关系检查 |
| element_power | power，必填 | 厚透镜光焦度，镜头单位倒数；设置在第二面，目标编号至少2 |
| concentric_surface / concentric_radius | source_surface，必填 | 曲率中心位于参考面顶点/参考面曲率中心；参考面须在前 |
| optical_path_difference | opd，必填；pupil_zone=1，范围−1至1 | 轴上场、主波长，出口瞳参考，OPD 为 waves |
| compensator | source_surface、sum，必填 | 本面与前序参考面厚度之和，镜头单位 |
| center_of_curvature | source_surface，必填 | 调整厚度，使下一面位于前序参考面的曲率中心 |
| pupil_position | 无 | 中心视场真实主光线的微分瞳位置 |
| material_model | index_nd、abbe_vd，必填；dpgf=0；vary_index/vary_abbe/vary_dpgf=false | 正折射率与正阿贝数；三个优化标志分别回读 |
| material_offset | nd_offset=0、vd_offset=0 | 在当前玻璃上叠加原生折射率和阿贝数偏移 |
| material_substitute | catalog="" | 空串表示当前已启用目录集合；非空须为已启用目录的原生名称 |
| automatic | 无 | 口径单元格的原生自动模式；Chip Zone 实测保留当前数值 |
| maximum | 无 | 至少两个配置；单配置会回退 Automatic，写入前拒绝 |
| zpl_macro | macro，必填 | 使用原生宏列表中的名称。半径列的 SOLVERETURN 返回曲率，单位为镜头单位倒数 |

`mechanical_semi_diameter`、`chip_zone` 加入 solve 单元格及 `get_surfaces.cells`，原有标量入口继续可用。同一修改先设置标量，再设置 solve。自动机械口径转 Fixed 后才写数值；替换关系沿用 `replace_solves`。

`get_system_resources` 新增 `kind="solve_macros"`，可指定 `surface`、`cell`，沿用 query/start/count 分页。宏来自 `ISolveZPLMacro.GetAvailableMacros()`。缺宏和目录在写入前报告 `INVALID_RESOURCE`。

## 实际采用与失败

创建原生 solve、设置参数、检查 IsValid 和 SetSolveData 返回值后，读取实际模式及参数。`Concentric*` 与本机拼写 `Cocentric*` 的枚举数值分别相同（12、13），使用本机 `_S_Cocentric*` 接口。原生未采用与参数丢失分别返回 `SOLVE_UPDATE_FAILED`、`SETTING_REJECTED`。

批量失败沿用检查点、模型修订、已完成曲面和失败曲面状态；原始错误保留在 cause。测试从独立基线开始，保存重载后重新读取设置。工作副本和关闭沿用现有链路。

## 本机探查与原生限制

本轮扫描本机81种可切换面型的基本列和活动参数列，发现27个不同的 LDE solve 名称（含旧九类）。完整枚举、接口成员及支持列表见 `verification/development/ED-02/all-types/probe.json`。

| 条目 | 探查结果与解除条件 |
| --- | --- |
| 机械半口径 SurfacePickup | 直接 API 与 MCP 均返回成功后变为 Fixed；先 Fixed 再设置仍失败。需要可采用并保存重载的正式设置路径 |
| Chip Zone SurfacePickup | 直接 API 与 MCP 均回退 Automatic；先 Fixed 后设置仍失败。需要保持 SurfacePickup 的正式路径 |
| 机械半口径 ZPLMacro | 直接 API 与 MCP 均回退 Fixed。需要正式接口正确采用宏 solve |
| Chip Zone ZPLMacro | 模式可采用，但宏名回读为空。需要正式接口保留宏名并执行 SOLVERETURN |
| DuplicateSag / InvertSag | DLL 有接口；扫描81种面型的基本列和活动参数列未提供可放置单元格。需要原生可用单元格或正式独立入口及相应样例 |
| MarginPercent / CA_fill / DIA_fill | 仅有 SolveType 值，ISolveData 未公开对应设置对象；上述 LDE 列未提供支持。需要正式的可用列与设置出口 |
| ObjectPickup / ConfigPickup / ThermalPickup / FieldPickup | 此轮 LDE 列未提供这些模式；Object/MCE 已有独立编辑器入口。FieldPickup 的编辑器扩展继续按相应工作包推进 |

原生控制记录见 `verification/development/ED-02/diagnostics/controls.json`。资源宏由测试创建专用副本，结束后移除；重放相应脚本会重新准备输入。既有 ED-01 阻塞另存原条目。

## 验收与证据

本轮数值检查以追迹基本量和解析关系为参考：角度取方向余弦比值；法线/消球差取近轴入射高度和斜率；光焦度取厚透镜公式；同心、曲率中心、补偿器取独立轴向和厚度关系；OPD 取归一化真实光线结果；瞳位置取正负小场差分主光线。一般使用 `atol=1e-8 + rtol=1e-7×|参考值|`；OPD 为 `1e-5 waves + 1e-7×|参考值|`；微分瞳位置为 `1e-6 + 1e-6×|参考值|`。

`numeric018` 保留最初将方向余弦直接当斜率所产生的超限；`final-cases018` 使用 m/n，保持原容差。参数9/10的旧用例选择了非活动参数；已改为带非零数据的 GridSag 基线，补测连接失败，尚未取得替代基线的数值结果。材料与多配置口径的真实 stdio 数值记录、最终普通与原生回归、wheel 安装冒烟汇入 `verification/solve-extensions018-summary.json`。

正式定义来源为本机安装的 `OpticStudio_UserManual_en.pdf` 第197–198、328–336、1348–1349、1602页及 DLL 反射。材料模型波长基准的实测差异保留在 `verification/development/ED-02/material-diagnostic018/`。

重放：`.venv/Scripts/python.exe -B -m pytest tests/test_extended_solves_live.py --run-zemax -q -s`。较大逐项原生检查：`.venv/Scripts/python.exe -B tests/support/solve_cases018.py <新的证据目录>`。原生执行串行。

## 本轮状态（2026-11-04 至 2026-11-05）

逐项台账共46项：30项 done、7项 implemented、9项 blocked。done 包括12个半径/厚度新solve、14个宏单元格以及4个机械半口径/Chip Zone固定或自动设置。材料三项、自动光学半口径、Maximum和宏参数9/10保留具体剩余验收。9项阻塞由4项采用失败和5项未找到正式LDE入口组成。

最终普通检查为781项通过、437项原生用例未执行，见 `verification/development/ED-02/ordinary-final.xml`。本轮41项矩阵记录中35项保存重载通过、27次数值比较通过，4项正式接口采用失败，2项旧宏参数基线失败。额外真实stdio用例完成新solve设置/重载、近轴光线结果读取和布局导出，且正常断开；机械自动半口径等于光学半口径加Chip Zone的4.25数值比较另有通过记录。

材料参考出现实际超限：物理d线的Snell折射率为1.6000019888117303，请求IndexNd为1.6，容差为`1e-6 + 1e-7×|参考值|`。回读参数为1.6；差异来源尚未确认。已准备六波长诊断比较物理谱线与四位小数波长，连接未完成，保留原容差。

随后补测连接返回`INVALID_LICENSE`，第二次材料诊断等待超过十分钟无返回，终止后确认测试启动的Python和OpticStudio进程均退出。本机配置为`1055@localhost`，1055端口监听，服务运行；`ansysli_server.log`为空，现有日志未给出本次具体拒绝原因。记录见 `verification/development/ED-02/licensing018.json`。恢复一次成功ZOS-API连接后，串行补材料、不同配置Maximum、GridSag参数9/10、受影响既有原生回归及安装包原生冒烟。

请求示例见 `examples/solve_extensions018_requests.json`；同一文件的各例须分别从其注明的基线开始。失败例明确保留原生拒绝状态。完整请求模型由 `docs/tool-schemas.json` 和 `get_capabilities` 提供。


0.1.8 wheel已构建并独立安装至`outputs/wheel-release018`；复用现有锁定依赖，以`-I`启动安装目录中的服务。真实stdio冒烟通过74工具发现、27模式、随包记录、请求schema、连接前提及类型拒绝，正常关闭。证据为`verification/development/ED-02/wheel-smoke018.json`。安装包的原生连接/建模/分析冒烟待许可恢复。


2026-11-07 ZPL solve收口348：发现EX-01的GridSag9/10待办已由ED-02 acceptance047完成；本轮复测替换两组宏返回值、中文31字符宏名、保存重载、缺资源与超长请求、模型保持和正常关闭。原生1通过，相关普通162通过。正式Setter对照显示ASCII/中文名称31个UTF-16单元可用，32个即便返回Success仍回退Fixed；加入有类型长度前检并更新schema/能力。超长请求在MCP参数验证阶段拒绝，修订和检查点保持。证据EX-01/acceptance348.json。按历史重复范围收口，不增加B004完成数；仍8/10、剩余137组。机械口径/ChipZone宏限制和任意宏执行沿原条目保留。

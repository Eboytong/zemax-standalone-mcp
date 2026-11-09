# 顺序 solve 扩展






原有折射率容差 `1e-6 + 1e-7×参考绝对值`、阿贝数容差 `1e-5 + 1e-7×参考绝对值` 保持。旧测试把输入 `vd_offset` 直接当作最终反算阿贝数的增量；参考已改为文档定义的模型差分，旧失败及实际增量0.9992435881404731保留。目录 `dPgF=-0.0009` 是 N-BK7 独立参考的一部分，省略它会改变模型差。

本机在最短波长恰为0.3µm时仍采用模型差分分支；使用目录有效范围覆盖0.29µm的 LITHOSIL-Q 时，逐波长采用恒定折射率偏移，阿贝数偏移不活动。最初0.29µm用例选用了最短有效波长0.3µm的 N-BK7，参考基线无效；改用有效资源并增加目录范围前置检查，原始结果保留。

MaterialModel 仍为 implemented。直接 `LDE.GetIndex` 已重现物理谱线阿贝数60.02418808120307、舍入谱线59.99988524798575及物理d线折射率1.6000019888117303；原容差仍待满足，偏差来源待控制实验定位。原始设置、环境与三组 Model/四组 Offset/两组 `dPgF` 对照见 `material-diagnostic270/271/anchors.json`。下文保留早期版本的历史状态。












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


| 条目 | 探查结果与解除条件 |
| --- | --- |
| 机械半口径 SurfacePickup | 直接 API 与 MCP 均返回成功后变为 Fixed；先 Fixed 再设置仍失败。需要可采用并保存重载的正式设置路径 |
| Chip Zone SurfacePickup | 直接 API 与 MCP 均回退 Automatic；先 Fixed 后设置仍失败。需要保持 SurfacePickup 的正式路径 |
| 机械半口径 ZPLMacro | 直接 API 与 MCP 均回退 Fixed。需要正式接口正确采用宏 solve |
| Chip Zone ZPLMacro | 模式可采用，但宏名回读为空。需要正式接口保留宏名并执行 SOLVERETURN |
| DuplicateSag / InvertSag | DLL 有接口；扫描81种面型的基本列和活动参数列未提供可放置单元格。需要原生可用单元格或正式独立入口及相应样例 |
| MarginPercent / CA_fill / DIA_fill | 仅有 SolveType 值，ISolveData 未公开对应设置对象；上述 LDE 列未提供支持。需要正式的可用列与设置出口 |
| ObjectPickup / ConfigPickup / ThermalPickup / FieldPickup | LDE 列未提供这些模式；Object/MCE 使用独立编辑器入口。 |










## 验收与证据




重放：`.venv/Scripts/python.exe -B -m pytest tests/native/test_extended_solves_live.py --run-zemax -q -s`。较大逐项原生检查：`.venv/Scripts/python.exe -B tests/support/solve_cases018.py <新的证据目录>`。原生执行串行。




材料参考出现实际超限：物理d线的Snell折射率为1.6000019888117303，请求IndexNd为1.6，容差为`1e-6 + 1e-7×|参考值|`。回读参数为1.6；差异来源尚未确认。已准备六波长诊断比较物理谱线与四位小数波长，连接未完成，保留原容差。


请求示例见 `examples/requests/solve_extensions018_requests.json`；同一文件的各例须分别从其注明的基线开始。失败例明确保留原生拒绝状态。完整请求模型由 `docs/reference/tool-schemas.json` 和 `get_capabilities` 提供。

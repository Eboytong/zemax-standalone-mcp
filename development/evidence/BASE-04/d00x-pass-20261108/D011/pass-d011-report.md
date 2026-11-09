# D011 审计报告（EXT-STAR，16 项）

日期：2026-11-08。性质：**离线审计 + 实际实现（Unload）+ 已有原生证据复用**。原生启动统一延后（`application_create` 三次 180 s 超时），本轮未启动新的原生会话，原生验收仍未完成。B003 计数属历史来源（见 §5），本轮不增加批次完成数。

> CV-01.FftSurfaceMtf 的留存数据单因素实验已交由 `zemax-p01-hologram` 并行执行；本报告不重复，FFT 索引最终引用其报告（见 §7）。

## 1. 方法

1. 从主仓 `development/tracking/d00x-pass-20261108.json` 过滤 `development_group=="D011"` 得 16 项，与 `development/ledgers/operations.csv`（`utf-8-sig`）逐项对齐（16/16 命中，均 `blocked`）。
2. 逐项读取当前适配器源码：`star.py`（读/导入/拟合）、`star_controls.py`（8 类控制）、`star_materials.py`（材料查询）、`star_models.py`（typed 请求）。
3. 核对正式反射接口：`probe037.json`（读/导入/拟合接口与枚举）、`probe038.json`+`parameters038.json`（控制接口与参数名）、`probe039.json`（`ISTARMaterials` 签名 + `ISTAR_*FEAData.UnloadData()`）。
4. 复用原生就绪证据：`readiness193.json`（2026-11-06）、`native190-materials.xml`、`native192-availability.xml`；对账 `development/evidence/EXT-STAR/control-evidence-reconciliation-20261108.md`。
5. 运行普通检查（见 §4）。

## 2. 证据清单（实测存在）

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `verification/development/EXT-STAR/probe037.json` | 41558 B | 2026-11-05 读/导入/拟合接口 + 枚举 |
| `verification/development/EXT-STAR/probe038.json` | 14481 B | 2026-11-05 控制接口 |
| `verification/development/EXT-STAR/parameters038.json` | 5529 B | 控制参数名 |
| `verification/development/EXT-STAR/probe039.json` | 7245 B | `ISTARMaterials` 方法签名 + unload 接口 |
| `verification/development/EXT-STAR/readiness193.json` | 2908 B | 原生就绪/材料/卸载恢复条件 |
| `development/evidence/EXT-STAR/control-evidence-reconciliation-20261108.md` | 2056 B | 2026-11-08 静态对账 |
| `docs/topics/extensions/star.md` | 6764 B | STAR 使用文档（含原生条件更新） |
| `docs/topics/imaging/materials.md` | 7804 B | 材料环境折射率/dn·dT 文档 |

注：台账引用的 `docs/star.md`、`docs/materials.md` 实际位于 `docs/topics/extensions/star.md`、`docs/topics/imaging/materials.md`；属路径差异，不影响内容。

## 3. 源码审计（逐项对应）

| 条目 | 适配器 | 关键校验（源码事实） |
| --- | --- | --- |
| Read | `star.py:57 get_star_data` | 读 `Are*Imported/NumberOfDataPoints/Filename`；`rows` 分页≤1000，先物化完整 `GetFEAPointsSafe` 再切页；单位来源注明不做换算 |
| UpdateMode | `star_controls.py:104` | `check_mode` 写后 `Equals` 回读；`DoManualUpdate()`；异常回滚 `mode_before` |
| Materials.refractive_index | `star_materials.py:16` | 参数顺序 `(catalog,material,λ,envP,envT,matP,matT)`；`value<=0` 或非有限 → `INVALID_RESULT_DATA` |
| Materials.dndt | `star_materials.py:17` | 参数追加 `ΔT`；仅有限性校验（**正确**：dn/dT 允许零或负值，不添加 `value>0`）；历史零值由独立热光参考与输入身份判定 |
| ThermalControls | `star_controls.py:161` | `SetThermalFEAFitType`/`SetWorkingWavelength`；波长编号≤系统波长数 |
| VolumeControls | `star_controls.py:176` | 分别改 `GRINStep` 与 `Fits.GRINStep`，回读最终组合 |
| Import×3 | `star.py:129 run_star_operation` | 绝对路径、`UNIT_MISMATCH`、坐标系写后回读、导入后核对标志/非空点数/文件回读、失败 `_restore_model` |
| Fit×3 | 同上 | `settings` 局部写回读→`Refit`→`apply`→启用态回读；`deformation_option` 按枚举值比较 |
| FittedSamples | `star.py:109` | 变形 X/Y、温/折射率 X/Y/Z；`MISSING_FEA_DATA` 门；≤1000 样本 |
| Unload×3 | `star.py:_run_star_unload` | 已实现：前读 `imported/NumberOfDataPoints/Filename`；`FEAData.UnloadData()`；后核对导入标志清除；检查点/取消/恢复同构 |

## 4. 实际运行的检查

1. `python -B -m pytest tests/unit/test_star.py tests/unit/test_star_controls.py tests/unit/test_star_materials.py -q -p no:cacheprovider --basetemp .local/pytesttmp-d011c`
   → **83 passed in 0.65s**（含新增 21 个卸载测试）。
2. 证据文件存在性检查 → probe037/038/039、parameters038、readiness193、对账 md 全部存在。
3. 实现前 `grep -r 'UnloadData|unload' src/zemax_mcp` → 无匹配（确认缺口）；实现后 `src/zemax_mcp/star.py` 含 `_run_star_unload` 与 `data.UnloadData()`，`star_models.py` 含 `StarUnload`。
4. 文档/示例 → `docs/topics/extensions/star.md`（新增卸载节）、`examples/requests/star-unload.json`。
5. `tests/unit/test_star.py` 单文件 → **47 passed**（26 原 + 21 卸载）。

本组 83 项的关键用例覆盖：`test_star_typed_conditions`、`test_star_point_paging_preserves_data_kind_and_native_state`、`test_star_feature_flag_checked_before_data_access`、`test_star_import_*`、`test_star_fit_partial_settings_final_readback_and_apply_order`、`test_star_option_compares_enum_values_instead_of_alias_names`、`test_star_native_fitted_sample_values`、`test_update_mode_manual_update_and_cancel_mode_restore`、`test_thermal_wavelength_preflight_and_final_combination_readback`、`test_volume_controls_patch_one_native_member`、`test_star_material_modal_*`、`test_invalid_native_index_closes_catalog`、`test_dndt_error_preserves_method_conditions_and_close_warning`、`test_restore_error_retains_control_error_and_requires_reconnect`。

## 5. 审计发现（本轮更新）

- **A（实现缺口，已修复+首轮审查收尾）**：三个 `Unload*` 此前无适配器路径。本轮已在主仓实现 `StarUnload` typed 联合 + `star.py:_run_star_unload`（检查点/取消/恢复），补 capabilities `unload`、文档与示例，新增 21 个卸载单测。首轮审查两点已落实：① `source_retained` 字符串改为 `source_file` 身份 + `exists_before`/`exists_after` 存在性事实 + `no_source_delete_performed=true`（仅记录存在性事实）；② 卸载成功判据用 `read_state` 完整回读，详细 `get_star_data` 改为尽力而为（`detail`/`detail_unavailable`），空数据下 Fits 读取失败不再把成功卸载误报为失败。导入标志按 `BRANCHES[data_kind][1]`（`IsDirectIndexImported` 等）读取，未虚构 `_are*` 字段。台账 `entry_points` 映射偏差仅记录，不改台账。已合入主仓，待原生验收。
- **B（证据日期，原 C 顺延）**：readiness193/probe037/038/039 为 2026-11-05/06 采集；2026-11-08 仅静态对账，无新原生会话；本轮沿用不新增。
- **更正**：dn/dT 允许零或负值，产品仅校验有限性是**正确**行为；原“缺少正性门”判断撤销。历史零值用独立热光参考与输入身份判定，不加 `value>0` 约束。

## 6. 外部阻塞（逐类）

1. **控制/读/导入/拟合（11 项）**：`IsSTARModuleEnabled=false`（readiness193），无受控 FEA 实例。解除：应用报告模块启用并提供受控 FEA，按原容差验收设置采用/数值/重载/恢复/关闭。
2. **材料折射率/dn·dT（2 项）**：`ISTARMaterials.GetRefractiveIndex/GetDNDT` 对 N-BK7/N-F2、三种目录、六组条件均返回 0；`native190` passed 0/failed 1。解除：返回有限正折射率及有意义 dn/dT，并建立独立色散/热光参考（dn/dT 可零/负，靠参考判定）。
3. **卸载（3 项）**：适配器已在主仓实现并通过 21 个卸载普通测试；剩余为原生验收（启用模块 + 独立拥有的 FEA 副本）；适配器已合入主仓。解除：原生验证导入标志转 false、源保留、恢复、关闭。

容差（原文，不改）：变形 `1e-8 镜头单位 + 1e-6×参考值`；温度 `1e-6 °C + 1e-6×参考值`；直接折射率 `1e-8 + 1e-7×参考值`。

## 7. 结论与界限

- 16 项全部完成**离线审计**（源码 + 反射 + 历史原生证据 + 普通检查）；**Unload 三型已实际实现**（83 passed，test_star 47 含 21 卸载测试），但原生验收未完成，条目仍 `blocked`，无一项本轮可关闭。
- 未启动原生、未改台账/批次/tracking、未提交 Git；共享 STAR 改动已合入主仓（`star_models.py`/`star.py`/`backend.py` 的 unload 相关行），待原生验收。
- 交付：本报告 + `pass-d011-plan.md` + `pass-d011-items.json` + `d011-unload-patch.md` + 文档/示例 + 卸载测试。
- **FFT 索引**：CV-01.FftSurfaceMtf 留存数据单因素实验引用 `zemax-p01-hologram` 并行报告（本 worker 不重复）。

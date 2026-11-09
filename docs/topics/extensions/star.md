# STAR 数据与拟合

`get_star_data` 和 `run_star_operation` 使用本机 `ILDERow.STARData` 的变形、温度和直接折射率接口，适用于当前顺序配置。每次调用检查 `IsSTARModuleEnabled`；未启用时返回具体功能状态。

## 导入

```json
{"request":{"kind":"import_deformation","surface":1,"path":"C:\\FEA\\surface1.txt","coordinate_system":"local","length_unit":"Millimeters"}}
```

`kind` 可选 `import_deformation/import_temperature/import_direct_index`。输入为已存在文件的绝对路径。`coordinate_system` 明确 local/global，原生设置后回读；`length_unit` 必须与当前镜头单位一致，数据在调用前已使用该单位。适配器不做隐式数值转换。温度采用摄氏度，折射率为无量纲。

输入复制到本次工作目录中的独立资源子目录，再调用对应 `Import*`。导入后核对标志、非空点数和实际文件名，返回原始资源、工作副本及采用设置。工作副本资源供后续保存重载使用。

## 拟合与采用

```json
{"request":{"kind":"fit_deformation","surface":1,"settings":{"mba_tolerance":0.001},"apply":"enable","deformation_option":"DeformationWithRBMs"}}
```

`kind` 可选 `fit_deformation/fit_temperature/fit_direct_index`，前置条件为相应数据已导入。`settings` 为局部修改对象，支持 `grid_1/2/3`、`mba_max_level`、`mba_tolerance` 和 `mba_min_fill`；省略保持原值。各值写入回读后调用 `Refit`，再处理 `apply=keep/enable/disable`，最后检查参数组合与启用状态。

`deformation_option` 专属于变形拟合，支持 `DeformationWithRBMs/DeformationWithoutRBMs/OnlyRBMs/NoDeformation`，按枚举值回读；与启用开关冲突的组合在请求层拒绝。

修改沿用模型检查点和修订号。成功保留结果；失败或取消恢复基线；恢复失败保留原始操作错误和恢复错误并要求重连。取消在原生方法之间生效，当前同步 Import/Refit 方法结束后进入下一取消边界。

## 读取

```json
{"request":{"surface":1,"data_kind":"deformation","include_points":true,"start":0,"count":100,"sample_points":[{"x":0,"y":0}]}}
```

返回导入/启用状态、原生文件、坐标系、拟合设置、统计、刚体位移及坐标变换。FEA点按 `rows` 分页，每页最多1000；原生 `GetFEAPointsSafe` 会先分配完整原生数组，Python只转换当前页。

`sample_points` 最多1000项，调用原生 `GetFitted*` 求值。变形使用 X/Y；温度和折射率使用 X/Y/Z。`remove_rigid_body=true` 仅用于变形。输出保留原生拟合坐标约定及单位来源。STAR对象由光学系统持有，本操作创建零个独立 Analysis/SystemTool；应用关闭随服务断连完成。


## 卸载

`kind` 可选 `unload_deformation/unload_temperature/unload_direct_index`，前置条件为对应数据已导入（原生 `AreDeformationsImported`/`AreTemperaturesImported`/`IsDirectIndexImported` 为真）。请求前读入导入标志、点数与原文件名；调用原生 `FEAData.UnloadData()` 后核对导入标志已清除，未清除则返回 `SETTING_REJECTED`。

```json
{"request":{"kind":"unload_deformation","surface":1}}
```

卸载记录前后状态（导入标志/点数/文件名）与 `source_file`（源文件身份、`exists_before`/`exists_after` 存在性事实、`no_source_delete_performed=true`）；源文件为导入时暂存的工作副本，卸载只清除原生引用，不删除磁盘副本。成功范围以导入标志清除为判据；详细 Fits/坐标/热控读取为尽力而为（成功记 `detail`，不可用记 `detail_unavailable`），空数据下读取失败不会把成功卸载误报为失败。沿用检查点与边界取消；失败或取消恢复基线，原始异常与恢复异常分开保留，恢复失败要求重连。

## 刚体、坐标、组件与更新控制

继续使用 `run_star_operation`：

| kind | 主要字段 | 原生接口与采用结果 |
| --- | --- | --- |
| `rigid_body` | surface、enabled、reference_point | SetReferencePoint、Enable/Disable；回读参考点、标志及变换 |
| `coordinate_transform` | surface、data_kind、enabled、offset、rotation_matrix、reset | SetDecenter、SetRotationMatrix；回读完整最终矩阵、偏移和启用状态 |
| `define_component` | first_surface、last_surface、adjust_index_data_with_rbm | 定义连续组件；检查重叠及最终成员 |
| `remove_component` | first_surface | 按原生首面删除组件；核对其余分组保持 |
| `component_rbm` | surface、action、adjust_index_data_with_rbm | configure、remove_from_fea、add_coordinate_breaks；回读处理标志、分组和曲面数 |
| `thermal_controls` | surface、fit_type、working_wavelength | 原生整数拟合类型与波长编号的 Set/Get；校验系统波长数量 |
| `volume_controls` | surface、data_kind、grin_step、fit_grin_step | 分别修改数据页及Fits页的GRINStep，回读最终组合 |
| `update_mode` | mode、manual_update | Normal/Suspended枚举及DoManualUpdate；回读实际模式 |

```json
{"request":{"kind":"coordinate_transform","surface":1,"data_kind":"deformation","offset":{"x":0.1,"y":0.2,"z":0.3},"rotation_matrix":[0,-1,0,1,0,0,0,0,1],"enabled":true}}
```

偏移和刚体参考点使用当前镜头长度单位。旋转矩阵按R11至R33行优先排列，须为正交、行列式+1的旋转，容差1e-6。reset与显式变换分开请求；省略enabled保留原启用状态。输入参数为空的修改请求会被拒绝。

组件必须位于物面与像面之间；已有分组与新范围重叠时返回关系保护错误。RemoveComponent的参数已由本机DLL确认是firstSurface。重复应用已完成的组件RBM操作会被拒绝。转为坐标间断后重新取得组件对象，记录原生成员和曲面数量变化，并使旧几何映射失效。

fit_type采用本机整数代码，具体可用代码的语义待原生运行确认；请求值须经Set/Get采用。两个GRINStep成员按原生值传递，其物理步长约定和成员关联仍待原生验收。getter读取失败在 `get_star_data.controls` 保留原始原因；写入操作要求目标状态成功回读。



## 本机原生条件更新



## 六项默认专题分析

通过 `run_analysis` 调用下列 kind；当前请求只包含 `kind`，采用原生默认设置。每次运行读取模块可用性，取得一次设置对象并记录实际可读值和公开成员。完整输入选择及数值范围仍待原生验收。

| kind | 正式枚举 | 编号 |
| --- | --- | ---: |
| `star_align_check` | `STARAlignCheck` | 155 |
| `star_sys_viewer` | `STARSysViewer` | 156 |
| `star_2d_def_plot` | `STAR2DDefPlot` | 157 |
| `star_perf_change` | `STARPerfChange` | 158 |
| `star_index_vs_temp` | `STARIndexVsTemp` | 159 |
| `star_inspect_fea` | `STARInspectFEA` | 160 |

```json
{"request":{"kind":"star_inspect_fea"}}
```

曲线返回 `series`，网格返回完整 `values[y][x]`，散点明细返回 `rows` 并保留有效点绘图数据 `scatter`。结果使用现有曲线/区域/行分页和图像导出。文本导出结果单独记录；原生失败消息及可取得的部分数据保留在错误详情。


## 本机许可与恢复条件

# 系统设置与顺序建模

适配本机 OpticStudio 2024 R2。曲面从 0 开始，视场和波长从 1 开始。所有长度为当前镜头单位，倾斜角、偏振相位和 VAN 为度；VDX/VDY/VCX/VCY 无量纲。修改前保存检查点并推进修订号，失败响应中的 `partial_changes_possible` 表示可能已有修改。

## 资源与系统设置

`get_system_resources` 使用 `request` 对象：

```json
{"request":{"kind":"materials","catalog":"SCHOTT","query":"BK7","start":0,"count":200}}
```

kind 支持 catalogs、materials、coatings、coating_files、scatter_profiles、abg_files、gradium_profiles、surface_types、surface_files、surface_import_files。materials 必须指定 catalog；coatings 的 surface 默认 1。surface_files 可指定 surface_type 查询待切换面型的可用文件。query 按名称不区分大小写过滤；count 为 1–1000，默认 200。返回 items、total、next_start，无匹配返回空列表。

`get_system_settings` 返回实际材料目录、偏振、瞄准、文件、归一化和每个视场的渐晕参数。`update_system_settings` 的参数名为 `settings`：

```json
{"settings":{"polarization":{"unpolarized":false,"jx":1,"jy":0,"x_phase":0,"y_phase":90,"method":"YAxisMethod"},"ray_aiming":{"mode":"Paraxial","method":"Heuristic","cache":true,"robust":false},"field_normalization":"Radial","field_updates":[{"number":2,"vdx":0,"vdy":0,"vcx":0.05,"vcy":0.05,"van":0}]}}
```

- material_catalogs 是完整的目标目录集合；添加先于移除，仍被材料曲面引用的目录不能移除。目录查找使用资源列表中的名称，曲面的 material_catalog 可带 `.AGF` 后缀。
- polarization 另支持 convert_thin_film_phase。系统偏振与分析 `use_polarization` 分别配置。归一化非偏振追迹仍不计算完整镀膜/偏振损耗。
- ray_aiming.mode 支持 Off、Paraxial、Real；method 支持 Heuristic、Optimize。另支持 auto_pupil_shift、scale_pupil_shift_by_field、enhanced、advanced_convergence、fallback_search、pupil_shift_x/y/z、pupil_compress_x/y、cache_steps，回读实际采用值。
- field_updates 只原位修改指定视场的渐晕参数；与 fields 互斥。fields 整组替换时可指定相同的五个渐晕参数，省略取零。
- vignetting_action=calculate/clear 调用原生自动渐晕/清除，与 fields/field_updates 互斥。
- files 支持 coating_file、scatter_profile、abg_file、gradium_profile。只接受本机可用列表中的文件名，修改设计引用后执行 ReloadFiles，不写入材料或镀膜文件。
- 嵌套设置省略字段保留现值，不使用 null。get_capabilities 返回本机设置枚举。

## 曲面与求解关系

`update_surfaces` 的 `mechanical_semi_diameter` 和 `chip_zone` 分别设置机械半口径与倒边区，单位为当前镜头单位。两者均回读请求值；原有自动或拾取关系需要 `replace_solves=true`。`get_surfaces` 的 `properties.mechanical` 返回实际数值与原生 solve 模式。热模型须明确机械半口径、净半口径及 Chip Zone；跨配置膨胀时使用对应的 MCSD、SDIA、CHZN 热拾取，不能只改变曲率与中心厚度。

`get_surfaces` 返回 cells、properties、光阑标记及各活动单元格的 available_solves。面型须在当前行的原生可用列表中；基础面型包括 Standard、EvenAspheric、CoordinateBreak、OddAsphere、Toroidal、Biconic、Paraxial。通过 surface_file 选择原生文件面型依赖；GridSag/GridPhase 可用 import_file 导入绝对 .DAT 路径，需要 replace_solves=true。具体参数以 header、writable 为准，系数单位按面型定义。tce 按原生 TCE × 1E-6 列输入，可用相同的变量和求解接口管理。

```json
{"changes":[{"surface":2,"coating":"","aperture":{"type":"RectangularAperture","x_half_width":5,"y_half_width":4},"tilt_decenter":{"before_decenter_x":1,"before_tilt_y":5}}]}
```

coating 使用资源列表中的镀膜名，空字符串清除镀膜；is_stop=true 指定唯一光阑。aperture.type 支持 None、CircularAperture/Obscuration、RectangularAperture/Obscuration、EllipticalAperture/Obscuration。圆形需要 maximum_radius，可指定 minimum_radius；矩形与椭圆需要两个半宽。偏心使用 x_decenter/y_decenter，默认零。孔径切换按完整类型设置覆盖尺寸。

孔径也可用 `{"pickup_from":1}` 设置拾取。已有拾取需要 replace_pickup=true 才能替换；合并同一请求的全部孔径修改及未修改的关系，拒绝最终图中的循环；拒绝发生在检查点和原生写入之前。应用合法请求时先解除被替换的旧拾取，再写入新关系，允许通过清除旧边来反转依赖。执行阶段失败时使用响应中的检查点恢复。显式倾斜偏心支持 before_/after_ 的 decenter_x/y、tilt_x/y/z 和 order（Decenter_Tilt/Tilt_Decenter）。面后已有拾取时需要 replace_pickup=true。Coordinate Break 用 parameter_1..6 配置坐标变化；无穷远物方第一面及原生标记禁用的曲面拒绝面属性倾斜偏心。

solve 使用 changes[].solves：

| mode | 参数 |
| --- | --- |
| marginal_ray_height | height、pupil_zone（默认 0 为近轴光线；-1–1 的非零值为真实光线 Py） |
| chief_ray_height | height |
| edge_thickness | thickness、radial_height（默认 0） |
| position | source_surface、length |
| pickup_chief_ray | field、wavelength（均默认 1） |

保留 fixed、variable、surface_pickup、f_number。surface_pickup 返回 supports_scale、supports_offset；不支持的参数返回 null，指定不支持的非默认比例或偏移会报 UNSUPPORTED_SOLVE_PARAMETER。半径拾取的比例作用于曲率，例如源半径 50、scale=2 时结果为 25，不支持 offset。单元格必须支持对应 solve，替换原关系需要 replace_solves=true。面型切换同样需要此标志；原生设置失败返回结构化错误；设置后同时回读 Solve，未采用请求模式时报告错误。改变面型后的单元格按新面型核对，失败可能已有部分修改。

Hologram2的`parameter_13`（Volume Hologram?）接受0/1。值为0时Variable不能持久化，`update_surfaces`与`set_variables`在写入前返回UNSUPPORTED_SOLVE；值为1时Variable已有`.zos/.zmx`保存重载依据。关闭已有Variable的体全息须同时显式设为Fixed。该状态限制与原生枚举分别返回，详见[Hologram2模式持久化](solve-support.md#hologram2-模式持久化)。

## 复制与几何

```json
{"request":{"start":1,"count":2,"at":4}}
```

`copy_surfaces` 在 at 前插入最多 100 面，源和目标限定物面与像面之间。使用原生复制规则处理参数、属性和引用，保持原物理光阑。返回 copied、start、stop_surface、total。复制后应读取移动后的曲面及 solve，确认其物理含义。本机验证中，将曲面 3 的半径拾取复制到其来源曲面之前时，原生复制将该副本的拾取改为 Fixed；原曲面的拾取仍随插入位置更新编号。不能假定每个副本都保留原关系。

```json
{"request":{"surface":2,"points":[{"x":0,"y":0},{"x":3,"y":0}]}}
```

`get_surface_geometry` 最多接受 200 个局部 X/Y 点，空列表只读取变换。global_transform 包含三行 rotation 和 translation，按 `global_position = rotation @ local_position + translation` 转换位置；方向仅乘旋转。global_reference_surface 是当前全局参考面，其自身变换可为单位矩阵。global_transform_valid=false 时变换为空。

Sag 返回原生 sag 和 alternateSag 两个解；不将 alternateSag 自动选为物理交点。失败点保留输入、error 和空值，不以零替代有效结果。

## 验证与运行

`tests/test_modeling_live.py` 通过真实 stdio 调用资源、系统设置、适配面型、五类 solve、孔径、复制、Sag、变换和保存重载。`tests/test_modeling_reference_live.py` 另核对完整带符号旋转矩阵、平移、三条光线的全局交点与方向，以及包含光阑和带拾取曲面的多种复制位置。球面 Sag、矩阵与光线解析参考采用 rtol=1e-7、atol=1e-8；结果范围以实际调用记录为准。

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest tests/test_modeling_live.py tests/test_modeling_reference_live.py --run-zemax -q -p no:cacheprovider
```

仅在需要定位原生异常时使用诊断程序（历史参考）。GUI对照、普通测试和原生数值分别评定；运行时串行访问原生实例。

## 变量模式写入

set_variables 对顺序曲面、MCE 和非序列对象单元格共用原生返回值与 cell.Solve 回读检查。原生报告成功但实际模式不符时返回 SOLVE_UPDATE_FAILED，包含 requested、actual、native_return、failed_index（从0起）及 completed_count。同批请求在失败项停止；先前修改可能已生效，使用响应中的检查点和修订号恢复。默认保持 solve/pickup 替换保护。

求解的当前模型支持表与独立数值依据见[重点面型求解支持](solve-support.md)。PARTIAL_UPDATE.cause 保留原生拒绝的结构化错误；available_solves 表示原生列表，不表示光学数值验收结论。

## 全局参考面与热安装

`update_system_settings` 的 `global_reference_surface` 选择顺序系统的正编号全局参考面；原生布尔返回及实际编号均核对。`get_system_settings` 和 `get_surface_geometry` 返回当前参考面。默认编号保留原生行为，插入曲面可能改变其编号；不能将参考面自身的单位矩阵误作绝对世界姿态。

非平面空气间隔的热拾取按手册2.1.1.4.4.2沿机械边缘长度计算，并考虑径向接触点变化。受控模型使用5度共同倾斜、前端R=50mm、接触半径3mm、CTE=100ppm/°C；半径保持固定，后端为平面。中心距离由边缘膨胀和新接触点Sag恢复，再用完整旋转矩阵转为全局端点。相互倾斜的非对称元件需要单独核对。

# EXT-STAR.Components 组件管理前置复核

原生数据日期：2026-11-06（readiness193）；2026-11-08为静态复核，未新增原生执行。

日期：2026-11-08

## 计划与探查

检查 `define_component`、`remove_component`、`component_rbm` 的有类型请求、组件成员读取、RBM 移除及坐标断点依赖；核对 `ISTAR_ComponentRBMs` 的正式成员和模块前置条件。

## 结果

- 反射记录 `probe037.json`/`probe038.json` 确认 `ISTAR_ComponentRBMs` 提供成员读取、`SetSurfacesInComponent`、`RemoveComponent`、`RemoveComponentRBMsFromFEADataSets` 和 `AddComponentRBMsAsCoordinateBreaks`。
- 适配器已有组件成员、重叠、首面删除、重复操作和恢复检查；普通组件控制测试可运行。
- 本机 `IsSTARModuleEnabled=false`，组件控制在 `_require_star()` 前置处返回 `FEATURE_UNAVAILABLE`，未写入曲面、配置或 STAR 状态；无受控 FEA 副本可执行保存重载和数值验收。
- 原生资源关闭和 stdio 断开沿 readiness193 记录成功。

## 结论

`EXT-STAR.Components` 保持 `blocked`，未计入完成数。解除条件：启用 STAR 模块并提供受控 FEA/顺序模型，随后验证组件成员、RBM 状态、坐标断点拓扑、保存重载和失败恢复。

### Components.configure（#111）

`component_rbm` 的 `action=configure` 要求显式 `adjust_index_data_with_rbm`，适配器会调用并回读 `AdjustIndexDataWithComponentRBM`。当前 STAR 前置检查在写入前失败，未产生部分修改；配置动作仍等待启用模块后的原生回读和持久性验收。

### Components.coordinate_breaks（#112）

`component_rbm` 的 `action=add_coordinate_breaks` 对应正式方法 `AddComponentRBMsAsCoordinateBreaks()`，适配器还检查 `CRBMsAreInCoordinateBreaks`、组件数量和曲面数量变化。当前模块前置检查阻止调用，未改变几何映射或曲面拓扑。

### Components.define（#113）

`define_component` 使用 `SetSurfacesInComponent(first_surface,last_surface)`，并在写入前检查像面范围、已有组件重叠；写入后核对成员列表和组件首尾面。当前 STAR 模块未启用，定义调用没有发生。

### Components.remove（#114）

`remove_component` 要求请求使用原生组件首面；适配器先读取成员状态并拒绝非首面请求，再调用 `RemoveComponent(first_surface)`，最后核对组件清单为空。当前 STAR 前置检查在读取/写入前阻止操作，模型保持不变。

### Components.remove_rbms（#115）

`component_rbm` 的 `action=remove_from_fea` 对应正式方法 `RemoveComponentRBMsFromFEADataSets()`，适配器在调用前拒绝已移除状态，调用后回读 `ComponentRBMsAreRemoved`。当前 STAR 模块未启用，方法未调用，FEA 数据保持不变。


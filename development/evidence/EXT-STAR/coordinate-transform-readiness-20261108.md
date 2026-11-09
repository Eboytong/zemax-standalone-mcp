# EXT-STAR.CoordinateTransform 前置复核

原生数据日期：2026-11-06（readiness193）；2026-11-08为静态复核，未新增原生执行。

日期：2026-11-08

## 计划与接口

核对坐标变换请求的偏移、旋转矩阵、启用状态和重置语义，并确认 `SetDecenter`、`SetRotationMatrix`、`ResetToDefaultFrameOfReference` 的回读条件。

## 结果

- 请求模型要求有限偏移；旋转矩阵必须正交且行列式为 `+1`；重置不能与显式偏移/旋转同时传入。
- 原生适配器按启用、偏移、旋转、回读顺序写入，并检查默认参考系和最终矩阵。
- 当前 `IsSTARModuleEnabled=false`，`_require_star()` 在任何写入前返回 `FEATURE_UNAVAILABLE`；坐标变换、曲面和模型修订保持不变。
- 原生关闭和 stdio 断开沿 `readiness193.json` 成功记录。

## 结论

条目保持 `blocked`。解除条件：启用 STAR 模块并提供受控 FEA/顺序模型，完成坐标数值、保存重载、恢复和任务关闭验收。


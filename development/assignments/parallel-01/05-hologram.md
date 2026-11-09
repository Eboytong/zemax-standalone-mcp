# Agent 5任务书：D010原生全息衍射效率收口

范围为`CO-01.DiffEfficiencyAngular`、`CO-01.DiffEfficiencyChromatic`、`CO-01.DiffEfficiency2D`三组。当前声明范围为原生Hologram1，见`development/tracking/scope.json`。依次按角度、波长、二维三项先计划后验收。

## 当前起点

三项2026-11-08复测记录均保留在`development/evidence/CO-01/`。Hologram1的S/P角度和波长已与独立参考在`atol=1e-6, rtol=1e-5`下对应；二维交叉切片、分页、图像、保存重载、失败、取消和关闭已有证据。历史整项未完成与当时跨模型范围有关，需按当前原生声明逐条审查。

先核对以下文件：`diff-efficiency-angular-repeat20261108.md`、`diff-efficiency-chromatic-repeat20261108.md`、`diff-efficiency-2d-repeat20261108.md`及其原始`calls.json`、`checks.json`、`reference_status.json`、关闭回执。

## 可立即开展

1. 为三项分别建立“当前声明—设置—结果—参考—单位—分页/图像—恢复/关闭—证据路径”矩阵，定位适用旧证据及缺失断言。
2. 审查Hologram1记录/重建几何、乳胶启用和级次、折射率调制/厚度、S/P方向与功率定义。独立参考复用`tests/support/kogelnik.py`，把已知输入和适用条件写清楚。
3. 核对typed请求、`configure_diff_efficiency`和`diff_efficiency_surface`的实际采用；结果轴分别为角度degrees、波长µm，效率无量纲；二维轴及切片对应明确。
4. 准备独立的Hologram1验收选择和必要普通测试；保留旧DLL研究记录，当前三项结论以原生Hologram1矩阵评定。
5. D001提供新的偏振约定结论时，审查与本项既有S/P映射是否相容。需要改动时保留原始差异及明确依据。

## 定向检查及原生申请

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_diff_efficiency.py -q -p no:cacheprovider
```

已有原生命令供Agent 0排队选择：

```powershell
.\.venv\Scripts\python.exe -B -m pytest 'tests/native/test_diff_efficiency_offaxis_live.py::test_unslanted_hologram_offaxis_reference[native]' --run-zemax -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_diff_efficiency_live.py --run-zemax -q -p no:cacheprovider
```

先审查旧证据对当前实现的覆盖；只有缺失、实现变更或未决问题涉及的条件进入复测。沿用`atol=1e-6, rtol=1e-5`；二维除切片一致性外，核对既有独立抽样参考的实际覆盖。

三项各自覆盖视场/波长/曲面和S/P身份、设置回读、曲线或网格、分页、图像、任务失败/取消/复用、模型重载及关闭。数值通过、诊断通过与实际声明范围分别记录。

## 所有权和交付

衍射效率专题逻辑、相关普通/原生测试与任务专用参考归本任务。`analyses.py`的设置、条件和结果标注函数及请求注册变动单列共享补丁。总能力文档、CSV重复记录、批次和schema提交建议变更，由审查负责人统一更新。

交付三份逐项收口结论、证据适用性表、缺失部分的新执行记录、请求示例及状态建议。三项分别达到当前声明范围后，每项各计一次；证据审查或一次诊断本身计数0。

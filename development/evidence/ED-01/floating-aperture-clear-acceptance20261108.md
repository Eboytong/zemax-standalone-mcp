# FloatingAperture 清除验收（2026-11-08）

- 条目：`ED-01.Aperture.FloatingToNone`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 计划：复核正式 `ChangeApertureTypeSettings` 适配、确认旧失败复现的设置条件，执行受控的 FloatingAperture→None 循环并比较周边曲面状态。
- 普通检查：`.venv\Scripts\python.exe -m pytest tests/unit/test_property_pages_adoption.py -q`，15 passed。
- 原生检查：`.venv\Scripts\python.exe -m pytest tests/native/test_property_pages_numeric_live.py::test_property_apertures_numeric -q -s --run-zemax`，1 passed。独立自建平面模型上运行三轮类型切换；三次 `None` 均由 `get_surfaces` 回读为 `None`，调用返回成功。
- 状态比较：每轮比较 FloatingAperture 写入后与 None 清除后的面型、所有曲面单元格及 `properties` 中除 aperture 以外的全部属性，均完全一致。模型修订按每次更新递增，未检测到额外修改。
- 结果目录：`.local/runs/runs/property_aperture_numeric_63cdfcea98`；`calls.json` 保存六次类型设置与实际回读，`state/close_receipt.json` 记录原生关闭 `closed=true`。stdio 测试客户端正常结束，无遗留测试或 OpticStudio 进程。
- 结论：当前 OpticStudio 24.2 环境中，正式接口可连续可靠地将 FloatingAperture 清为 None，且其他属性保持；本条完成。早期“返回成功但仍保留 FloatingAperture”的复现仅作为历史记录，不代表本次现状。

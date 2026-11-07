# ZRD 光线数据库查看

`ray_database_viewer` 通过 `run_analysis` 读取现有绝对路径 ZRD：

```json
{"kind":"ray_database_viewer","path":"C:/data/trace.zrd","filter":"H3","max_segments":10000}
```

请求沿用 `read_zrd` 的原生筛选表达式、起始光线/段和分段上限。每行对应一个光线段，包含光线编号、段编号、交互对象、全局坐标、方向、强度、光程及原生状态；坐标长度使用镜头单位。通过 `get_task_result(start,count)` 分页，或使用返回的 `summary.next_read` 从下一段继续读取。

RayDatabaseViewer 专题设置在本机只有 `AS_Default` 通用设置，没有正式文件/筛选选择器。实现使用正式 `OpenRayDatabaseReader` 工具，回读筛选，执行 `RunAndWaitForCompletion`/`Succeeded`，读取段数据并确认关闭。ZRD 文件属性为 write-only，报告所请求绝对路径及该原生属性的读取限制。

控制验收使用 NSC 点光线到矩形探测器，三条光线在确定的撞击坐标、方向和单光线强度上逐项核对；续页、筛选、空结果、畸形文件、关闭、重载及复用记录在 `verification/development/NS-02/native461-reader.xml`。本机 Reader 对内容畸形的文件返回成功与零段；这一原生行为保留在结果中。

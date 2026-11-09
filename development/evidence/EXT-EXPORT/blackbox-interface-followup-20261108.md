# EXT-EXPORT.BlackBox 接口复核

日期：2026-11-08

## 探查计划与输入

检查安装版 OpticStudio 2024 R2 的公开程序集、现有 ZBB 相关类型、手册材料和样例目录；确认是否存在有类型创建请求所需的工厂、设置对象、结果文件出口及关闭协议。

## 实际结果

- 公开类型扫描记录：`.local/evidence/development/EXT-EXPORT/public-types042.json`，共 908 个导出类型。
- `ISurfaceBlackBoxLens` 只提供对已有 ZBB 黑盒面的消费/设置能力，未发现创建、参数写入或 ZBB 文件导出方法。
- `IOpticalSystemTools` 的公开导出覆盖 CAD、布局和 Speos；LDE 公开导出覆盖点云；未发现命名为 BlackBox/ZBB 的创建工厂或任务接口。
- 手册记录的 ZBB GUI 功能与公开 API 能力分开保留；样例目录未找到 ZBB 创建样例或受控 ZBB 输入。
- 本项未创建原生工具，也未修改模型；不存在可执行的正式请求契约，因而没有伪造请求或替代计算。

## 结论

`EXT-EXPORT.BlackBox` 保持 `blocked`。解除条件：本机版本提供受支持的 ZBB 创建协议/工厂、参数和许可说明，或提供明确的自动化协议；取得后再补有类型请求、设置回读、ZBB 文件、重载/追迹对照及资源关闭验收。


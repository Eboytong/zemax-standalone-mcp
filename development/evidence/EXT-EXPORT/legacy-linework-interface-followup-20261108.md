# EXT-EXPORT.LegacyLinework 接口复核

日期：2026-11-08

## 探查

检查安装版 OpticStudio 2024 R2 的公开程序集、CAD/布局工具、DXF/IGES 关键词和本机手册/样例目录，寻找旧线框导出的正式创建接口及输出设置。

## 结果

- 公开类型扫描 `.local/evidence/development/EXT-EXPORT/public-types042.json` 未发现 `Linework`、`DXF`、`IGES` 或 Export 2D/3D 专用创建方法。
- 手册 `manual042.txt` 第 49–51 页描述 GUI 的 2D DXF、3D DXF 和 IGES Linework，明确这是旧 CAD 线框出口；公开 `run_cad_export` 的实体 CAD 格式不能替代该声明范围。
- 没有可取得的正式设置对象、文件命名协议、结果回读或独立取消/关闭句柄；本次未创建工具或修改模型。

## 结论

条目保持 `blocked`。解除条件：本机版本提供旧线框创建工厂/自动化协议、参数和许可说明，再补有类型请求、原生文件与几何参考、保存重载和资源关闭验收。


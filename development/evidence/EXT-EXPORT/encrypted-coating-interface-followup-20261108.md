# EXT-EXPORT.EncryptedCoating 接口复核

日期：2026-11-08

## 探查

检查 OpticStudio 2024 R2 安装版公开类型扫描、手册和本机样例目录，寻找 ZEC 创建工厂、加密设置、输出文件和关闭协议。

## 结果

- 公开类型扫描 `.local/evidence/development/EXT-EXPORT/public-types042.json` 未发现 `EncryptedCoating`、`ZEC` 或专用创建接口。
- 手册 `manual042.txt` 第 54 页及第 283 页描述 GUI 的 Export Encrypted Coating 和 `.ZEC` 文件；该材料没有对应的公开 API 方法签名。
- 已有 CAD、布局、Speos 和点云接口不能表达镀膜加密的范围、文件名和测试重载条件。
- 未创建原生工具或修改模型；没有可验证的有类型请求、设置回读和结果出口。

## 结论

条目保持 `blocked`。解除条件：取得安装版本支持的 ZEC 创建工厂/自动化协议、参数和许可说明，再补有类型请求、输出文件、重载/透射对照、模型保持和资源关闭验收。


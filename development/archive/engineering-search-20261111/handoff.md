# 开发交接

2026-11-11。主仓C:/Users/tonge/Desktop/mcp，源码1.3.0，107工具、146种分析。工程搜索与设计改进D017—D022全部完成，6/6；统一发行检查已通过，GitHub正式版v1.3.0已发布。

## 交付及修复

- 能力检索、持久候选、联合玻璃、评价函数、去敏感化及逐面损耗已交付，逐项记录见[当前阶段](current.md)和[台账](ledgers/roadmap.csv)。
- 显式材料池仅读请求材料，自动目录扫描分步进行并在取消时关闭；OPD写入、回读和结果读取每16项交还控制，解决发行回归的状态查询超时。
- 原生向导依完整设置组合回读，支持单配置/单视场；逐面损耗按原生渐晕码定位真实截断面。
- 全量普通3765通过；原生首轮8通过、3项超时，修复复测3通过；跨三面归属另1通过。原始失败及后续证据一并保留。

## 发行与会话

wheel：releases/1.3.0/zemax_standalone_mcp-1.3.0-py3-none-any.whl。独立安装目录.local/builds/release130-installed。独立安装stdio的107/146 schema和离线搜索通过，安装包4项原生通过，最终重建wheel另1项原生通过，全部会话正常断开。完整命令及最终发布状态见[1.3.0记录](evidence/release130.md)。

发行已完成：main及v1.3.0已推送，wheel为uploaded，源码提交3cb8ae6。后续按具体维护请求执行。保留未跟踪releases/0.1.62/。既有1.1.0与更早证据沿用其实际适用条件。

```powershell
.\.venv\Scripts\python.exe -B scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json --ranked development/remaining-ranked.md
```

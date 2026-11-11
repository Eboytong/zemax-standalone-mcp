# 后续选题与可行性核对

日期：2026-11-11。工作区C:/Users/tonge/Desktop/mcp，源码a099540，产品1.1.0。交付为选题、计划及台账更新；本期实现计数0/6。

## 1. 输入与方法

参考用户提供的“AI-Native Zemax”四阶段建议，采用其中阶段1、2作为选题材料。核对当前源码、请求模型、发行证据、本机程序集及固定版本GitHub源码，按实际开发增量组织D017—D022。

环境沿用Windows x64、Python3.14、OpticStudio2024 R2/API24.2.0/build240529 Premium。当前schema102工具、144分析请求。上期检查见[1.1.0发行记录](../release110.md)。

## 2. 已有基础及实际缺口

| 源码 | 已有实现 | 后续增量 |
| --- | --- | --- |
| backend.py:get_capabilities，server.py | schema详情、领域设置和能力元数据 | 统一索引、中文检索、单位/条件定位 |
| files.py:copy_system；backend.py:_checkpoint/_working_copy | 原生副本、工作副本和修改前保存 | 具名候选、父子归属、持久索引与显式恢复 |
| evaluation.py:_restore_model/compare_results | 恢复、统一评价及严格条件比较 | 将设计差异与评价条件分开，公平比较换玻璃候选 |
| history.py | 请求回执、任务历史和历史结果读取 | 关联候选及父任务，复用现有存储 |
| glass_trials.py:GlassTrials/run_glass_trials | groups列表、单一target_group、目录筛选、原生优化、指标、保存/关闭 | 多槽位联合赋值、组合预算及搜索策略 |
| evaluation.py/configurations.py/pareto.py | DLS/OD、Global、Hammer、多起点、有限权重Pareto | 统一候选/预算衔接 |
| wizard_models.py/wizards.py | Gaussian Quadrature、矩形瞳、场/配置及制造良率选项 | 目标/约束预览、尺度、OPD参考及自定义目标 |
| tolerance_budget.py/tolerancing.py | 灵敏度、公差预算、Monte Carlo、独立种子验证 | 固定公差范围并修改设计变量的去敏感化 |
| rays.py/coatings.py | 偏振光线强度/电场、双向R/T/A | 同一带权光线集的逐面损耗归属 |

因此，当前架构可承载六项工作。设计变量、任务、恢复和历史模块继续复用；元数据与候选索引按实际使用补齐。

## 3. 本机正式接口反射

执行命令：使用项目.venv的Python -B -X utf8，pythonnet加载安装目录ZOSAPI_Interfaces.dll，经System.Reflection.Assembly读取枚举及向导属性。

结果：

```json
{
  "assembly": "1.0.0.0",
  "operands": {
    "OPDX": true,
    "OPDC": true,
    "OPDM": true,
    "TOLR": true,
    "HYLD": true
  },
  "wizard_type": "ZOSAPI.Wizards.ISEQOptimizationWizard2",
  "properties": [
    "UseGaussianQuadrature",
    "UseRectangularArray",
    "IsHighManufacturingYieldAvailable",
    "OptimizeForManufacturingYield",
    "ManufacturingYieldWeight"
  ]
}
```

程序集版本1.0.0.0与产品API版本分别记录。反射进程正常退出，OpticStudio实例创建数0。原始摘要位于.local/evidence/development/PLAN-20261111/interface-reflection.json。

D021首个原生用例需读取运行时制造良率标志，确认TOLR公差设置文件/编号和TDE归属，再决定具体路线。代表用例及容差已写入任务书。

## 4. 官方定义及GitHub源码核对

读取官方2024 R2操作数说明，OPDC按主光线参考，OPDM按瞳均值参考，OPDX另去除倾斜；TOLR支持名义值、RSS变化和估计性能等数据选择，并关联指定公差设置。按原生规则生成相应组行与配置。

- [Optimization Operands](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Optimization_Operands_Alphabetically.html)：本轮通过HTTPS实际读取；保留上述定义摘要。
- [Gaussian Quadrature](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Gaussian_Quadrature.html)：可读取；常规采样沿本项目已适配原生向导。

Joey仓库固定a7375ba48235b2db71ae40766dbc1969c0671401，实际读取：

- [ForbesMeritFunctionTool.cs](https://github.com/joeyijun/OpticStudioMCPServer/blob/a7375ba48235b2db71ae40766dbc1969c0671401/src/ZemaxMCP.Server/Tools/Optimization/ForbesMeritFunctionTool.cs)
- [ForbesPupilSampling.cs](https://github.com/joeyijun/OpticStudioMCPServer/blob/a7375ba48235b2db71ae40766dbc1969c0671401/src/ZemaxMCP.Server/Tools/Optimization/ForbesPupilSampling.cs)

可复用的思路：有类型参数、构建前保存MFE、失败恢复、逐场/波长/配置组织操作数。需要重做的部分：普通采样theta覆盖0—π，轴上只取一个子午线；对称采样取第一象限。偏心、倾斜和非对称波前需完整瞳参考。其视场读取统一按最大径向范围归一化，接入时需尊重本项目实际场归一化设置。具体实现采用本机正式列定义和原生向导。

本轮参考阅读保持源码独立；代码借鉴实施时在对应D项记录文件、改写及许可处理。

## 5. 取舍与完成门槛

有实际功能增量的六项进入现行计划。执行保护/追溯与原生搜索整合进入相关任务；新外部优化算法待具体同预算镜头对照后再选。独立会话平台、全量COM日志和向量数据库暂未形成额外工程交付需求。

本期验收使用可读取的能力入口、同条件候选指标、约束、固定预算、独立Monte Carlo及真实关闭结果。测试集按对应功能选择受控小模型。

本次维护运行test_development_roadmap.py的4项普通测试通过，并重新生成当前六项队列。计划准备证据与后续原生功能验收分别记录。

# Gradium写入顺序与传播起点控制

日期：2026-11-09。条目MA-01.GradiumProfile，别名CV-02.GradiumProfile；源码0.1.62工作树，项目Python 3.14；OpticStudio 24.2.0 build240529 PremiumEdition。

## 声明范围与实验计划

保留高阶求值、capping及专题配置/波长选择原范围。本次检验两个假设：capping与offset写入顺序影响最终采用；传播失败与入口面或负profile坐标段相关。使用自有平面模型、正式Gradium曲面和批量Direct真实光线，不新增公开请求字段。

材料G14SFN，波长0.58756 µm，厚度0.4 mm，offset=-0.2 mm，capping=2，积分步长0.01 mm。本机手册244—246页定义profile位置为局部z加offset；capping=2开放左端扩展，扩展材料应保持端点折射率和色散。摘录来源保留在.local/evidence/development/MA-01/gradium-contract-review-20261109/。

## 命令和实际结果

执行程序scripts/probes/MA-01/gradium_capping_order.py，参数分别为：

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/MA-01/gradium_capping_order.py .local/evidence/development/MA-01/gradium-capping-order-20261109
.venv/Scripts/python.exe -B -X utf8 scripts/probes/MA-01/gradium_capping_order.py .local/evidence/development/MA-01/gradium-capping-bypass-20261109 --bypass
```

上述为复现命令；实际请求、参数顺序、设置回读和上下文以各probe.json的calls/cases字段为准。

四种顺序为offset后cap、cap后offset、分两次先cap后offset、设置后offset归零再重写。最终参数1/2/8均为0.01/-0.2/2；UpdateStatus后GetIndex入口折射率均为1.804945948428175。每组从面1到面2光线成功，从面1穿过Gradium到面3均返回error_code=2；任务本身均succeeded，逐光线失败独立保留。

| 起点面 | 目标面 | 局部起点z/mm | error_code |
| --- | --- | ---: | ---: |
| 1 | 2 | 0 | 0 |
| 1 | 3 | 0 | 2 |
| 2 | 3 | 0 | 2 |
| 2 | 3 | 0.21 | 0 |

最后一条对应起点profile坐标0.01 mm，输出方向[0,0,1]。改变起点同时缩短传播区间；此实验将失败范围缩小到负profile坐标/capping段传播，原生内部原因尚未确定。原既定曲线/高阶数值门槛保持；本轮为离散状态诊断，不增加数值容差。

## 生命周期和检查

两次记录均settings_restored=true、surfaces_restored=true、cleanup_failures=[]、disconnect.connected=false。每个光线任务均到succeeded终态，分页取得一条光线；任务与逐光线状态分开判定。首次顺序记录只保存target_surface，start_surface及起点可由calls中的正式请求确认。恢复采用工作副本检查点，本轮未新增独立保存重载验收。

原相关普通69项通过、0.62秒，XML：.local/evidence/development/MA-01/gradium-capping-order-20261109/unit.xml。请求模型检查覆盖参数顺序和Direct光线类型。原始JSON位于两条命令的输出目录。

## 结论和下一步

写入顺序解释已排除；负profile段传播仍失败。状态保持in_progress，完整计数增加0。解除条件：取得负profile坐标均匀扩展传播的正式处理依据或有效最小修复，并按既有正反配置/波长/边界矩阵复验；同时完成10/11阶剖面求值和专题选择缺口。后续优先推进D004，不重复同条件顺序实验。

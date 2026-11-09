# MaterialModel 正式定义与本轮参考审查

2026-11-09更新：正式Environment页确认关闭折射率修正时温压固定；修正基线后八组已执行、五组重载及双角Snell/direct一致性通过。Using Model Glasses未公开完整色散重建公式，下文“公式待转录”属于历史动作，现由[环境与矩阵复测](environment-model-controls-20261109.md)替代。

日期：2026-11-08；条目 `ED-02.MaterialModel.Material`，归属 D002。主仓源码 0.1.62，101 个工具、130 种分析；本轮没有安装包或原生数值验收增量。

## 正式资料及适用定义

资料来自本机 OpticStudio 2024 R2 正式帮助 `C:/Program Files/Ansys Inc/v242/Zemax OpticStudio/Help/OpticStudio_Help_en.chm`，已解包的主题位于 Gradium worker 工作区 `.local/coordination/parallel-02/chm_en/OpticStudio_Help/topics/`。检索报告保留在同一工作区 `.local/coordination/parallel-02/material-model-definition-review.md`。

| 主题 | 确认的定义 | 后续检查作用 |
| --- | --- | --- |
| `Using_Model_Glasses.html` | d=0.5875618 µm，F=0.4861327 µm，C=0.6562725 µm；输入为 Nd、Vd、dPgF | Nd 与 Vd 主比较采用精确谱线；四位小数谱线作为历史诊断并列保存 |
| `Index_of_Refraction_Computation.html`、`Using_Material_Catalogs.html` | 原生追迹使用相对空气折射率，当前环境下空气定义为 1 | 分开登记参考温压、系统温压及波长修正 |
| `Environmental_Effects_on_Index_for_Gradient_Index_MIL.html` | Model Glass 没有本体 dn/dT 数据，环境变化通过周围空气修正相对折射率 | 现有 Snell/direct 对照用于一致性检查；环境数值参考需另行计算 |
| `Wavelength_Data.html` 等 | 默认系统条件为 20 °C、1 atm | 控制实验显式记录实际温压 |
| `Description_of_Catalog_Data.html` | dPgF 为相对部分色散对 normal line 的偏离 | 从正式公式独立计算 PgF，建立第三参数参考 |

Model Glass 的可见光折射率近似精度约为 0.0001，此量对应折射率 n。Vd 仍按原条目门槛比较。

Abbe、PgF/normal line 与色散重建公式以图片或 SVG 存在，当前完成了页面定位，公式转录及独立实现待补。

## 历史数值与本轮结论

已有 Nd=1.6、Vd=60 控制结果中，四位小数谱线复算 Vd=59.99988524798844，精确谱线复算 Vd≈60.02418808。两套历史误差均保留，原门槛 Nd `1e-6 + 1e-7×|参考值|`、Vd `1e-5 + 1e-7×|参考值|` 延续。

“内部使用四位小数常数”仍是待检验假设；空气与环境修正、色散近似尚需单变量实验区分。本轮没有新增原生数值，因此条目保持 `implemented`。

## 下一动作

1. 转录正式公式，建立 PgF 与环境修正的独立参考。
2. 原生恢复两进程门槛通过后，运行 B0/C1/C2/C3/B1/B2/B3 控制矩阵，保留直接折射率与双入射角 Snell 结果、实际波长和 solve 六字段。
3. 补保存重载、失败恢复及 `vary_abbe=True`，取得任务终态和正常关闭回执后，再判断完整声明范围。

探针加固与集成结果见 [本轮收口报告](parallel-02-material-model-20261108.md)。

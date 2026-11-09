# 编辑器扩展








本批实现TDE逐行修改、插入和删除，MFE/MCE/TDE统一插入、复制和元数据查询，以及原生`.tol`文件读写。原生设置采用与持久状态验收等待成功连接；普通检查和安装包stdio记录分别列出。

## 原生接口依据

本机`ZOSAPI_Interfaces.dll`反射确认三个编辑器均公开`InsertNewOperandAt`及`CopyOperands(fromOperandNumber, NumberOfOperands, toOperandNumber)`。TDE另有`LoadToleranceFile`、`SaveToleranceFile`；MFE已有`LoadMeritFunction`、`SaveMeritFunction`入口。MCE未公开独立Load/Save方法，使用现有完整系统保存和加载。



## 请求与结果

- `update_tolerances(request)`保留`replace/append`，新增`update/insert/delete`。`update`使用`updates`，每项包含1基`operand`及待修改字段；省略字段保留原值，显式null被拒绝。原生切换类型后，两种类型均启用且可写的遗漏字段保持原值。
- `insert`使用`at`和非空`operands`，按请求顺序连续插入；`delete`使用`operand_numbers`，编号对应编辑前的公差表，按降序删除。原生保留最后一行TOFF时，返回`placeholder_retained=true`。
- `get_tolerances(request)`增加`include_metadata=false`。开启后返回字段活动性、只读标志、数据类型、标题及原生可用类型。`Nominal`作为只读结果返回。Param1/2/3为有符号32位整数；Min/Max使用各原生操作数的单位。
- `insert_editor_rows(request)`：`editor=MFE/MCE/TDE`、1基`at`、`count=1..1000`及可选`operand_type`。未指定类型时采用原生新行类型；后续通过对应编辑器修改工具设置参数。
- `copy_editor_rows(request)`：同样三个编辑器，1基`start/at`及`count=1..1000`。返回原生复制数量、最终行数和实际目标行。引用重编号沿用原生处理，MCE结果包含实际solve。
- `get_editor_metadata(request)`：`editor`、1基`operand=1`、0基元数据列表偏移`column_start=0`、`column_count=30`。输出包含原生行类型、可用类型、列号、标题、数据类型、活动状态和只读状态；MCE列号为配置号，单独返回参数启用状态。
- `save_tolerance_file(path, overwrite=false)`保存`.tol`；`load_tolerance_file(path)`创建检查点后读取`.tol`并返回实际公差表。路径沿用现有绝对路径和覆盖约定。

写操作复用现有检查点与修订号，修改后回读请求字段。失败返回`PARTIAL_UPDATE`、已完成行、当前行或行数、原始原因及恢复检查点；当前状态读取失败时保留原始修改错误。

## 检查与限制

普通检查覆盖稀疏修改、活动字段、32位整数、类型拒绝、插入顺序、降序删除、TOFF占位、原生静默忽略、最终回读、状态读取失败和原始错误、公差文件载入及覆盖条件。真实stdio原生用例为`tests/native/test_editor_extensions_live.py`，包含表编辑、元数据、文件回读、系统保存重载和正常断开。



## 多配置评价函数替换回读（261）

多配置模型的replace请求以显式CONF行开头，CONF仅使用parameters第2列指定配置号，省略target/weight。省略字段经stdio保留，结构行的原生非活动目标/权重保持。替换完成后重新读取最终行类型、参数、目标和权重，拒绝原生自动插入导致的静默改写；失败返回实际完成项和检查点，便于读取和恢复。



## MCE数值回读精度（542）

本机MCE的DoubleValue getter返回九位有效数字。CRVT写入1/60后，getter为0.0166666667，实际曲面半径为59.99999999999988；Value和DoubleValue两种正式setter得到相同结果。update_configurations先保留原严格检查；仅在数值MCE因该getter精度被拒时，按已探查的九位表示核对。实际不一致或二次回读失败保留原始设置拒绝，其他单元格检查沿用原行为。

get_configurations的Double单元格新增value_readback，给出source、significant_digits=9、内部精度说明和探查证据；value仍是原生实际getter值。get_capabilities返回mce_double_readback。请求结构保持可用，示例见examples/requests/mce-precision542.json；先在独立模型中准备曲面1，再新增第二配置及CRVT行。

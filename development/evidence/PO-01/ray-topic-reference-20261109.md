# D001 偏振光线逐面参考与光纤接收场复测

日期：2026-11-09；执行主仓 `C:/Users/tonge/Desktop/mcp`；源码0.1.62未提交工作区。原生24.2.0/build240529/PremiumEdition，Windows/Python3.14.6，进程级 `COMPLUS_LoadFromRemoteSources=1`。原生串行执行，本轮未构建安装包。

## 实施范围与输入

PO-01.PolarizationRayTrace沿用正式专题、kind-only请求、AS_Default设置及UTF-16逐面文本出口；新增受控模型数值验收，不增加尚未经接口确认的选择字段。原正式接口反射见controls-20261109.md及official-settings-20261109.json。

新测试 `tests/native/test_polarization_topic_reference_live.py` 从独立新建模型开始：0.5876µm、中心视场、10mm入口瞳、无膜层、模型玻璃Nd=1.5/Vd=60/dPgF=0，第一面为平面或R=20mm球面，厚5mm，第二面平面出射，后接10mm空气与像面。三种Jones为X、Y和等幅90°相差。报告实际Hx/Hy/Px/Py用于正式CreateNormPol逐面终止对照，未假定默认光线等于主光线。行输出包含两折射面及像面，共3行。

请求：`{"request":{"kind":"polarization_ray_trace"}}`。Jones由update_system_settings写入并由报告头读取；比较0.5876µm实际波长。原生参数及修订记录保留在各次calls.json和任务JSON。

## 参考、容差与实际结果

Fresnel参考用n1/n2与入射余弦计算Rs/Rp、Ts/Tp；球面全系统功率另用tests/support/transmission_reference.py的解析球面—平面追迹参考。功率原门槛为atol=rtol=1e-6。逐面坐标和方向与正式批量光线对应；比较规则为1e-8+1e-7×|参考值|。相对复振幅使用归一化相干矩阵Ei·conj(Ej)/Σ|E|²，同样使用1e-8+1e-7×|参考值|；该比较消去共同传播相位，绝对相位基准留在PhaseAberration专题继续处理。

| 项目 | 平面系统最大绝对误差 | 球面系统最大绝对误差 |
| --- | ---: | ---: |
| 单面Rs/Rp/Ts/Tp | 1.5030e-9 | 1.6067e-9 |
| 累计批量功率 | 2.8888e-9 | 3.0175e-9 |
| 全系统解析功率 | 2.8890e-9 | 3.0443e-9 |
| 归一化相干矩阵 | 1.8071e-16 | 6.2047e-13 |
| 局部坐标，mm | 0 | 4.7225e-8 |
| 局部方向分量 | 0 | 4.9383e-13 |
| 保存重载后总透射 | 0 | 0 |

每模型268个数值断言，共536个通过。报告rows分页、任务succeeded、无cleanup_warnings、三种Jones同会话复用、完整系统偏振恢复、曲面/solve保持均通过。保存重载前后系统设置、曲面及报告头/逐面结果一致。该模型使用当前单配置、空评价函数；本用例未扩展多配置/评价函数断言。

最终命令：

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
& ./.venv/Scripts/python.exe -m pytest --run-zemax -q tests/native/test_polarization_topic_reference_live.py --junitxml=.local/evidence/development/PO-01/ray-topic-reference-reload-20261109.xml
```

2 passed，26.92s。原始目录：

- `.local/runs/runs/polarization_topic_plate_Infinity_d34e52b613/`
- `.local/runs/runs/polarization_topic_plate_20_444ed46182/`

两次最后disconnect响应均ok=true、connected=false；会话分别89e40b39db104e96870029f38dfb0bd4、a831dd93f0304081ad33dd6fb4703a5d。close_receipt.json为随后无连接shutdown回执（was_connected=false），关闭结论引用实际disconnect调用，未把该文件当成原会话关闭事件。

## N2探针修正与复验

新增Transmission可选择路径后，N2的model_dump()展开默认值，导致原本kind-only请求意外进入批量路径。现改为model_dump(exclude_unset=True)，单测明确四种请求均只传kind；公开工具/schema保持原值。

`.local/evidence/development/PO-01/n2-20261109-r7/`实际复验四任务succeeded；相位、偏振光线、原生Transmission三个报告Jones头跟随系统，restored_equal=true、restore_failures=[]、disconnect_ok=true。FiberCoupling报告缺少相同Jones头，follows=false记录为未提供头，不能作为偏振采用失败的判据。r6保留误进入批量透射路径的原始结果。

普通命令为相关测试加开发统计测试，XML在`.local/evidence/development/PO-01/ray-topic-unit-20261109.xml`：135 passed，1.88s。首次单独三专题普通66项通过；后续集合有重叠，不相加。

## 光纤耦合复测与正式定义

`tests/native/test_pupil_coupling_live.py --run-zemax`两项通过，134.25s：矩形瞳参考28次断言、最大差0.0122881，门槛0.02；POP倾斜高斯接收场306次断言、最大差8.9476e-9，重叠效率门槛5e-4。原始目录分别rectangular_pupil_c690368c0b和tilted_gaussian_96f9dea0d0，最后disconnect均ok=true、connected=false。此为既有POP接收场路径的本轮证据。

本机OpticStudio_UserManual_en.pdf第894—897页的Single Mode Coupling明确source/receiver NA、角度、去心、视场/波长/采样、对准主光线、Ignore Source、Use Polarization及Use Huygens Integral；接收效率为归一化复场重叠，总效率为系统效率乘接收效率。MODIFYSETTINGS第1541—1555页中取得的是POP_FIBERTYPE/POP_FPARAMn等POP入口，未取得专用FiberCouplingSettings的对应选择键。文本摘录位于`.local/evidence/development/WP-01/fiber-manual-20261109/`，保留原页码。

## 过程中的失败记录

- N2 r5误选同名.ZDA；open_lens返回INVALID_INPUT_FILE，未创建分析任务，finally断开记录保留。
- 首次平板用例假定只有两行，实际含像面第3行；修正测试预期，保留polarization_topic_plate_dd2054cf54。
- 下一次外部环境测试在connect返回REQUEST_TIMEOUT，未进行数值比较；请求e2fb02437f444415b1689d76d230092d保留在polarization_topic_plate_81c20befca。测试句柄已终止，进程查询未发现存活python/OpticStudio后，改用项目内环境执行，最终两轮原生通过。该次超时原因未定位，未归因为功能数值错误。

## 状态与下一步

PolarizationRayTrace保持in_progress：已完成默认光线的逐面Fresnel、相对复振幅、分页、复用及重载，尚需正式任意光线/波长/坐标选择、绝对相位约定及适用失败/取消验收。解除条件为正式专题选择接口/已公布CFG键，或覆盖同等逐面字段且可独立验收的正式替代路径。

FiberCouplingSettings保持implemented：POP参考通过；专用专题source/receiver选择和输入身份仍待确认。下一步核对正式Single Mode Coupling可脚本化设置，记录输入后与POP重叠参考逐项对应；已有相同接口反射不重复运行。

本轮新增完整功能0项，累计4/10，剩余92组/99条源记录/94个编号。修正verification-cycle.json中将Transmission误列last_verified_item_ids的问题：该项只做过逐项检查，集中检查尚未执行，基线列表恢复为空；生成计数为4/10、再6项集中检查。

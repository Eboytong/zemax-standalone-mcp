# MaterialModel与两类拾取：迁移后原生控制实验

## 范围、环境与实施计划

日期2026-11-09（本机Asia/Shanghai；原始时间戳按UTC保存）。主仓`C:/Users/tonge/Desktop/mcp`，源码0.1.62工作区，使用主仓`.venv/Scripts/python.exe`及进程环境`COMPLUS_LoadFromRemoteSources=1`。原生24.2.0 build240529 PremiumEdition。各进程串行执行。

MaterialModel计划运行精确/四位d/F/C及环境控制矩阵，比较直接ILDE.GetIndex与双入射角Snell，检查六项solve、vary_abbe和保存重载。拾取计划检查最终模式、来源/比例/偏移、源值联动、两次重载、代表光线、预检查拒绝、原生部分失败恢复和关闭。

## 修复及定向检查

修复三个直接Backend探针错误使用stdio `settings`包装的问题。拾取readback在Fixed/Automatic时保留原模式，在SurfacePickup但payload为空时记录具体错误；原先访问None导致探针提前退出。机械半口径受控源面的净半口径改小于请求机械尺寸，避免基线被原生强制钳制；源值扰动显式允许替换源面solve。

新增material探针请求与真实COMMAND_MODELS的契约检查；拾取fake dispatch也采用真实请求模型，并新增三种模式下null payload检查。最终定向普通测试命令：

```powershell
& ./.venv/Scripts/python.exe -B -m pytest tests/unit/test_pickup_adoption_helper.py tests/unit/test_pickup_probe_contracts.py tests/unit/test_material_model_reference.py tests/unit/test_material_probe_requests.py -q -p no:cacheprovider --basetemp=.local/tmp/ed02-unit-20261109-r3
```

最终r3结果：60 passed in1.03s，覆盖随后源值扰动和基线尺寸调整。

## MaterialModel结果

命令：`python -B -X utf8 scripts/probes/D002-MODEL_GLASS/model_glass_control018.py .local/evidence/development/ED-02/mm-20261109-r2`。

八个实验、11次模型/环境写入。B0 Nd=1.6、Vd=60、dPgF=.001；B1 Nd=1.5；B2 Vd=50；B3 dPgF=0；B4 vary_abbe=True。C1关闭环境修正，C2压力0，C3温度10。请求与实际完整保存在anchors.json。

| 组 | 正式谱线Vd | 正式d处Nd误差 | 六项solve/保存重载 |
| --- | ---: | ---: | --- |
| B0 | 60.02418808120307 | 1.9888117301913866e-6 | 通过/通过 |
| B1 | 60.024188081203604 | 1.6573431085298296e-6 | 通过/通过 |
| B2 | 50.020382919557946 | 2.3653440166526707e-6 | 通过/通过 |
| B3 | 60.02417428911052 | 1.9898635561510503e-6 | 通过/通过 |
| B4 | 60.02418808120307 | 1.9888117301913866e-6 | 通过/通过 |

容差保持Nd `1e-6+1e-7×abs(reference)`、Vd `1e-5+1e-7×abs(reference)`，上述主比较超限。C2/C3均SETTING_REJECTED，实际压力1 atm、温度20°C；记录完整响应并恢复基线后继续。C1可运行。环境各组恢复设置记录在environment_restores。

`acceptance_passed=false`、`diagnostics_passed=false`；双入射角与direct的逐点差保存在原始结果中。`save_reload_passed=true`，五个模型组均核对索引、六项solve及波长表。`closed=true`、`native.closed=true`、`forced=false`、无cleanup_error、无活动任务。

早期失败目录mm-20261109保留参数包装错误；r1保留环境拒绝导致提前终止；r2为最终完整控制矩阵。仍需正式色散公式/环境独立参考解释误差、dPgF数值参考及完整失败恢复模型比较，MaterialModel保持implemented。

## 两类拾取结果

入口：`python -B -X utf8 scripts/probes/ED-02/pickup_adoption_helper.py --cell <cell> --out <folder>`。

最终证据目录：`.local/evidence/development/ED-02/cz-20261109-r2/`与`msd-20261109-r1/`，各有anchors.json。早期目录保留脚本空对象错误、源solve保护及机械尺寸基线拒绝。

两组最终流程均error=null；ChipZone在更新、光线、两次保存重载和源值扰动后保持Automatic；机械半口径保持Fixed。均无时刻确认SurfacePickup；联动不通过。各有一条真实光线到像面3，state=succeeded且error/vignette为0。

预检查自引用拒绝为INVALID_SOLVE且未写模型；原生拾取请求部分失败保留PARTIAL_UPDATE、检查点、失败面实际状态及恢复记录。两组最终incomplete_reasons仅剩模式/参数/值与联动不通过，没有恢复或关闭缺项。`lifecycle.closed_confirmed=true`、native.closed=true、forced=false，任务终态完整。

两项保持blocked。解除条件：正式接口能实际采用并持久化对应SurfacePickup模式，然后重新执行现成联动与重载矩阵。原生计算通道本轮可用，当前阻塞归于具体设置采用。

本轮新增完整验收0项，累计保持3/10。

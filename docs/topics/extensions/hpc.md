# HPC 配置与任务

`get_hpc_settings` 读取本机正式 `IHPCSettings`，提供偏好与自定义两种有类型选择：

```json
{"request":{"mode":"preferences"}}
```

```json
{"request":{"mode":"custom","node_count":2,"instance_type":"Small"}}
```

自定义要求正整数节点数；规格为 `Default/Tiny/Small/Medium/Large/XLarge`。偏好模式只使用OpticStudio已保存配置。返回实际配置标志、节点数、最大节点数、规格、每任务线程数和关机ticks。自定义节点数及显式规格均核对采用值；Default的实际解析结果单独记录。

IHPCSettings属性均为只读；查询创建零个SystemTool。`is_configured=false` 可作为查询结果读取。实际节点、许可、调度与作业可用性由执行结果确认。

## 执行

四个现有入口新增可选 `hpc` 对象：

| 工具 | 本机HPC工厂 |
| --- | --- |
| run_nsc_ray_trace | OpenNSCRayTrace_HPC |
| run_tolerance_analysis | OpenTolerancing_HPC |
| run_global_optimization | OpenGlobalOptimization_HPC |
| run_hammer_optimization | OpenHammerOptimization_HPC |

```json
{"request":{"runtime_seconds":2,"hpc":{"mode":"custom","node_count":2,"instance_type":"Small"}}}
```

以上请求用于Global或Hammer入口。NSC及公差请求沿用各自原有字段，并加入同样的hpc对象。省略hpc沿用现有本机工厂；指定hpc后使用相应正式HPC工厂。原生未配置时返回 `HPC_NOT_CONFIGURED`，工厂及节点服务失败保留实际方法、配置和原生原因。

执行前解析HPC配置，随后写入并核对工具实际设置。NSC的HPC参数核对成功后才执行请求的探测器清空。NumberOfCores仍按原生工具设置写入和回读；HPC的ThreadsPerTask另行保留，两者在具体节点上的调度关系待原生验收。

任务查询、取消、结果分页、ZRD/公差文件、优化时间预算及关闭沿用现有链路。HPC配置写入任务设置及NSC追迹来源，原生工具配置拒绝时关闭工具；关闭失败同时保留原始修改错误并要求重连。时间预算沿用现有优化任务定义，排队、启动及停止时序仍须实际节点验证。

## 当前证据

本机设置接口、规格枚举及四个工厂已反射；有类型请求、实际设置核对和普通检查已实现。证据见 `.local/evidence/development/EXT-HPC/probe040.json`，例子 `examples/requests/hpc040.json`。

2026-11-08 parallel-02 已修正原生测试对成功响应的读取，新增独立成功验收入口 `tests/native/test_hpc_live.py::test_hpc_native_preferences_success_readback`。共享检查读取六项实际字段；`is_configured=false/node_count=0` 是有效查询结果，正式工厂返回空对象则记录具体原因并跳过成功验收。45 项相关普通检查通过，详见[本轮检查记录](../../../development/evidence/EXT-HPC/parallel-02-query-checks-20261108.md)。

本轮 API 在 `application_create` 阶段超时 180.1439575 秒，正式配置对象查询未执行；[启动诊断](../../../development/evidence/BASE-04/parallel-02-runtime-20261108.md)记录了常规 GUI 对照和强制收尾。原生恢复两进程门槛通过后，先运行配置成功用例，再分别验证四类最小任务、状态/取消、结果回收与关闭。直接光线探测器功率采用参考1、容差 `1e-8 + 1e-7×参考值`。公差与优化的分布、数值一致性及保存重载继续列入原生交叉验收。

接口参考：[IHPCSettings 2024 R2](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_tools_1_1_i_h_p_c_settings.xhtml)。各条目为implemented，原生验收待补。

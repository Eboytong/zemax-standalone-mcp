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




接口参考：[IHPCSettings 2024 R2](https://developer.synopsys.com/docs/zos-api-interface-2024-r2-sp02/interface_z_o_s_a_p_i_1_1_tools_1_1_i_h_p_c_settings.xhtml)。各条目为implemented，原生验收待补。

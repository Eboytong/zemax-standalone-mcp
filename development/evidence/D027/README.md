# D027：模式对照与发行检查

2026-11-11。D023冻结的60条检索任务和12条原生场景，使用Python3.14、MCP2.3.0、OpticStudio2024 R2/API24.2.0/build240529 Premium；原生调用串行。每个场景独立MCP及Standalone会话，full/compact交替先后顺序。输入、输出、数值、终态和断开在`.local/evidence/development/D027/<case>-<mode>/calls.json`。汇总见[summary.json](summary.json)。

## 对照结果

| 指标 | full | compact |
| --- | ---: | ---: |
| 真实stdio/native场景通过 | 12/12 | 12/12 |
| 初始工具目录UTF-8字节 | 1,432,668 | 12,862 |
| 冷启动场景耗时中位数 | 16.505秒 | 20.959秒 |
| 场景耗时P95 | 53.534秒 | 52.964秒 |

compact目录减少99.1022%。wavefront单能力详情1,145字节。两模式12组光学结果在1e-8+1e-7×参考值下相符；场景覆盖保存重载、真实光线分页、MTF/波前图像和网格、1W NSC/Viewer、POP/ZBF、局部优化、公差灵敏度、逐面损耗、候选恢复及有限共轭非球面材料试验。原有分项数值容差继续执行。

60题检索59通过；Q43跨域读取波前并保存候选，Top5命中候选/保存能力，原记录保留。测试是固定调用的协议与原生集成；模型推理完成率、实际模型输入token和缓存usage均未取得。宿主当前支持延迟工具发现，但未提供独立切换其提示组装/usage的观测接口。子Agent条件实验因父子总usage采集条件缺失未执行，保留为宿主侧选型项。

默认full保持现有直接工具兼容；compact供全目录加载客户端选择。已有数据证明目录缩减与原生调用等价；默认选型不以未观测的模型token收益为依据。

## 重跑

`.venv/Scripts/python.exe -B -X utf8 development/evidence/D027/compare.py`运行未成功场景；每对之间串行关闭，可指定场景ID。`summarize.py`整理原生对照、容差和检索结果。初轮优化用例缺MFE、候选创建缺评价合同、面型切换缺replace_solves已补齐，原始记录在本机证据中。

全量普通3775通过，70.37秒，见[XML](../release140-ordinary.xml)。最终注册/派发与玻璃定向47通过，23.39秒，见[XML](../D025-final-targeted.xml)。受影响原生回归、wheel独立安装和GitHub发行结果见[发行记录](../release140.md)。

1.4.0已于2026-11-11正式发布，标签v1.4.0对应源码a95c5b3；605030字节wheel上传完成。D027及本期五项全部完成，发布收据见[JSON](../release140-github.json)。

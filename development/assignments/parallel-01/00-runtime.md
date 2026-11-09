# Agent 0任务书：运行环境恢复、集成及原生执行协调

任务编号`BASE-04.RUNTIME`；完成计数0。共同约定见[并行安排](../../parallel-development.md)。**最新异常是`application_create`（`CreateNewApplication()`）180秒超时**（三次受控启动 runtime-recovery-01/02/05 一致）；CLR/API/connection 已完成，`clr_load: Failed to resolve Python.Runtime.Loader.Initialize` 的加载错误为**历史**结论、已不再是最新，当次尚未创建可用 OpticStudio 实例。

## 开工计划

先阅读`development/handoff.md`、`docs/guides/native-startup.md`及最新原始异常。发布本次计划，列出新进程复现、导入来源/依赖/运行时假设、最小修复、定向普通测试和原生连接关闭门槛。

## 工作顺序

1. 固定包含当前有效未提交及新增源码的共同开发起点，记录基线标识、Python环境、当前版本和后续个人分支入口。Git HEAD `bc289be`只记录已有提交。保留本机证据和输入的访问入口。
2. 在新的Python子进程复现，记录`sys.executable`、pythonnet/clr-loader及Python.Runtime的实际导入位置/版本、netfx加载阶段和完整异常链；将“导入失败”和“OpticStudio许可/实例创建失败”按实际阶段记录。
3. 逐一验证导入路径遮蔽、程序集/依赖来源和进程加载状态假设。使用有依据的最小修复，记录修改位置及运行环境变化。
4. 检查`NativeSession`的成功连接、复用、失败清理和断开；串行执行一个现有代表性分析，收集任务成功、结果读取和关闭回执。FRU警告另存定位记录。
5. 运行环境恢复后，通知各功能线可使用的源码/环境基线；接收原生作业请求并按D00x优先级串行执行。每个作业从所属分支/工作区执行，保存完整命令和输出路径。
6. 依据审查结论，依次应用功能Agent提交的共享入口补丁并执行受影响消费者的定向检查。在集成源码上执行用于关闭条目的原生验收，回报实际状态。

## 入口和所有权

主要阅读/修改`src/zemax_mcp/native.py`；按定位需要检查`config.py`、`bridge.py`及启动相关脚本。环境与依赖调整由本任务统一记录。`backend.py`、安装脚本或锁定依赖的修改需附具体原因和影响范围。

共享注册/模型入口由本任务作为集成负责人统一采用，各功能Agent提供经过普通测试的最小补丁。三份台账、批次、schema和总交接的最终更新交审查负责人。

## 定向检查

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_native_startup.py tests/unit/test_startup_license_probe.py tests/unit/test_runtime_lifecycle.py -q -p no:cacheprovider
```

根据修复涉及的实际路径补充消费者检查。原生检查优先复用已有真实stdio测试/启动诊断入口；先在计划中写明精确命令，再独占执行。

## 交付与完成条件

提交共同基线记录、复现输入/异常链、修复及原因、普通测试、原生连接/分析/读取/关闭证据、环境使用说明和原生作业队列。修复后若进入许可或其他外部阻塞，记录实际阶段与解除条件，其他Agent继续离线工作。

原生作业开始前登记工作区、版本、环境、命令、输出目录及预计时长；完成后登记任务终态、`close_attempted`、断开回执和遗留资源。每次关闭确认后交接下一作业。

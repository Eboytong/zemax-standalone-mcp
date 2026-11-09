# EX-01.StandaloneMacro 受控宿主复核

日期：2026-11-08

## 声明范围

验证独立 `.ZPL` 宏的有类型请求、命令行启动、输出结果、任务终态、取消/超时路径和进程关闭。现有实现入口为 `run_standalone_macro`，请求模型为 `StandaloneMacro`。

## 原生探查与执行

- OpticStudio 2024 R2 本机命令行参数 `-zpl`、`-v<Name>=<value>` 已通过手工 PowerShell 启动确认可被接受。
- MCP 真实 stdio 运行目录：
  - `.local/runs/runs/standalone_macro_b26a52bec5`
  - `.local/runs/runs/standalone_macro_73682d9066`
- 两次请求均使用绝对 `.ZPL` 文件，任务轮询到 `succeeded`，`exit_code=0`，`close_attempted=true`，PowerShell 日志记录 `OpticStudioExitCode=0`。
- 任务结果和进程日志均成功落盘，运行后未发现 OpticStudio、PowerShell 或 Python 残留进程。

## 结果与缺口

两次宏均包含文件输出/打印动作，但预期输出文件未生成，日志只有启动完成信息，未取得宏打印内容、宏返回值或可归属的原生结果出口。因此当前证据覆盖任务创建、轮询、退出及清理，不覆盖“宏已实际执行并产生结果”。命令行退出码不能单独证明宏执行成功。

## 结论

`EX-01.StandaloneMacro` 保持 `blocked`。解除条件：取得 OpticStudio 支持的独立宏执行协议（包括宏实际执行确认、输出/返回值或错误出口、取消/停止语义），或取得可由 MCP 可靠调用的正式宿主接口。现有有类型请求和资源清理链路保留，不计入 B006 完成数。


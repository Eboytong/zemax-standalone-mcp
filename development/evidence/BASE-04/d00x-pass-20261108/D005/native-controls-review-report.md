# N1/N2/N3 控制探针审查修订报告

- 日期：2026-11-08
- 范围：`scripts/probes/PO-01/{probe_common,n1_settings_surface,n2_system_polarization,phase_aberration_reference}.py` 与其定向测试
- 状态：审查提出的 5 项 + 收尾 2 项已全部落实；未创建 OpticStudio 应用，未提交 Git，未改公共台账
- 定向测试：`tests/unit/test_native_controls.py` **41 passed**（`python -B -m pytest tests/unit/test_native_controls.py -q -p no:cacheprovider`）

## 1. N1 `save_cfg`：不再用返回值真假判定成败

`SaveTo` 可能返回 `void`，因此不再调用 `bool(SaveTo(...))`：

- 保留**原始返回值与类型**：`return_value` / `return_type`（void 时为 `None` / `"NoneType"`）。
- `SaveToFailed` **在 SaveTo 之后**读取（`save_failed_flag_read_after_save: true`），测试替身故意在调用内才写入该标志。
- `saved` 的判定条件：本次调用未抛异常（`written_by_this_call`）且文件存在、字节数 > 0、可确证解码、`SaveToFailed` 为假。

覆盖用例：`test_n1_void_save_is_not_treated_as_failure`、`test_n1_save_failed_flag_read_after_save_wins`、`test_n1_records_unsaved_cfg_without_crashing`。

## 2. N1 CFG 读取：原始字节保留、编码可确证、损坏文本不作有效 CFG

- 原始 CFG 文件**留在磁盘**作为证据；记录只保留 `path`、`byte_count`、`bytes_hex_prefix`（前 32 字节）与编码身份。**已删除 hashlib/SHA 字段及对应用例**。
- 严格解码，由 BOM 决定：`ff fe`/`fe ff` → `utf-16`（`encoding_source: bom`）；`ef bb bf` → `utf-8-sig`；否则先 `utf-8`（`strict`），失败再试 `cp936` 并标记 `assumed`。
- 全程不使用 `errors="replace"`。无法解码时 `text=None`、`decoded=false`、`saved=false`，并保留 `decode_failures`；`cp936` 猜测成功时 `encoding_confirmed=false`、`text_trusted=false`，同样不判成功。
- 覆盖用例：`test_n1_undecodable_cfg_is_not_reported_as_valid_text`、`test_n1_utf16_bom_cfg_is_decoded_and_confirmed`、`test_n1_legacy_codepage_decode_is_marked_assumed`。

## 3. N1 `saved` 不受上一轮残留文件影响；每次探查使用全新文件名

- `saved` 现在要求 `written_by_this_call`：SaveTo 抛异常时即使目标路径上已有旧文件（`file_created=true`、`byte_count>0`），也判 `saved=false` 并记录本次异常 `save_error`。
- 每次 `probe` 生成自己的 `run_stamp`，CFG 命名为 `<Kind>-<run_stamp>.cfg`；`run_stamp` 写入记录，两轮探查不会互相覆盖。
- 覆盖用例：`test_save_cfg_failure_keeps_stale_file_from_looking_successful`、`test_each_probe_run_writes_its_own_cfg_names`。

## 4. N1 CLI：启动回执检查 + finally 记录断连与关闭回执

- 新增 `run_cli(backend, folder, model)`：`connect`、`open_lens` 均通过 `dispatch_checked` 保留 `ok` 与原始 `reply`。
- `connect` 失败或 `open_lens` 失败时**不构建 session、不执行探查**（不会去读空 system），并记录 `startup.aborted`；`session` 构建异常同样记录为 `session_failed`。
- `finally` 中始终执行 `disconnect` 并记录回执（`disconnect.ok`、`disconnect.reply`、`disconnect_receipt`）。
- 每个分析的关闭回执单独记录（`close_receipt`），关闭异常进入 `close_failures`。
- 覆盖用例：`test_n1_cli_aborts_before_probe_when_connect_fails`、`test_n1_cli_aborts_when_open_lens_fails`、`test_n1_cli_records_failed_disconnect_receipt`、`test_n1_close_receipt_is_recorded`、`test_n1_close_failure_is_listed_separately`。

## 5. N2 `poll_task` 超时：保留最后状态、请求取消、有界确认终态

- 超时写入 `poll_timeout`：`last_state`、已见状态序列、以及 `cancel` 子记录（`requested`、`receipt`、`terminal`、`final_state`、`error`）。
- 返回的任务对象带 `poll_timed_out` 与 `terminated_after_cancel`，调用方据此决策。
- **取消未确认终态时停止启动下一个分析**：后续 kind 记为 `skipped`，并写入 `aborted_native_task`。
- **恢复不与活动原生任务并行**：存在未确认终态任务时跳过 restore，记录 `restore_skipped.reason = "native task not confirmed terminal; restore must not run in parallel"`；确认取消后才恢复。
- 覆盖用例：`test_poll_timeout_preserves_last_state_and_requests_cancel`、`test_poll_timeout_records_confirmed_terminal_after_cancel`、`test_n2_timeout_without_terminal_cancel_stops_and_skips_restore`、`test_n2_confirmed_cancel_allows_restore`。

## 6. `paged_result`：禁止无限分页

- `next_start` 必须为整数、非重复、且**严格大于上一游标**：
  - 重复值 → `cursor_repeated`
  - 首次倒退（如 100→50）→ `cursor_not_advancing`
  - 非法类型 → `invalid_next_start`；超过 `max_pages` → `page_limit`
- `seen` 记录所有已请求游标，`last` 记录上一游标，两类边界分别断言。
- 覆盖用例：`test_paged_result_walks_next_start`、`test_paged_result_rejects_repeated_cursor`、`test_paged_result_rejects_first_backward_cursor`、`test_paged_result_rejects_invalid_next_start`、`test_paged_result_stops_at_page_limit`。

## 7. 断连成功按实际回执字段记录

- `disconnect_ok(reply)`：优先显式 `ok`/`success`；否则取 `connected is False`（同时兼容 `reply` 与其 `data` 层）。
- `record_disconnect` 保存 `ok`、`returned`、`reply`、`from_receipt`，不再以 `bool(dict)` 作为成功依据（`{"connected": false}` 之前会被误判为真）。
- N2/N3 均改用该记录方式；覆盖用例见第 4、5 节的 CLI 与离线端到端用例（`test_n3_probe_end_to_end_offline` 断言 `disconnect["ok"] is True`）。

## 8. 仍未运行（阻塞）

- 三个探针的原生执行（N1/N2/N3）仍为 `ready_not_run`：`application_create` 三次 180 s 超时未解除，证据 `development/evidence/BASE-04/runtime-phase-environment-20261108.md`。
- 因此本报告全部结论仅覆盖离线契约与失败/超时/分页/关闭路径，不构成原生行为验收。

## 9. 本次改动文件

- `scripts/probes/PO-01/probe_common.py`（回执判定、取消确认、严格分页、断连记录）
- `scripts/probes/PO-01/n1_settings_surface.py`（save_cfg 语义、严格解码、独立文件名、`run_cli` 回执检查）
- `scripts/probes/PO-01/n2_system_polarization.py`（超时中止、恢复串行化、断连回执）
- `scripts/probes/PO-01/phase_aberration_reference.py`（断连回执、超时标记）
- `tests/unit/test_native_controls.py`（上述全部定向用例，41 passed）

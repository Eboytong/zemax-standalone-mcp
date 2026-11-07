# 开发工作区

阅读顺序：`plan.md` → `current.md` → `handoff.md` → `ledgers/` → `generated/`。

常用命令：

```powershell
.\.venv\Scripts\python.exe -B tests\support\development_status.py --output development\generated\status.json --markdown development\generated\remaining.md --queue development\generated\queue.json
.\.venv\Scripts\python.exe -B -m pytest --collect-only -q -p no:cacheprovider
```

原生证据位于 `.local/evidence`，历史归档索引见 `archive/README.md`。

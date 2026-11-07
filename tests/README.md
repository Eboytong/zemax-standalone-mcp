# 测试入口

`unit/`：普通测试；`native/`：OpticStudio串行测试；`support/`：共享夹具与数值参考。

普通测试：`.venv/Scripts/python.exe -B -m pytest tests/unit -q -p no:cacheprovider`。
原生测试：追加 `--run-zemax`，从 `tests/native` 选择单个用例执行。

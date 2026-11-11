# D003 原生 Detector Viewer

日期2026-11-10；源码主仓 C:/Users/tonge/Desktop/mcp，基线fc814ef及当前修改。Python3.14，原生OpticStudio24.2.0/build240529，PremiumEdition。发行包1.0.0保持原有内容；当前源码102工具、133种分析请求。

## 接口与设置

新增 run_analysis:detector_viewer，类型请求区分current_detector/zrd。原生AnalysisIDM.DetectorViewer；Detector、ShowAs、DataType、Scale、Smoothing、RowCol逐项写入回读。枚举按值核对本机别名。当前来源清空RayDatabaseFilename/Filter；非空Filter限ZRD。旧run_zrd_replay可选显示字段复用相同适配。分析对象交由任务机制关闭，设置失败即时关闭。

## 模型、参考与数值

SourceRay位于(1,−2)，沿+Z发射1W；DetectorRectangle位于Z10，半宽2.5/3mm，5×3像素。原始get_detector_data作为辐射量交叉参考；Linear/0平滑Viewer单位W/cm²，每像素0.02cm²。当前与ZRD/H2共30点比较，容差1e-8W+1e-6×参考值；最大误差1.1102230246251565e-16W。像素中心X=[−2,−1,0,1,2]、Y=[−2,0,2]mm，区域分页一致。

Log_Minus_5及Smoothing2采用确认，三份PNG导出成功，逐次Viewer读取后原始累积值保持。CrossSection_Row输出有效一维数据；DetectorPolar采用Polar_AngleSpace并取得有效结构化结果。无效光源对象拒绝后可继续运行。清空Rectangle后取得全零网格，原生GetTextFile返回true却未生成文本，适配保留网格及具体导出状态。一般分析默认仍报告缺失文件。

取消实际经历cancelling→cancelled，close_attempted=true。Rectangle所有显示调用前后对象设置一致；后续切换Polar为用例的预期模型变更。guarded及常规disconnect均成功。

## 检查与原始记录

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_detector_viewer.py tests/unit/test_zrd_replay.py tests/unit/test_files_and_analysis.py tests/unit/test_nsc_analyses.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d003-final
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_detector_viewer_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d003-angular2
```

普通93 passed；真实stdio原生1 passed，23.44秒。记录 `.local/runs/runs/detector_viewer_native_eb3b9ae052/{calls.json,checks.json}` 包含请求、实际设置、终态、关闭及误差；图像在同目录。早期失败记录保留：空文本导出定位、测试取消异步等待修正、INVALID_LICENSE。用户重新授权后连接及以上执行成功。

参考G2固定版本用于确认正式设置；未复制其实现。完成D003声明范围，下一项D004。

D001—D003联合定向回归（含开发状态工具）259 passed，1.13秒；命令使用九个相关普通测试文件，basetemp=.local/tmp/pytest-stage-a。schema已重新生成。

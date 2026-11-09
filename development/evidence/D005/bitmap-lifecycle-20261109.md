# D005位图生命周期及设置入口

2026-11-09；条目IM-01.GeometricBitmapImageAnalysis，状态implemented。源码0.1.62，本机OpticStudio24.2.0/build240529/PremiumEdition，主仓.venv，COMPLUS_LoadFromRemoteSources=1。

正式依据：本机manual042.txt第3.2.8.3节及ModifySettings表1543—1544页；GBM条目列出FIELDSIZE/RAYS/XPIX/YPIX/XSIZ/YSIZ/INPUT/OUTPUT/SURFACE/ROTATION十键。Parity/Source/Normalize/Wavelength/Field/Reference等UI设置在该表无对应GBM键；既有AS_Default成员探查未取得专用设置对象。需要正式可写且能回读的入口，之后才能扩展这些请求字段。

新增tests/native/test_bitmap_image_live.py::test_bitmap_cancel_native_failure_reuse_and_model_reload，以真实stdio连接。自有200/100/200mm有限共轭Paraxial模型、128×128RGB源、10000光线/像素任务用于取消；源图改7×5、100光线/像素用于复用。输出17×11、0.1mm像素。

首轮XML bitmap-lifecycle-20261109.xml失败：测试错误地读取顶层error，原生失败实际位于task.error，已修正；原始calls在.local/runs/runs/bitmap_lifecycle_8fff9ce8da。修复后同一用例1项通过，18.22s，XML bitmap-lifecycle-20261109-r2.xml，实际调用在.local/runs/runs/bitmap_lifecycle_79bd286cbf。

已验：长任务cancelled；不存在资源写前INVALID_RESOURCE；损坏BMP触发failed/INVALID_RESULT_DATA并保留原生空文本路径；取消和失败任务close_attempted=true，无cleanup_warnings；同会话成功复用；保存重载前后设置、曲面、MFE和配置一致；重载后再次成功执行。最终disconnect响应成功。最终close_receipt因退出时无连接shutdown写为session_id=null，未将该回执作为前一会话原生关闭证据。

命令：主仓.venv/Scripts/python.exe -B -m pytest tests/native/test_bitmap_image_live.py::test_bitmap_cancel_native_failure_reuse_and_model_reload --run-zemax -q -p no:cacheprovider --basetemp=.local/tmp/bitmap-lifecycle-20261109-r2 --junitxml=.local/evidence/development/D005/bitmap-lifecycle-20261109-r2.xml。

下一步：取得其余正式设置与采用回读，定位效率/强度归一化及物理原点；生命周期本次覆盖范围沿用。完整验收仍3/10、剩余93组。

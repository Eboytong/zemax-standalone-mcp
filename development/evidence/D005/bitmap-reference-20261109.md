# D005几何位图：独立有限共轭参考

日期：2026-11-09（原生日志UTC为11月8日）。条目IM-01.GeometricBitmapImageAnalysis，状态implemented；集中验收3/10、剩余93组保持。

## 范围与依据

源码0.1.62，主仓C:/Users/tonge/Desktop/mcp；本机OpticStudio24.2.0/build240529/PremiumEdition。正式说明来自本机保留手册manual042.txt第3.2.8.3节（832—835页）：源像素和入口瞳随机均匀采样，源Y尺寸为全宽，探测器外光线计作渐晕；显示可按峰值或平均归一化。正式设置为AS_Default，沿用十项GBM配置键及原生报告回读。

自有模型：ObjectHeight，物距200mm、Paraxial焦距100mm、像距200mm，解析放大率−1；入口瞳直径2mm。自有7×5RGB图：左两列红255、上两行绿160、右下3×2蓝96。源全Y1mm；输出17×11，像素0.1mm。RGB采用专题默认波长，Paraxial模型无色散；系统波长0.55µm。

## 命令与原始记录

设置COMPLUS_LoadFromRemoteSources=1，使用主仓.venv/Scripts/python.exe：

```powershell
.\.venv\Scripts\python.exe -B scripts/probes/D005/bitmap_geometry.py .local/evidence/development/D005/bitmap-geometry-20261109
.\.venv\Scripts\python.exe -B scripts/probes/D005/bitmap_geometry.py .local/evidence/development/D005/bitmap-reference-20261109 --reference
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_bitmap_image.py tests/unit/test_native_bitmap.py -q -p no:cacheprovider --basetemp=.local/tmp/bitmap-reference-20261109 --junitxml=.local/evidence/development/D005/bitmap-reference-unit-20261109.xml
```

各原生目录probe.json保留源图、请求、逐次调用、模型、实际回读、完整结果、独立网格、任务和关闭回执。普通检查21项通过（0.45s）。首轮1/1000光线每像素为方向与噪声探查；第二轮事先写入参考和比较界限后执行10000光线每像素、0/90度两任务。

## 独立参考与结果

独立参考将源色块按放大率−1投影，90度按首轮确定的顺时针约定旋转，与固定探测器矩形逐像素求面积交叠；共同峰值归一化。90度含边缘裁切。参考未调用原生追迹或原生网格拟合。诊断界限预设6/sqrt(N)+2/255，在N=10000时为0.0678431372549；此为本受控样例的显示差比较界限，尚无原生随机种子/有限样本分布依据支持将它解释为统计置信区间。

| 旋转度 | 通道 | 最大归一化显示差 | 界限 | 通过 |
| ---: | --- | ---: | ---: | --- |
| 0 | R | 0.0352941176471 | 0.0678431372549 | True |
| 0 | G | 0.0274509803922 | 0.0678431372549 | True |
| 0 | B | 0.0156862745098 | 0.0678431372549 | True |
| 90 | R | 0.0549019607843 | 0.0678431372549 | True |
| 90 | G | 0.0313725490196 | 0.0678431372549 | True |
| 90 | B | 0.0156862745098 | 0.0678431372549 | True |

0度质心R=(13.4986216402,5.49891700305)、G=(8.49943952472,2.50145723574)、B=(4.50567933595,8.50218435998)，符合解析像方色块位置。峰值参考在该样例通过；最终Normalize默认模式及效率含义仍需正式采用证据。首轮原生报告出现350.719%的效率，保留原始值，未按物理功率使用。

## 生命周期、结论及下一步

首轮三项和参考轮两项任务均succeeded且close_attempted=true。两轮系统设置/曲面保持true；各自shutdown回执native.closed=true、forced=false、error=null。参考轮session为9bf9703f1fbb47a4acd7c79218bb3803。FRU__delta_init警告仍出现，未定位，应用正常关闭回执独立保留。

本轮补齐受控模型中的成像方向、三通道和90度裁切独立参考。完整功能仍待其余正式设置（Parity/Source/Normalize/Wavelength/Reference等）、效率/强度语义、取消/失败复用及保存重载；原物理原点未确认字段继续保留。下一步先探查这些设置的正式键与读回，补生命周期，再扩大参考条件；满足原声明范围后计完整验收。

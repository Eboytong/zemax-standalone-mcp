# D026：贡献分析与原生材料试验解耦

2026-11-11。Python3.14、OpticStudio2024 R2/API24.2.0/build240529 Premium Standalone。源码基线1.3.0加本轮修改。新增include_contributions默认true，原有贡献、完整groups和谱线条件保持；false采用材料赋值和原生评价本身的条件。get_glass_slots将面型条件放入contribution_conditions，材料身份/solve继续保护。

原生受控模型：有限物距500mm、EvenAspheric入面、N-BK7/N-F2、单波长0.55µm、ObjectHeight、Radial归一化；替换N-BK7/N-BAK4，共两组合。每组合DLS固定1循环、面3厚度65–110mm、RSCE采样3环。关闭贡献，实际原生材料回读、RMS/波前/EFL/MTF、优化、候选保存、独立重载和副本关闭通过。

随后从同一基线按公开原生工具逐候选赋材料→建立相同RSCE和CTGT/CTLT→设置相同变量→DLS1循环→读取RSCE及厚度。两条路径按1e-8+1e-7×参考值比较，两组合全部通过；实际值和误差在`.local/runs/runs/d026_optional_contribution_a0de29b946/checks.json`。源模型和系统设置在副本试验后保持，恢复基线后参数一致。

命令：`.venv/Scripts/python.exe -B -m pytest tests/native/test_glass_optional_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d026-native-final --junitxml=development/evidence/D026-native-final.xml`。1通过，37.57秒，正常disconnect。前两次失败为测试读取字段rows误用，分别修正为operands和surfaces/cells；原始失败XML保留，产品数值未超差。

普通检查覆盖贡献默认兼容、谱线独立、非球面/部分材料段及solve保护。原有贡献模型、错误恢复与取消在最终受影响回归中继续检查。自主组合、显式joint_slots与预算搜索说明见使用指南和请求示例。

最终compact原生回归4通过，274.07秒：原贡献模型的目录试验、采样/矩阵参考、保存重载、空替换与取消；联合优化取消、候选恢复及逐面损耗取消均通过。安装包独立导入再运行本用例通过，原始目录`d026_optional_contribution_f12fb12903`，99次调用以成功disconnect结束。见[原生回归](../release140-native.xml)和[安装包原生](../release140-installed-native.xml)。

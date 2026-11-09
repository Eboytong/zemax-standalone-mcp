# YNI报告恢复审计与结果读取加固

2026-11-08；源码0.1.61工作区，OpticStudio24.2.0 build240529 PremiumEdition，Python3.14。

计划：保留原有Cooke报告定义及逐面数值门槛，补有限性/顺序错误、分页、模型保持和任务关闭。原有默认报告有typed kind-only请求，缺少显式波长选择，原声明范围保持未完成。

实现：YNI波长须为有限正数；每行贡献须有限，面号须严格递增；损坏数值行整体拒绝，避免返回部分表。接受原生两种微米字符。新增10项普通边界场景（NaN/inf/overflow、无效词、重复/倒序、非正波长和合法零贡献）。请求字段未变化，无schema增量。

命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_yni_contributions.py tests/unit/test_contracts.py -q -p no:cacheprovider`，46通过。

原生：`.venv/Scripts/python.exe -B -m pytest tests/native/test_yni_contributions_live.py --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/CV-01/yni-recovery-audit-20261108.xml`，1通过，9.25秒。输入本机Cooke 40 degree field.zos，当前配置；0.55微米、毫米，面1-6数值对原生文本参考仍为atol=1e-12、rtol=0。新增start=2,count=2分页正确返回面3/4和总数6；任务succeeded、close_attempted=true，系统设置前后相同，disconnect成功。原始调用`.local/runs/runs/yni_contributions_a47c2cdb8e/calls.json`。启动FRU警告仍保留。

新正式依据：Ansys 2024 R2手册YNI Contributions明确给出Wavelength选择，并说明YNIP操作数对应同一定义（近轴边缘光线高度×折射率×入射角）。官方地址：https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/YNI_Contributions.html 。这为显式波长请求提供了可探查的正式替代路径，尚未验证本机YNIP参数及数值对应关系。

结论：结果处理修复完成，默认报告重测通过，功能保持implemented，B006不增计。下一动作先确认本机YNIP的Surf/Wave参数，使用正式GetOperandValue与默认报告逐面对照，再在通过后接入显式波长请求；独立近轴参考和生命周期一并验收。源光谱与方向性图按队列继续。

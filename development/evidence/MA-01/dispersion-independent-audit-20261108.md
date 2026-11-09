# 色散图与色散随波长独立参考审计

日期2026-11-08；源码0.1.61加未发行修改，OpticStudio24.2.0 build240529 PremiumEdition，Python3.14。

## 计划与参考

核对kind-only请求、原声明范围、实际AS_Default设置、报告材料身份、单位、分页、模型保持及关闭。固定本机SCHOTT.AGF的BK7G18、公式2的六项CD系数，以独立Sellmeier公式及其解析导数比较101个波长节点。折射率和导数的新增诊断门槛均预设绝对5.1e-8，rtol=0；原99点中心差分验收门槛仍为5e-5，未改动。

本机Rad_Hard.AGF也含同名BK7G18，使用公式1及不同系数；本次参考明确锁定SCHOTT，并检查任务系统设置确实加载SCHOTT。不能仅凭材料名合并两份目录。

## 执行与结果

普通命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_dispersion_diagram.py tests/unit/test_contracts.py -q -p no:cacheprovider`，41通过。

新增严格解析导数实验首次原生执行失败，保留`.local/evidence/development/MA-01/dispersion-independent-audit-20261108.xml`及`.local/runs/runs/dispersion_vs_wavelength_native_7e4d457054/`。离线读取完整输出，折射率最大差4.966168343223387e-8，解析导数最大差5.9190213202997555e-8；四个节点超过新增门槛。该失败保留，未扩大容差。

定位实验：用相同SCHOTT系数分别计算中心差分，半步长1e-2/1e-3/1e-4/1e-5/1e-6微米。1e-4半步长的101点最大差4.921866580617773e-8，其他小步长仍有四点超过5.1e-8。结果支持原生采用有限差分的假设，原生步长尚无正式定义依据。

最终测试将上述解析导数比较作为完整诊断文件保存，折射率仍执行5.1e-8严格断言，原中心差分5e-5验收断言保持。命令：`.venv/Scripts/python.exe -B -m pytest tests/native/test_dispersion_vs_wavelength_live.py --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/MA-01/dispersion-independent-diagnostics-20261108.xml`，1通过，9.40秒。该通过不覆盖尚未满足的解析导数诊断门槛。

完整逐点参考、六项CD系数和误差：`.local/runs/runs/dispersion_vs_wavelength_native_4dd6492208/independent-derivative-diagnostics.json`；请求/实际设置/任务结果/断连见同目录calls.json。原生任务成功、分页和模型保持通过，disconnect正常。两次启动均有FRU__delta_init警告，继续归入BASE-04。

## 状态与下一步

两项均保留implemented：原生报告适配已实现；任意材料及环境选择仍无正式设置回读，色散导数还需正式差分定义。已支持的当前系统报告与完整条目范围分别记录，不计新增B006完成数。下一步取得正式差分步长或算法定义，再复验独立导数；选择缺口等待正式接口或可验证CFG键。继续下一项玻璃图范围审计。

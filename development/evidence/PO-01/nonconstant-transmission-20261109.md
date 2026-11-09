# D001正式接口与非恒定瞳透射

日期：2026-11-09。主仓C:/Users/tonge/Desktop/mcp，源码0.1.62未发行工作区；Python为主仓.venv，进程COMPLUS_LoadFromRemoteSources=1。原生OpticStudio24.2.0 build240529 PremiumEdition，当前配置1、镜头单位Millimeters，全部原生执行串行。

## 计划与范围

核查正式程序集的专题设置类型，并用球面—平面无镀膜模型验收随瞳位置变化的Fresnel透射。正式选择器、吸收/渐晕、失败与取消完整范围继续逐项处理；本次覆盖非恒定瞳、Jones采用和模型恢复。

## 正式接口探查

新增scripts/probes/PO-01/official_settings_inventory.py。命令：`python -B -X utf8 scripts/probes/PO-01/official_settings_inventory.py .local/evidence/development/PO-01/official-settings-20261109.json`。

加载本机ZOSAPI_Interfaces.dll，枚举908个公开导出类型，137个设置相关类型；保留程序集身份、全部设置类型名称及相关成员签名。本次只反射程序集，未创建原生应用。

四个D001专题未发现名称匹配的专用设置接口；结合已有N1的实际AS_Default及30个公开成员，仍未取得专题视场/波长/采样/接收场选择路径。名称搜索的范围为公开导出类型，不据此断言所有正式替代路径均不存在。D002可继续采用已公开IAS_GrinProfile的Surface、Wavelength、ShowIndexVs及坐标范围成员。

## 独立参考与检查

新增tests/support/transmission_reference.py：球面半径20mm、轴向平行入射，首面入射角asin(r/R)，折射方向由Snell定律独立求得；后续平面入射角为两角之差。两界面分别计算s/p Fresnel功率，按每条光线径向/方位偏振分量合成。

模型：入口瞳直径10mm；面1半径20mm、厚度5mm、模型玻璃Nd1.5/Vd60/dPgF0；面2平面出射至空气，后厚度10mm；两面半口径6mm、无镀膜；单波长.5876µm、轴上视场。自有32×32像素中心圆瞳812点，分别执行X/Y线偏振，并执行非偏振原生全瞳分析。每偏振逐点参考变化超过.005，以确认覆盖非恒定透射。

参考程序3项普通测试通过：正常入射极限、Brewster p分量无反射、位置与Jones共同旋转不变及方向差异。

最终命令：`python -B -m pytest tests/native/test_transmission_pupil_reference_live.py::test_transmission_nonconstant_pupil_spherical_plano_fresnel --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/transmission-nonconstant-20261109-r2 --junitxml=.local/evidence/development/PO-01/transmission-nonconstant-20261109-r2.xml`。

最终1 passed in13.03s。原始调用与1627项数值检查位于`.local/runs/runs/transmission_nonconstant_pupil_9b4a4bd23f/`。两种线偏振1624条光线均成功且无追迹错误，独立逐点参考最大误差3.034468565310533e-9。X/Y/非偏振原生全瞳结果均约0.921578196，独立32×32圆瞳均值约0.92157736574，差约8.3026e-7。最终逐光线及全瞳比较均使用atol1e-6、rtol1e-6。首次探查全瞳使用1e-4诊断门槛；最终复验收紧至上述既有Fresnel门槛并增加非偏振，首次结果留存但不替代最终验收。

## 实际采用与生命周期

检查原生Jones头、32×32采样、非偏振头、逐光线状态/数量、系统设置和曲面恢复。真实stdio的disconnect成功，connected=false、requires_reconnect=false，保留last_session与模型修订9及checkpoint。stdio退出后的close_receipt被无连接shutdown覆盖，session_id=null、was_connected=false；该文件不作为本会话关闭的独立回执。已执行关闭依据为工具disconnect成功响应及stdio正常退出。

## 状态与下一步

Transmission保持in_progress，累计完整验收3/10，剩余93组。非恒定瞳Fresnel缺口已补；继续正式专题选择路径、渐晕/吸收组合、分页及适用失败/取消生命周期。相位及其他D001状态保持；缺正式接口条目记录条件后按D002队列继续。

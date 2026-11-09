# 双目发散/会聚

`run_analysis`新增`biocular_dipvergence_convergence`，当前done，完整验收见acceptance414-biocular.json；历史推进记录保留，见`.local/evidence/development/CV-02/acceptance414-biocular.json`。

```json
{"request":{"kind":"biocular_dipvergence_convergence","left_configuration":1,"right_configuration":2,"wavelength":1,"scan_axis":"Y","use_angles":true,"minimum":5,"maximum":-5,"offsets":[-5,-3,-1,1,3,5],"points":21,"convergence_offset_mrad":0}}
```

默认左右配置1/2、波长1、Y扫描、角度模式、−5至5、偏移[0]、21点、会聚补偿0。配置和波长编号从1开始。扫描允许反向及相同端点；points为2–1001；最多六条偏移，−99禁用槽，至少一个活动偏移。X扫描时偏移为Y，Y扫描时偏移为X。角度为度，方向余弦模式要求每点X²+Y²<1。角度限制在开区间(−90,90)。

本机正式操作数为BIOC和BIOD，分别返回会聚和垂直发散，单位毫弧度。原生以左眼配置为参考，迭代右眼主光线匹配同一像面坐标；从STOP中心出发，STOP之前的曲面沿原生定义忽略。每行保存八项原生参数、原始会聚值及减去convergence_offset_mrad后的显示值。series每条偏移包含发散/会聚两列，actual_settings保存请求、活动槽和当前配置。

专题接口是AS_Default，原生文本可导出；当前方法直接查询正式操作数。活动配置在查询后核对并按需恢复，恢复失败进入重连状态。无独立分析工具实例由此查询路径创建。

已通过：69项普通检查；双平面100/120mm的X/Y反向扫描独立参考20点，绝对容差0.001mrad，原表面/配置/MFE保持和正常断连。仍待余弦、六偏移、原生文本逐点对照、补偿/眼位交换、截断与原生失败、分页/绘图/取消/重载及配置2状态检查。双目FOV另有条目，当前数组/文本出口不足，继续探查绘图及直接追迹契约。


2026-11-07 推进409：普通相关98通过；408六偏移/余弦/补偿/同眼/配置2/分页/PNG查看/取消复用/重载通过，284次数值检查最大差3.5366e-5mrad，保持0.001mrad容差。但407探查句柄7977仍live时启动了408，违反串行要求，408证据暂存、验收前须串行复测。407无probe.json，阶段未定位；明确Ctrl-C后exit1，PID7732/13692/21456均已消失，未取得正式Close记录。脚本现已逐阶段落盘并支持clipping_only隔离；下一步先定位截断操作数错误契约，结束句柄后再串行复测408。条目implemented/B0052/10保持；当前无已知运行原生句柄。详见CV-02/progress409-biocular.json。


2026-11-07 双目完成414：隔离410确认截断BIOC/BIOD静默返回0；新增两眼独立副本STOP真实追迹和像点残差核对，原始0保留、无效显示null，全无效NO_VALID_BIOCULAR_POINTS，消除假零成功。串行411/412三类原生用例通过，共307次参考检查、最大差4.344098438302524e-05mrad（预设0.001mrad）；普通106通过，涵盖原始失败与恢复/关闭失败保留。六偏移、余弦、补偿、眼位交换、同眼、配置2保持、分页/PNG查看、取消复用、重载与所有副本/会话关闭通过。409调度问题与旧408暂存记录继续保留，验收采用新串行结果。条目done，B0053/10，剩余132组/143源记录；源码104种分析，wheel0.1.60仍100种。证据CV-02/acceptance414-biocular.json。下一条双目FOV，当前无运行原生句柄。


每点用独立配置副本从STOP中心验证左右眼真实光线。右眼角由原生会聚/发散增量重建，核对两侧通过状态及像面X/Y匹配残差，容差为1e-5+1e-6×最大像点坐标（镜头单位）。验证失败保留raw_dipvergence_mrad和raw_convergence_mrad，显示值为null，状态invalid；summary统计valid/invalid，整组无有效点返回NO_VALID_BIOCULAR_POINTS。副本关闭和配置恢复失败分别保留原始异常并进入重连处理。

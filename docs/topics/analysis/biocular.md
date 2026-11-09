# 双目发散/会聚


```json
{"request":{"kind":"biocular_dipvergence_convergence","left_configuration":1,"right_configuration":2,"wavelength":1,"scan_axis":"Y","use_angles":true,"minimum":5,"maximum":-5,"offsets":[-5,-3,-1,1,3,5],"points":21,"convergence_offset_mrad":0}}
```

默认左右配置1/2、波长1、Y扫描、角度模式、−5至5、偏移[0]、21点、会聚补偿0。配置和波长编号从1开始。扫描允许反向及相同端点；points为2–1001；最多六条偏移，−99禁用槽，至少一个活动偏移。X扫描时偏移为Y，Y扫描时偏移为X。角度为度，方向余弦模式要求每点X²+Y²<1。角度限制在开区间(−90,90)。

本机正式操作数为BIOC和BIOD，分别返回会聚和垂直发散，单位毫弧度。原生以左眼配置为参考，迭代右眼主光线匹配同一像面坐标；从STOP中心出发，STOP之前的曲面沿原生定义忽略。每行保存八项原生参数、原始会聚值及减去convergence_offset_mrad后的显示值。series每条偏移包含发散/会聚两列，actual_settings保存请求、活动槽和当前配置。

专题接口是AS_Default，原生文本可导出；当前方法直接查询正式操作数。活动配置在查询后核对并按需恢复，恢复失败进入重连状态。无独立分析工具实例由此查询路径创建。

已通过：69项普通检查；双平面100/120mm的X/Y反向扫描独立参考20点，绝对容差0.001mrad，原表面/配置/MFE保持和正常断连。仍待余弦、六偏移、原生文本逐点对照、补偿/眼位交换、截断与原生失败、分页/绘图/取消/重载及配置2状态检查。






每点用独立配置副本从STOP中心验证左右眼真实光线。右眼角由原生会聚/发散增量重建，核对两侧通过状态及像面X/Y匹配残差，容差为1e-5+1e-6×最大像点坐标（镜头单位）。验证失败保留raw_dipvergence_mrad和raw_convergence_mrad，显示值为null，状态invalid；summary统计valid/invalid，整组无有效点返回NO_VALID_BIOCULAR_POINTS。副本关闭和配置恢复失败分别保留原始异常并进入重连处理。

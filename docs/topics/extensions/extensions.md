# 已有扩展资源查询与历史宿主记录


## 已有资源查询

`get_system_resources`支持`kind=extension_files`，通过`extension_role`选择资源：

```json
{"request":{"kind":"extension_files","extension_role":"user_analysis","query":"Sample","start":0,"count":20}}
```

资源角色包括surface、source、object、surface_scatter、bulk_scatter、physical_optics、gradient_index、birefringence、diffractive、user_analysis、user_operand、extension、library和zpl。使用原生应用的ZemaxDataDir/ZPLDir，返回目录、存在状态、过滤后的文件名、总数及下一页。目录查询错误保留原因；缺目录返回空列表及`directory_exists=false`。


## 宿主与宏的历史状态

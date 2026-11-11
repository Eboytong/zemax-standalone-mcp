# 按工程需求查找能力

`search_capabilities`在未连接OpticStudio时即可使用。它返回工具、分析kind、匹配词、单位、前置条件和详情请求；参数、枚举、范围及默认值由当前请求模型生成。

```json
{"query":"镀膜反射率透射率吸收率","limit":5,"category":"all"}
```

检索结果中的`detail_request`可直接传给`get_capabilities`：

```json
{"topic":"detail","capability_id":"tool:get_coating_rta"}
```

读取`request_schema`后，连接、打开模型，再调用对应工具。分析结果的`analysis_kind`通过`run_analysis`的`request.kind`选择。`availability.static`说明适配状态，原生执行按当前模型、资源和许可确认。

完整索引使用`get_capabilities(topic="index",start=1,count=100)`分页，编号从1开始。`topic="dependencies"`返回指定能力的条件及修改作用。检索的`category`可选择`tool`或`analysis`，默认`all`。

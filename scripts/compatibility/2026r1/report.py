import collections
import csv
from datetime import datetime
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pydantic import TypeAdapter
from zemax_mcp.analysis_models import AnalysisRequest

def records(name):
    path=OUT/name
    if not path.exists(): return []
    values=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try: values.append(json.loads(line))
        except json.JSONDecodeError: pass
    return values

all_tests=json.loads((OUT/'collected-tests.json').read_text())
native_tests=[t for t in all_tests if t.startswith('tests/native/')]
rows=records('test-results.jsonl')
latest={x['test']:x for x in rows}
counts=collections.Counter(x['outcome'] for x in latest.values())
def classify(row):
    text=str(row.get('reason',''))
    if 'IGES' in text and ('层号' in text or 'layer' in text):return 'IGES 多配置图层限制'
    if 'run_nsc_conversion' in text and 'An unknown error occurred' in text:return 'NSC 分组转换原生错误'
    if 'BUDGET_EXCEEDED' in text:return '计算预算耗尽'
    if 'time.monotonic()<deadline' in text:return '测试等待超时'
    if 'INVALID_INPUT_FILE' in text:return '测试样例路径'
    if 'request.detector_viewer.detector' in text:return '参考测试请求不符合接口'
    if 'FileNotFoundError' in text and 'tmp' in text:return '测试临时目录准备'
    if 'nsc_unit_fixtures.py' in text and 'No such file' in text:return '测试夹具搬迁后的旧路径'
    if 'Abbe' in text:return '材料 Abbe 数值参考超差'
    if 'assert 348 == 346' in text:return '玻璃图旧版固定目录计数'
    if 'test_glass_trials_native_stdio' in text and "identity" in text:return '材料候选池未覆盖不同 Nd'
    if 'coherent pupil slice' in text:return '相干 FFT 线扩散数值参考超差'
    if 'PSF Fourier MTF' in text:return 'PSF 傅里叶与原生 MTF 数值超差'
    if 'path CDF 3mm' in text:return '散射路径 CDF 超差（观察到边界几何差异）'
    if '评价函数最终目标或权重未采用' in text:return '评价函数浮点严格相等导致回读误拒绝'
    if 'NSC_TRACE_ERRORS' in text:return '导入模型原生追迹出现错误光线'
    if 'LoadNETCallback returned null' in text:return '受控 .NET 回调装载返回空值'
    if 'CriticalRayData' in text and 'RESULT_UNAVAILABLE' in text:return 'CriticalRayData 原生结果不可用'
    if 'There are no uncategorized paths' in text:return '路径阈值过滤后未提供未分类通量'
    if 'STAR import file did not match' in text:return 'STAR 导入回读为 ZST 容器路径'
    if 'constant temperature' in text and "'actual': 0.0" in text:return 'STAR 温度拟合采样为0（输入恒温21度）'
    if 'STAR component creation or selection was not adopted' in text:return 'STAR 组件刚体添加坐标断点未通过回读'
    if 'NO_RESULT_DATA' in text and 'STAR' in text:return 'STAR 未返回有效数据'
    if 'ABgFile' in text and 'UNSUPPORTED_SETTING' in text:return 'ABgFile 散射资源接口不可用'
    if 'macro_result.txt' in text and 'FileNotFoundError' in text:return '独立宏运行后未生成预期输出'
    if 'uniform-area batch versus GaussQuad' in text:return 'QuickYield 瞳采样数值参考超差'
    if 'map Centroid SpotRadius' in text:return 'RMS 视场图数值参考超差'
    if 'circular pupil incoherent' in text:return '曲面 MTF 圆瞳参考超差'
    if 'PSF/OTF' in text:return '曲面 MTF 与 PSF 傅里叶参考超差'
    if "KeyError: 'series'" in text and 'test_analytic_analyses_live' in text:return '原生离焦 MTF 无效结果仍标为成功'
    if 'FileNotFoundError' in text:return '测试资源搬迁路径或历史输入缺失'
    if 'CoordinateBreak' in text and 'SOLVE_UPDATE_FAILED' in text:return 'Coordinate Break 测试夹具设置'
    if 'setting' in text and '圆锥系数' in text and "'inf'" in text:return '非活动圆锥系数测试夹具设置'
    if 'Tilted' in text and '曲率半径' in text and "'inf'" in text:return '非活动曲率单元格测试夹具设置'
    if '18.135027806' in text:return '保存重载浮点精确相等断言'
    return '待逐项分析'
problem_groups=collections.Counter(classify(x) for x in latest.values() if x['outcome']=='failed')
calls=records('native-calls.jsonl')
expected_tools=set(json.loads((OUT/'tool-names.json').read_text(encoding='utf-8')))
expected_analysis=set(TypeAdapter(AnalysisRequest).json_schema()['discriminator']['mapping'])
tools=collections.defaultdict(lambda:dict(calls=0,ok=0,errors=0,tests=set()))
analyses=collections.defaultdict(lambda:dict(calls=0,accepted=0,task_ids=set(),tests=set()))
tasks={}
for c in calls:
    name=c['tool']; q=c.get('arguments') or {}
    if name in ('execute_capability','query_capability'):
        wrapper=tools[name];wrapper['calls']+=1;wrapper['ok']+=int(bool(c.get('ok')));wrapper['errors']+=int(not c.get('ok'));wrapper['tests'].add(c['test'])
        target=q.get('capability_id','')
        if target.startswith('tool:'): name=target[5:]; q=q.get('arguments') or {}
        elif target.startswith('analysis:'): name='run_analysis'; q={'request':{'kind':target[9:]}}
    t=tools[name];t['calls']+=1;t['ok']+=int(bool(c.get('ok')));t['errors']+=int(not c.get('ok'));t['tests'].add(c['test'])
    if c.get('task_id') and c.get('state'):
        tasks[c['task_id']]=c['state']
    kind=(q.get('request') or {}).get('kind') if name=='run_analysis' else None
    if kind:
        a=analyses[kind];a['calls']+=1;a['accepted']+=int(bool(c.get('ok')));a['tests'].add(c['test'])
        if c.get('task_id'):a['task_ids'].add(c['task_id'])
unit={}
unit_failures=[]
if (OUT/'unit.xml').exists():
    tree=ET.parse(OUT/'unit.xml')
    cases=tree.findall('.//testcase')
    unit=dict(total=len(cases),passed=sum(not any(c.find(tag) is not None for tag in ('failure','error','skipped')) for c in cases),
        failed=sum(any(c.find(tag) is not None for tag in ('failure','error')) for c in cases),skipped=sum(c.find('skipped') is not None for c in cases))
    unit_failures=[dict(test=c.get('classname','')+'::'+c.get('name',''),reason='\n'.join(n.text or '' for tag in ('failure','error') for n in c.findall(tag))) for c in cases if any(c.find(tag) is not None for tag in ('failure','error'))]
modules=records('module-results.jsonl')
module_count=len(list((ROOT/'tests/native').glob('test_*.py')))
resolved=[x for x in rows if x['outcome']=='failed' and latest[x['test']]['outcome']=='passed']
resolved=list({x['test']:x for x in resolved}.values())
active=json.loads((OUT/'active.json').read_text()) if (OUT/'active.json').exists() else {}
summary=dict(updated=datetime.now().astimezone().isoformat(),active=active,native=dict(collected=len(native_tests),completed=len(latest),not_completed=len(native_tests)-len(latest),**counts),problem_groups=dict(problem_groups),
    unit=unit,modules_completed=len({m['module'] for m in modules}),module_runs=len(modules),modules_total=module_count,resolved_failures=resolved,tools_seen=len(expected_tools & set(tools)),tools_total=len(expected_tools),
    analyses_seen=len(expected_analysis & set(analyses)),analyses_total=len(expected_analysis),
    tools_missing=sorted(expected_tools-set(tools)),analyses_missing=sorted(expected_analysis-set(analyses)),
    failed_tests=[x for x in latest.values() if x['outcome']=='failed'],skipped_tests=[x for x in latest.values() if x['outcome']=='skipped'],
    unit_failures=unit_failures)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# OpticStudio 2026 R1 全功能试验','',f'更新：{summary["updated"]}',
    '',f'原生测试：收集 {len(native_tests)} 项，已完成 {len(latest)} 项；通过 {counts["passed"]}、失败 {counts["failed"]}、跳过/预期限制 {counts["skipped"]}。',
    f'已结束模块：{len({m["module"] for m in modules})}/{module_count}。当前状态：'+('全部计划试验已结束。' if active.get('state')=='finished' and len(latest)==len(native_tests) else f'`{active}`。'),
    f'工具调用覆盖：{summary["tools_seen"]}/{len(expected_tools)}；run_analysis 请求覆盖：{summary["analyses_seen"]}/{len(expected_analysis)}。',
    f'普通测试：{unit}。','',
    '结论：设置v261安装目录后，MCP可连接本机2026 R1并完成大部分建模、追迹、分析、优化和文件操作。当前结果包含下列未通过项目，需按具体功能采用测试结论。',
    '环境：Python 3.14.10 x64，MCP 1.4.0，OpticStudio API 26.1.0 / build 260127，EnterpriseEdition。',
    '使用仓库原生测试及补充覆盖用例，逐个独立进程串行执行；测试环境转发 v261 安装目录。测试夹具调整涉及安装路径、搬迁路径、目录计数和等待上限。首轮按模块限制1800秒，补跑按用例限制3600秒。产品源码保持原样。',
    '覆盖表区分接口调用结果与后台任务终态；错误路径、预期限制和缺少外部输入均保留原始记录。',
    f'原先失败后复测通过：{len(resolved)}项。已记录的工具中，至少一次返回成功的有{sum(bool(tools[n]["ok"]) for n in expected_tools)}/{len(expected_tools)}项；后台任务完成情况见分析覆盖表。',
    'HPC读取在本机返回HPC_SETTINGS_UNAVAILABLE，相关5项测试按原生接口条件跳过；另有4项缺少历史数值输入或原生CFG预设，以及2项仓库预期失败。',
    'STAR分析包含Cooke基准镜头的原始测试，以及用原生API预先导入FEA数据的补充镜头。补充镜头用于单独测试MCP拟合、读取、卸载和分析；MCP导入路径检查的原始失败记录保留。',
    'STAR补测：变形及直接折射率的拟合、常量采样与卸载通过；温度数据卸载通过，恒温21°C输入的拟合采样返回0°C；刚体开关/参考点、组件配置和从FEA去除组件刚体通过，添加坐标断点返回SETTING_REJECTED。6类STAR分析在已导入并拟合FEA的镜头上均返回NO_RESULT_DATA，原生IsSTARModuleEnabled为true。',
    '复现与原始证据：.local/full-2026r1/下保存collected-tests.json、test-results.jsonl、native-calls.jsonl、module-results.jsonl、各次pytest日志/XML、summary.json与feature-coverage.csv；光学输入和输出保存在.local/runs/。首轮、补跑和中断记录均保留。',
    '', '## 已定位的产品代码问题', '',
    '- `backend.py:1516`：评价函数目标/权重使用浮点严格相等比较。请求49.99999950000002、原生回读49.9999995，约2e-14差异触发SETTING_REJECTED。',
    '- `star.py:235`：STAR导入要求回读文件名等于输入文本路径。本机导入后回读为Documents/Zemax/OBJECTS/STOP Files/*.zst，触发SETTING_REJECTED。',
    '- `analyses.py:912`起的通用结果收集：受控抛物面镜FFT离焦MTF输出“计算终止; 无效的结果!”且无曲线/网格，任务仍标记succeeded。',
    '原始调用、原生文本和首次失败记录均保留；本次功能试验中的产品源码保持原样。',
    '', '## 当前未通过原因', '', '| 类别 | 用例数 |', '| --- | ---: |']
for group,count in problem_groups.items():lines.append(f'| {group} | {count} |')
lines+=['', '## 工具覆盖', '', '| 工具 | 已记录调用 | 返回成功 | 返回错误 |', '| --- | ---: | ---: | ---: |']
for name in sorted(expected_tools):
    t=tools[name];lines.append(f'| {name} | {t["calls"]} | {t["ok"]} | {t["errors"]} |')
lines+=['','## 分析请求覆盖','','| 请求 | 调用 | 已受理 | 任务终态 |','| --- | ---: | ---: | --- |']
for name in sorted(expected_analysis):
    a=analyses[name];states=dict(collections.Counter(tasks.get(t,'unknown') for t in a['task_ids']))
    lines.append(f'| {name} | {a["calls"]} | {a["accepted"]} | {states} |')
lines+=['','## 原生失败与限制','']
for x in summary['failed_tests']+summary['skipped_tests']:
    lines+=['### '+x['test'],'',f'结果：{x["outcome"]}。','', '```text',str(x['reason'])[:18000],'```','']
lines+=['','## 普通测试失败','']
for x in unit_failures:
    lines+=['### '+x['test'],'','```text',x['reason'][:9000],'```','']
lines+=['','## 复测通过记录','']
for x in resolved:
    lines+=['- '+x['test']+'：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。']
with (OUT/'feature-coverage.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.writer(stream)
    writer.writerow(['category','name','recorded_calls','accepted','errors','task_states'])
    for name in sorted(expected_tools):
        t=tools[name];writer.writerow(['tool',name,t['calls'],t['ok'],t['errors'],''])
    for name in sorted(expected_analysis):
        a=analyses[name];writer.writerow(['analysis',name,a['calls'],a['accepted'],a['calls']-a['accepted'],json.dumps(dict(collections.Counter(tasks.get(t,'unknown') for t in a['task_ids'])))])
(ROOT/'FULL_COMPATIBILITY_2026R1.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('failed_tests','skipped_tests','unit_failures','tools_missing','analyses_missing','resolved_failures')},ensure_ascii=False,indent=2))

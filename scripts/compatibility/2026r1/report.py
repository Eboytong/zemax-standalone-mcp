import argparse
import collections
import csv
from datetime import datetime
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = next(p for p in SCRIPT_DIR.parents if (p/'src/zemax_mcp').is_dir())
sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp import __version__

parser = argparse.ArgumentParser(description='Generate the current compatibility run report.')
parser.add_argument('--out', type=Path, default=(ROOT/'.local'/f'v{__version__}-2026r1'
    if SCRIPT_DIR == ROOT/'scripts/compatibility/2026r1' else SCRIPT_DIR))
OUT = parser.parse_args().out.resolve()
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
native_ids=set(native_tests)
latest={x['test']:x for x in rows if x['test'] in native_ids}
counts=collections.Counter(dict.fromkeys(('passed','failed','skipped'),0))
counts.update(x['outcome'] for x in latest.values())
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
module_count=len({t.split('::')[0] for t in native_tests})
active=json.loads((OUT/'active.json').read_text()) if (OUT/'active.json').exists() else {}
summary=dict(version=__version__,out=str(OUT),updated=datetime.now().astimezone().isoformat(),active=active,native=dict(collected=len(native_tests),completed=len(latest),not_completed=len(native_tests)-len(latest),**counts),problem_groups=dict(problem_groups),
    unit=unit,modules_completed=len({m['module'] for m in modules}),module_runs=len(modules),modules_total=module_count,tools_seen=len(expected_tools & set(tools)),tools_total=len(expected_tools),
    analyses_seen=len(expected_analysis & set(analyses)),analyses_total=len(expected_analysis),
    tools_missing=sorted(expected_tools-set(tools)),analyses_missing=sorted(expected_analysis-set(analyses)),
    failed_tests=[x for x in latest.values() if x['outcome']=='failed'],skipped_tests=[x for x in latest.values() if x['outcome']=='skipped'],
    unit_failures=unit_failures)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
lines=[f'# MCP {__version__} / OpticStudio 2026 R1 全功能试验','',f'更新：{summary["updated"]}',
    '',f'原生测试：收集 {len(native_tests)} 项，已完成 {len(latest)} 项；通过 {counts["passed"]}、失败 {counts["failed"]}、跳过 {counts["skipped"]}。',
    f'已结束模块：{len({m["module"] for m in modules})}/{module_count}。当前状态：'+('全部计划试验已结束。' if active.get('state')=='finished' and len(latest)==len(native_tests) else f'`{active}`。'),
    f'工具调用覆盖：{summary["tools_seen"]}/{len(expected_tools)}；run_analysis 请求覆盖：{summary["analyses_seen"]}/{len(expected_analysis)}。',
    f'普通测试：{unit}。','',
    f'本次运行：MCP {__version__}；Python {sys.version.split()[0]}；运行目录 `{OUT}`。',
    '本次从 collected-tests.json 获取计划用例，以本运行目录中的最新用例记录统计进度和结果；普通测试结果来自 unit.xml。',
    'run.ps1 对仓库测试执行收集和普通测试，随后逐模块以独立进程串行执行原生测试；compat_plugin 显式启用 full 工具模式，以执行历史直接工具测试，模式专项测试使用各自设置。',
    '原生测试安装目录由启动脚本及插件设置为 v261；当前活动模块见上述状态，已结束模块、失败、跳过和覆盖均随本次记录更新。',
    '覆盖表区分接口调用结果与后台任务终态；错误路径、跳过原因和缺少外部输入均保留原始记录。',
    f'原始证据：`{OUT}` 下的 collected-tests.json、test-results.jsonl、native-calls.jsonl、module-results.jsonl、pytest 日志/XML、summary.json 与 feature-coverage.csv。',
    '', '## 本次版本包含的三项修复', '',
    '- `backend.py`：评价函数目标与权重回读采用 rel_tol=1e-12、abs_tol=1e-12 的浮点容差比较，接受原生浮点回读舍入差异。',
    '- `star.py`：STAR 导入确认非空数据集后，接受实际存在的绝对路径 ZST 容器作为原生回读结果。',
    '- `analyses.py`：离焦 MTF 收集检查原生计算错误、无效结果及曲线数据，失败时返回结果错误。',
    '修复的本机执行结果见本次用例记录与下方失败/跳过列表；运行进度由本次采集数据给出。',
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
with (OUT/'feature-coverage.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.writer(stream)
    writer.writerow(['category','name','recorded_calls','accepted','errors','task_states'])
    for name in sorted(expected_tools):
        t=tools[name];writer.writerow(['tool',name,t['calls'],t['ok'],t['errors'],''])
    for name in sorted(expected_analysis):
        a=analyses[name];writer.writerow(['analysis',name,a['calls'],a['accepted'],a['calls']-a['accepted'],json.dumps(dict(collections.Counter(tasks.get(t,'unknown') for t in a['task_ids'])))])
(OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('failed_tests','skipped_tests','unit_failures','tools_missing','analyses_missing')},ensure_ascii=False,indent=2))

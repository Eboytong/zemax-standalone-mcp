"""Summarize the development ledgers and retain item-level remaining actions."""
import argparse
from collections import Counter
import csv
from datetime import date
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_ledger(name):
    with (ROOT / 'development/ledgers' / dict(zip(['development-tasks.csv','development-items.csv','development-backlog.csv'],['packages.csv','operations.csv','analyses.csv']))[name]).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def summarize():
    packages = read_ledger('development-tasks.csv')
    operations = read_ledger('development-items.csv')
    analyses = read_ledger('development-backlog.csv')
    groups = {}
    for key, rows in [('packages',packages),('operations',operations),('analyses',analyses)]:
        groups[key] = dict(total=len(rows),states=dict(Counter(r['execution_state'] for r in rows)))
    gates = []
    historical = []
    for source, rows in [('development-items.csv',operations),('development-backlog.csv',analyses)]:
        for row in rows:
            state = row['execution_state']
            if state == 'done':
                continue
            item = dict(source=source,item_id=row['item_id'],work_package=row['work_package'],
                        state=state,reason=row.get('blocked_reason',''),next_action=row.get('next_action',''),
                        evidence=[e.strip() for e in row.get('evidence','').split(';') if e.strip()])
            (historical if state in ('baseline','documented') else gates).append(item)
    unique_ids = sorted({item["item_id"] for item in gates})
    duplicate_ids = sorted(item_id for item_id, count in Counter(item["item_id"] for item in gates).items() if count > 1)
    package_rows = []
    for row in packages:
        if row['execution_state'] == 'done':
            continue
        package_rows.append(dict(task_id=row['task_id'],state=row['execution_state'],
            operation_states=dict(Counter(r['execution_state'] for r in operations if r['work_package']==row['task_id'])),
            analysis_states=dict(Counter(r['execution_state'] for r in analyses if r['work_package']==row['task_id'])),
            next_action=row['next_action'],blocked_reason=row['blocked_reason']))
    version=tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    release = None
    for path in sorted((ROOT / "verification/development/BASE-04").glob("release*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("version") == version:
            release = dict(source=path.relative_to(ROOT).as_posix(), **data)
    alias_path = ROOT / 'docs/development-functional-groups.json'
    aliases = {}
    if alias_path.exists():
        for group in json.loads(alias_path.read_text(encoding='utf-8-sig'))['groups']:
            for alias in group['aliases']:
                aliases[alias] = group['canonical_item_id']
    canonical_ids = sorted({aliases.get(item_id, item_id) for item_id in unique_ids})
    for item in gates:
        item['canonical_item_id']=aliases.get(item['item_id'],item['item_id'])
    batch_path = ROOT / 'docs/development-batches.json'
    batch = json.loads(batch_path.read_text(encoding='utf-8-sig')) if batch_path.exists() else None
    source_capabilities = None
    if (ROOT / 'src/zemax_mcp/models.py').exists():
        from zemax_mcp.models import COMMAND_MODELS
        source_capabilities = dict(tools=len(COMMAND_MODELS), analyses=len(COMMAND_MODELS['run_analysis'].model_json_schema()['properties']['request']['discriminator']['mapping']))
    return dict(version=version,date=date.today().isoformat(),ledgers=groups,
                canonical_remaining_count=len(canonical_ids),canonical_remaining_ids=canonical_ids,
                current_batch=batch,source_capabilities=source_capabilities,remaining_gate_count=len(gates),remaining_gates=gates,
                unique_remaining_item_count=len(unique_ids), duplicate_remaining_item_ids=duplicate_ids, release=release,
                historical_scope_count=len(historical),historical_scope=historical,remaining_packages=package_rows)


def markdown(report):
    lines=['# 未完成项汇总','',
        f"代码基线 {report['version']}；汇总日期 {report['date']}。按三份执行台账生成，逐项证据和后续动作保留在 JSON 报告中。",'',
        '| 台账 | 总数 | 状态 |','| --- | ---: | --- |']
    for key,label in [('packages','工作包'),('operations','操作条目'),('analyses','分析条目')]:
        row=report['ledgers'][key]
        lines.append(f"| {label} | {row['total']} | "+' / '.join(f'{s} {n}' for s,n in row['states'].items())+' |')
    lines += ['',f"待处理源记录 {report['remaining_gate_count']} 项；历史 baseline/documented 范围 {report['historical_scope_count']} 项另列。",'',
        '| 未完成工作包 | 工作包状态 | 操作条目 | 分析条目 |','| --- | --- | --- | --- |']
    for row in report['remaining_packages']:
        def counts(values):return ' / '.join(f'{s} {n}' for s,n in values.items()) or '—'
        lines.append(f"| {row['task_id']} | {row['state']} | {counts(row['operation_states'])} | {counts(row['analysis_states'])} |")
    lines += ['',f"按相同 item_id 去重后为 {report['unique_remaining_item_count']} 项；跨清单同名条目同步更新状态和证据。",'', '当前执行动作：','']
    for row in report['remaining_packages']:
        lines.append(f"- {row['task_id']}：{row['next_action']}")
        if row['blocked_reason']:
            lines.append(f"  当前缺口：{row['blocked_reason']}")
    lines += ['', f"共同功能去重后为 {report['canonical_remaining_count']} 组。"]
    if report.get('source_capabilities'):
        c = report['source_capabilities']
        lines += ['', f"源码能力：{c['tools']} 工具、{c['analyses']} 种分析；发行能力见对应发行记录。"]
    if report.get('current_batch'):
        b = report['current_batch']
        lines += ['', f"当前批次 {b['batch_id']}：{len(b['completed_item_ids'])}/{b['target']}；下一条：{b['current_item']}"]
    release=report.get('release')
    lines += ['', '最近发行证据：','']
    if release:
        lines.append(f"当前版本发行记录：{release['source']}。")
        for key,label in [('ordinary_passed','普通检查通过'),('native_wheel_passed','独立安装包原生检查通过')]:
            if key in release:
                lines.append(f"- {label}：{release[key]} 项。")
        lines += ['', '以上检查数量属于对应发行记录；本轮新增执行另存证据，历史执行与当前执行分别记录。']
    else:
        lines.append('尚无与当前版本对应的发行记录；逐项执行证据见台账。')
    lines += ['', '历史 baseline/documented 沿用各自记录范围。条目完成需要实际设置、可用结果、相关数值或输出检查、关闭及文档证据。','']
    return '\n'.join(lines)


def queue_snapshot(report, previous=None):
    """Refresh derived queue membership and actions while retaining phase labels."""
    previous=previous or {}
    old={r['canonical_item_id']:r for r in previous.get('items',[])}
    batch=report.get('current_batch') or {}
    order={key:i+1 for i,key in enumerate(batch.get('candidate_item_ids',[]))}
    grouped={}
    for record in report['remaining_gates']:
        canonical=record['canonical_item_id']
        item=grouped.setdefault(canonical,dict(canonical_item_id=canonical,
            phase=old.get(canonical,{}).get('phase','D8' if record['work_package'].startswith('EXT-') else 'unassigned'),
            batch_role='candidate' if canonical in order else 'later',
            batch_order=order.get(canonical),source_records=[]))
        item['source_records'].append(dict(ledger='docs/'+record['source'],item_id=record['item_id'],
            execution_state=record['state'],next_action=record['next_action'],
            evidence=';'.join(record['evidence']),blocked_reason=record['reason']))
    rows=sorted(grouped.values(),key=lambda row:(row['batch_order'] or 100000,row['phase'],row['canonical_item_id']))
    release=report.get('release') or {}
    result=dict(previous)
    result.update(planned_on=report['date'],plan='docs/next-development-plan.md',
        released_baseline=release.get('version'),candidate_release=batch.get('next_release'),
        current_gate=f"{batch.get('batch_id')}: {len(batch.get('completed_item_ids',[]))}/{batch.get('target')}; {batch.get('current_item','')}",
        source_record_count=report['remaining_gate_count'],unique_item_id_count=report['unique_remaining_item_count'],
        canonical_group_count=report['canonical_remaining_count'],phases=previous.get('phases',{}),
        phase_counts=dict(Counter(row['phase'] for row in rows)),
        execution_rules=previous.get('execution_rules',[]),items=rows)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--markdown',type=Path)
    parser.add_argument('--queue',type=Path,help='Refresh the derived queue, preserving its existing phase labels.')
    args=parser.parse_args()
    report=summarize()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.markdown:
        args.markdown.parent.mkdir(parents=True,exist_ok=True)
        args.markdown.write_text(markdown(report),encoding='utf-8')
    if args.queue:
        previous=json.loads(args.queue.read_text(encoding='utf-8-sig')) if args.queue.exists() else None
        args.queue.parent.mkdir(parents=True,exist_ok=True)
        args.queue.write_text(json.dumps(queue_snapshot(report,previous),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(ledgers=report['ledgers'],remaining_gate_count=report['remaining_gate_count'],historical_scope_count=report['historical_scope_count']),ensure_ascii=False))

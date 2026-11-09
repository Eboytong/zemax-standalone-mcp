"""Summarize the development ledgers and retain item-level remaining actions."""
import argparse
from collections import Counter
import csv
from datetime import date
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def read_ledger(name):
    path = ROOT / 'development/ledgers' / {'development-tasks.csv':'packages.csv','development-items.csv':'operations.csv','development-backlog.csv':'analyses.csv'}[name]
    allowed = {'pending', 'in_progress', 'implemented', 'done', 'blocked'}
    if name == 'development-backlog.csv':
        allowed |= {'baseline', 'documented'}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        try:
            header = next(reader)
            if 'execution_state' not in header or len(set(header)) != len(header):
                raise ValueError(f'{path}:1: missing execution_state or duplicate columns')
            rows = []
            for values in reader:
                if len(values) != len(header):
                    raise ValueError(f'{path}:{reader.line_num}: expected {len(header)} columns, got {len(values)}')
                row = dict(zip(header, values))
                if row['execution_state'] not in allowed:
                    raise ValueError(f"{path}:{reader.line_num}: unknown execution_state {row['execution_state']!r}")
                rows.append(row)
            return rows
        except StopIteration:
            raise ValueError(f'{path}:1: empty ledger') from None
        except csv.Error as exc:
            raise ValueError(f'{path}:{reader.line_num}: {exc}') from exc


def development_group_snapshot(gates, records, aliases, scope):
    path = ROOT / 'development/tracking/development-groups.json'
    if not path.exists():
        return None
    plan = json.loads(path.read_text(encoding='utf-8-sig'))
    groups = []
    membership = {}
    records_by_id = {}
    for record in records:
        canonical = aliases.get(record['item_id'], record['item_id'])
        records_by_id.setdefault(canonical, []).append(record)
    remaining = {record['canonical_item_id'] for record in gates}
    excluded = {aliases.get(key, key) for key in (scope or {}).get('excluded_item_ids', [])}
    for group_order, definition in enumerate(plan['groups'], 1):
        group_id = definition['group_id']
        if group_id != f'D{group_order:03d}':
            raise ValueError(f'{path}: expected D{group_order:03d}, got {group_id!r}')
        items = []
        for item_order, definition_item in enumerate(definition['items'], 1):
            item = dict(definition_item)
            canonical = aliases.get(item['canonical_item_id'], item['canonical_item_id'])
            if canonical in membership:
                raise ValueError(f'{path}: duplicate canonical item {canonical!r}')
            item.update(canonical_item_id=canonical, development_group=group_id,
                        group_order=group_order, item_order=item_order)
            membership[canonical] = item
            items.append(item)
        ids = [item['canonical_item_id'] for item in items]
        completed = [key for key in ids if records_by_id.get(key)
                     and all(row['execution_state'] == 'done' for row in records_by_id[key])]
        groups.append(dict(definition, group_order=group_order, items=items,
            target_count=len(ids), remaining_count=sum(key in remaining for key in ids),
            completed_count=len(completed), completed_item_ids=completed,
            outside_scope_item_ids=[key for key in ids if key in excluded],
            untracked_item_ids=[key for key in ids if key not in records_by_id and key not in excluded]))
    for record in gates:
        member = membership.get(record['canonical_item_id'])
        if member:
            record.update({key: member[key] for key in ('development_group', 'group_order', 'item_order')})
    return dict(source=path.relative_to(ROOT).as_posix(), effective_date=plan['effective_date'],
        execution_policy=plan['execution_policy'], groups=groups,
        planned_function_count=len(membership),
        current_group=next((group['group_id'] for group in groups if group['remaining_count']), None),
        unassigned_remaining_ids=sorted(remaining - membership.keys()))


def summarize():
    packages = read_ledger('development-tasks.csv')
    operations = read_ledger('development-items.csv')
    analyses = read_ledger('development-backlog.csv')
    scope_path = ROOT / 'development/tracking/scope.json'
    scope = json.loads(scope_path.read_text(encoding='utf-8-sig')) if scope_path.exists() else None
    if scope:
        excluded_items = set(scope['excluded_item_ids'])
        excluded_packages = set(scope['excluded_package_ids'])
        packages = [r for r in packages if r['task_id'] not in excluded_packages]
        operations = [r for r in operations if r['item_id'] not in excluded_items]
        analyses = [r for r in analyses if r['item_id'] not in excluded_items]
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
    for path in sorted((ROOT / "development/evidence/BASE-04").glob("release*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("version") == version:
            recorded_action = data.pop('next_action', None)
            release = dict(source=path.relative_to(ROOT).as_posix(), **data)
            if recorded_action is not None:
                release['historical_next_action'] = recorded_action
    alias_path = ROOT / 'development/tracking/functional-groups.json'
    aliases = {}
    if alias_path.exists():
        for group in json.loads(alias_path.read_text(encoding='utf-8-sig'))['groups']:
            for alias in group['aliases']:
                aliases[alias] = group['canonical_item_id']
    canonical_ids = sorted({aliases.get(item_id, item_id) for item_id in unique_ids})
    for item in gates:
        item['canonical_item_id']=aliases.get(item['item_id'],item['item_id'])
    source_capabilities = None
    if (ROOT / 'src/zemax_mcp/models.py').exists():
        from zemax_mcp.models import COMMAND_MODELS
        source_capabilities = dict(tools=len(COMMAND_MODELS), analyses=len(COMMAND_MODELS['run_analysis'].model_json_schema()['properties']['request']['discriminator']['mapping']))
    development_groups = development_group_snapshot(gates, operations + analyses, aliases, scope)
    freeze_path = ROOT / 'development/tracking/native-freeze.json'
    native_freeze = None
    if freeze_path.exists():
        native_freeze = json.loads(freeze_path.read_text(encoding='utf-8-sig'))
        if not isinstance(native_freeze.get('active'), bool):
            raise ValueError(f'{freeze_path}: active must be boolean')
        if native_freeze.get('scope') != 'all_remaining_native_functions':
            raise ValueError(f'{freeze_path}: unsupported freeze scope')
        active = native_freeze['active']
        native_freeze.update(source=freeze_path.relative_to(ROOT).as_posix(),
            affected_canonical_item_ids=canonical_ids if active else [],
            affected_function_count=len(canonical_ids) if active else 0,
            affected_source_record_count=len(gates) if active else 0)
        if development_groups and active:
            development_groups['resume_priority_group'] = development_groups['current_group']
            development_groups['current_group'] = None
    cycle_path = ROOT / 'development/tracking/verification-cycle.json'
    verification = None
    if cycle_path.exists():
        verification = json.loads(cycle_path.read_text(encoding='utf-8-sig'))
        completed = [key for group in (development_groups or {}).get('groups', [])
                     for key in group['completed_item_ids']]
        verified = set(verification.get('last_verified_item_ids', []))
        recent = [key for key in completed if key not in verified]
        interval = verification['interval']
        if not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
            raise ValueError(f'{cycle_path}: interval must be a positive integer')
        verification.update(completed_since_check_item_ids=recent,
            completed_since_check_count=len(recent),
            remaining_until_check=max(0, interval - len(recent)), due=len(recent) >= interval)
    return dict(version=version,date=date.today().isoformat(),ledgers=groups,development_scope=scope,
                development_groups=development_groups,native_freeze=native_freeze,
                canonical_remaining_count=len(canonical_ids),canonical_remaining_ids=canonical_ids,
                verification_cycle=verification,source_capabilities=source_capabilities,remaining_gate_count=len(gates),remaining_gates=gates,
                unique_remaining_item_count=len(unique_ids), duplicate_remaining_item_ids=duplicate_ids, release=release,
                historical_scope_count=len(historical),historical_scope=historical,remaining_packages=package_rows)


def markdown(report):
    lines=['# 未完成项汇总','',
        f"代码基线 {report['version']}；汇总日期 {report['date']}。按三份执行台账生成，逐项证据和后续动作保留在 JSON 报告中。",'',
        '| 台账 | 总数 | 状态 |','| --- | ---: | --- |']
    if report.get('development_scope'):
        lines[3:3] = ['当前计划范围：OpticStudio内建功能、官方STAR及HPC。范围定义见tracking/scope.json；移出条目的原始状态和证据保存在开发归档。', '']
    for key,label in [('packages','工作包'),('operations','操作条目'),('analyses','分析条目')]:
        row=report['ledgers'][key]
        lines.append(f"| {label} | {row['total']} | "+' / '.join(f'{s} {n}' for s,n in row['states'].items())+' |')
    lines += ['',f"待处理源记录 {report['remaining_gate_count']} 项；历史 baseline/documented 范围 {report['historical_scope_count']} 项另列。",'',
        '| 未完成工作包 | 工作包状态 | 操作条目 | 分析条目 |','| --- | --- | --- | --- |']
    for row in report['remaining_packages']:
        def counts(values):return ' / '.join(f'{s} {n}' for s,n in values.items()) or '—'
        lines.append(f"| {row['task_id']} | {row['state']} | {counts(row['operation_states'])} | {counts(row['analysis_states'])} |")
    frozen = (report.get('native_freeze') or {}).get('active', False)
    if frozen:
        lines += ['', f"原生开发与验收排期冻结：{report['canonical_remaining_count']}组共同功能。实际实现状态和证据沿用台账，解冻条件见[当前计划](../current.md)及[冻结记录](../tracking/native-freeze.json)。"]
    lines += ['',f"按相同 item_id 去重后为 {report['unique_remaining_item_count']} 项；跨清单同名条目同步更新状态和证据。",'', '解冻后的保留动作：' if frozen else '当前执行动作：','']
    for row in report['remaining_packages']:
        lines.append(f"- {row['task_id']}：{row['next_action']}")
        if row['blocked_reason']:
            lines.append(f"  当前缺口：{row['blocked_reason']}")
    lines += ['', f"共同功能去重后为 {report['canonical_remaining_count']} 组。"]
    if report.get('source_capabilities'):
        c = report['source_capabilities']
        lines += ['', f"源码能力：{c['tools']} 工具、{c['analyses']} 种分析；发行能力见对应发行记录。"]
    if report.get('verification_cycle'):
        cycle = report['verification_cycle']
        lines += ['', f"集中检查：每完成{cycle['interval']}组共同功能执行一次；距下次检查还需{cycle['remaining_until_check']}项。"]
    if report.get('development_groups'):
        plan = report['development_groups']
        lines += ['', '开发与进度按D00x及组内条目统计；独立任务的并行准备见[并行安排](../parallel-development.md)。每十项集中检查的节奏单独记录。', '',
            '| 开发组 | 关联功能 | 初始项数 | 已完成 | 剩余 |', '| --- | --- | ---: | ---: | ---: |']
        for group in plan['groups']:
            lines.append(f"| {group['group_id']} | {group['name']} | {group['target_count']} | {group['completed_count']} | {group['remaining_count']} |")
        current = '原生排期冻结' if frozen else plan['current_group']
        lines += ['', f"当前开发组：{current}；逐项顺序和动作见[remaining-ranked.md](../remaining-ranked.md)。"]
        if plan['unassigned_remaining_ids']:
            lines += ['', '待分配开发组：' + ', '.join(plan['unassigned_remaining_ids'])]
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
    """Derive D00x order from the plan; old snapshots cannot override it."""
    cycle=report.get('verification_cycle') or {}
    plan=report.get('development_groups') or {}
    frozen=(report.get('native_freeze') or {}).get('active', False)
    members={item['canonical_item_id']:item for group in plan.get('groups',[]) for item in group['items']}
    grouped={}
    for record in report['remaining_gates']:
        canonical=record['canonical_item_id']
        member=members.get(canonical,{})
        item=grouped.setdefault(canonical,dict(canonical_item_id=canonical,
            development_group=member.get('development_group', 'unassigned'),
            group_order=member.get('group_order'), item_order=member.get('item_order'),
            title=member.get('title', canonical), difficulty=member.get('difficulty'),
            depends_on_item_ids=member.get('depends_on_item_ids', []),
            native_scheduling_state='frozen' if frozen else 'planned',
            source_records=[]))
        item['source_records'].append(dict(ledger='development/ledgers/'+{'development-tasks.csv':'packages.csv','development-items.csv':'operations.csv','development-backlog.csv':'analyses.csv'}[record['source']],item_id=record['item_id'],
            execution_state=record['state'],next_action=record['next_action'],
            evidence=';'.join(record['evidence']),blocked_reason=record['reason']))
    rows=sorted(grouped.values(),key=lambda row:(row['group_order'] or 100000,row['item_order'] or 100000,row['canonical_item_id']))
    release=report.get('release') or {}
    result=dict(planned_on=report['date'],plan='development/current.md',
        grouping_source=plan.get('source'),
        development_scope=report.get('development_scope'),
        released_baseline=release.get('version'),candidate_release=cycle.get('next_release'),
        verification_cycle=report.get('verification_cycle'),
        native_freeze=report.get('native_freeze'),
        source_record_count=report['remaining_gate_count'],unique_item_id_count=report['unique_remaining_item_count'],
        canonical_group_count=report['canonical_remaining_count'],
        current_development_group=plan.get('current_group'),
        resume_priority_group=plan.get('resume_priority_group'),
        development_groups=[dict(group_id=group['group_id'],name=group['name'],
            target_count=group['target_count'],remaining_count=group['remaining_count'],
            completed_count=group['completed_count']) for group in plan.get('groups',[])],
        group_counts=dict(Counter(row['development_group'] for row in rows)),
        unassigned_remaining_ids=plan.get('unassigned_remaining_ids',sorted(grouped)),
        execution_rules=plan.get('execution_policy', []),items=rows)
    return result


def ranked_markdown(report):
    """Render the remaining actions in maintained D00x group and member order."""
    queue = queue_snapshot(report)
    plan = report.get('development_groups') or {}
    frozen = (report.get('native_freeze') or {}).get('active', False)
    current = '原生排期冻结' if frozen else plan.get('current_group') or '已全部完成'
    labels = dict(pending='待开发', in_progress='进行中', implemented='已实现待验收',
                  blocked='受阻', done='已完成')
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', '<br>')
    lines = ['# D00x开发顺序与剩余工作', '',
        f"更新{report['date']}。当前{report['remaining_gate_count']}条待处理源记录、{report['unique_remaining_item_count']}个不同编号、{report['canonical_remaining_count']}组共同功能；源码/发行{report['version']}。当前开发组：{current}。", '',
        '以D001→D013及组内编号作为调度优先级；独立任务的并行准备见[并行安排](parallel-development.md)，原难度作为估计信息保留。归属和顺序由[development-groups.json](tracking/development-groups.json)维护，实际状态、动作和证据来自三份台账。每十项集中检查见[verification-cycle.json](tracking/verification-cycle.json)。多个来源状态并列显示，原始逐行记录见[queue.json](generated/queue.json)。', '',
        '每项先说明实施计划，依[长期规范第7节](plan.md#7-完成状态与证据)交付证据。依赖或许可受阻时记录具体条件，顺序处理下一可执行条目；条件变化后回到最早可执行项。实施说明见[当前计划](current.md)，运行前置问题见[交接](handoff.md)。', '',
        '| 开发组 | 功能类别 | 初始项数 | 已完成 | 剩余 |', '| --- | --- | ---: | ---: | ---: |']
    if frozen:
        lines[4:4] = ['**原生开发与验收排期冻结。** 下表保留实际实现状态及解冻后的动作。冻结范围、可独立开展的离线工作和解冻条件见[当前计划](current.md)与[冻结记录](tracking/native-freeze.json)。', '']
    for group in plan.get('groups', []):
        lines.append(f"| [{group['group_id']}](#{group['group_id'].lower()}) | {group['name']} | {group['target_count']} | {group['completed_count']} | {group['remaining_count']} |")
    if plan:
        groups = plan['groups']
        lines.append(f"| 合计 | {len(groups)}个开发组 | {sum(group['target_count'] for group in groups)} | {sum(group['completed_count'] for group in groups)} | {sum(group['remaining_count'] for group in groups)} |")
    for group in plan.get('groups', []) + [dict(group_id='unassigned',name='待分组',objective='登记新增条目的关联归属后执行。')]:
        rows = [row for row in queue['items'] if row['development_group'] == group['group_id']]
        if not rows:
            continue
        lines += ['', f"## {group['group_id']}", '', group['name'] + '。' + group['objective'], '',
            '| 组内顺序 | 功能及编号 | 难度 | 实现状态 | 原生排期 | 剩余工作与完成条件 |', '| ---: | --- | --- | --- | --- | --- |']
        for row in rows:
            records = row['source_records']
            states = ' / '.join(dict.fromkeys(labels.get(record['execution_state'], record['execution_state']) for record in records))
            actions = list(dict.fromkeys(record['next_action'] for record in records if record['next_action']))
            reasons = list(dict.fromkeys(record['blocked_reason'] for record in records if record['blocked_reason']))
            details = '；'.join(actions)
            for reason in reasons:
                if reason not in details:
                    details += ' 条件：' + reason
            if row['depends_on_item_ids']:
                details += ' 前置：' + '、'.join(row['depends_on_item_ids']) + '。'
            scheduling = '冻结' if row['native_scheduling_state'] == 'frozen' else '按前置条件排期'
            lines.append(f"| {row['item_order'] or '—'} | {cell(row['title'])}（`{row['canonical_item_id']}`） | {cell(row['difficulty'] or '待评估')} | {states} | {scheduling} | {cell(details)} |")
    lines += ['', '## 工作包收口', '',
        f"另有{len(report['remaining_packages'])}个未完成工作包汇总；随相关D00x子项完成后核对，采用原有证据要求和状态。", '',
        '| 工作包 | 状态 | 当前原生范围与收口动作 |', '| --- | --- | --- |']
    for row in report['remaining_packages']:
        details = row['next_action']
        if row['blocked_reason'] and row['blocked_reason'] not in details:
            details += ' 条件：' + row['blocked_reason']
        lines.append(f"| `{row['task_id']}` | {labels[row['state']]} | {cell(details)} |")
    lines += ['', '来源：[操作台账](ledgers/operations.csv)、[分析台账](ledgers/analyses.csv)、[工作包台账](ledgers/packages.csv)。原生归属见[产品能力分类](remaining-origin-classification.md)，范围变更见[历史索引](archive/scope-native-only-20261108/index.json)。', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--markdown',type=Path)
    parser.add_argument('--queue',type=Path,help='Generate the queue in D00x plan order.')
    parser.add_argument('--ranked',type=Path,help='Generate the grouped remaining-work table.')
    args=parser.parse_args()
    report=summarize()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.markdown:
        args.markdown.parent.mkdir(parents=True,exist_ok=True)
        args.markdown.write_text(markdown(report),encoding='utf-8')
    if args.queue:
        args.queue.parent.mkdir(parents=True,exist_ok=True)
        args.queue.write_text(json.dumps(queue_snapshot(report),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.ranked:
        args.ranked.parent.mkdir(parents=True,exist_ok=True)
        args.ranked.write_text(ranked_markdown(report),encoding='utf-8')
    print(json.dumps(dict(ledgers=report['ledgers'],remaining_gate_count=report['remaining_gate_count'],historical_scope_count=report['historical_scope_count']),ensure_ascii=False))

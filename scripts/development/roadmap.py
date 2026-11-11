"""Read the current development roadmap and render its queue and status views."""
import csv
from collections import Counter
from datetime import date
import json
from pathlib import Path


def summarize(root: Path):
    config = json.loads((root / 'development/tracking/roadmap.json').read_text(encoding='utf-8'))
    with (root / config['ledger']).open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    by_id = {row['item_id']: row for row in rows}
    order = config['execution_order']
    if len(by_id) != len(rows) or set(by_id) != set(order) or len(order) != len(rows):
        raise ValueError('Roadmap ledger and execution_order must contain the same unique item IDs.')
    states = {'pending', 'in_progress', 'implemented', 'done', 'blocked'}
    schedules = {'active', 'conditional', 'future'}
    items = []
    for item_id in order:
        row = dict(by_id[item_id])
        if row['execution_state'] not in states or row['schedule'] not in schedules:
            raise ValueError(f'{item_id}: unknown state or schedule')
        dependencies = [part for part in row['depends_on'].split(';') if part]
        if any(part not in by_id for part in dependencies) or item_id in dependencies:
            raise ValueError(f'{item_id}: unknown or self dependency')
        pending_dependencies = [part for part in dependencies if by_id[part]['execution_state'] != 'done']
        row.update(depends_on_item_ids=dependencies, pending_dependencies=pending_dependencies,
                   ready=row['schedule'] == 'active' and row['execution_state'] not in {'done', 'blocked'}
                   and not pending_dependencies)
        items.append(row)
    completed = [row['item_id'] for row in items if row['execution_state'] == 'done']
    verified = set(config['verification']['last_verified_item_ids'])
    since_check = [key for key in completed if key not in verified]
    interval = config['verification']['interval']
    counts = {schedule: dict(total=sum(row['schedule'] == schedule for row in items),
                            completed=sum(row['schedule'] == schedule and row['execution_state'] == 'done'
                                          for row in items)) for schedule in sorted(schedules)}
    next_item = next((row['item_id'] for row in items if row['ready']), None)
    return dict(schema_version=1, plan_id=config['plan_id'], date=date.today().isoformat(),
                baseline_release=config['baseline_release'], target_release=config['target_release'],
                ledger=config['ledger'], planned_count=len(items), completed_count=len(completed),
                remaining_count=len(items) - len(completed), completed_item_ids=completed,
                next_item=next_item, schedule_counts=counts,
                state_counts=dict(Counter(row['execution_state'] for row in items)),
                verification=dict(interval=interval, completed_since_check_item_ids=since_check,
                                  completed_since_check_count=len(since_check),
                                  remaining_until_check=max(0, interval-len(since_check)),
                                  due=len(since_check) >= interval,
                                  tail_check_at_stage_close=config['verification']['tail_check_at_stage_close']),
                items=items)


def queue_snapshot(report):
    return {key: value for key, value in report.items() if key != 'items'} | {
        'items': [row for row in report['items'] if row['execution_state'] != 'done']}


def markdown(report, generated=False):
    prefix = '../' if generated else ''
    state_labels = dict(pending='待执行', in_progress='进行中', implemented='已实现待验收',
                        done='已完成', blocked='受阻')
    schedule_labels = dict(active='主队列', conditional='条件任务', future='后续算法专题')
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', '<br>')
    lines = ['# 开发工作表', '',
             f"更新：{report['date']}。计划：`{report['plan_id']}`；产品基线{report['baseline_release']}，目标{report['target_release']}。", '',
             f"共{report['planned_count']}项，已完成{report['completed_count']}项，剩余{report['remaining_count']}项；下一项：{report['next_item'] or ('全部交付完成' if not report['remaining_count'] else '等待依赖或外部条件')}。", '',
             f"状态源：[专题台账]({prefix}ledgers/roadmap.csv)；任务书：[开发计划]({prefix}plan.md)。每项先发布实施方案，按编号选择依赖满足的主队列任务。", '',
             '| 类别 | 总数 | 已完成 | 剩余 |', '| --- | ---: | ---: | ---: |']
    for schedule in ('active', 'conditional', 'future'):
        count = report['schedule_counts'][schedule]
        lines.append(f"| {schedule_labels[schedule]} | {count['total']} | {count['completed']} | {count['total']-count['completed']} |")
    for schedule in ('active', 'conditional', 'future'):
        if report['schedule_counts'][schedule]['total'] == 0:
            continue
        lines += ['', f'## {schedule_labels[schedule]}', '',
                  '| 编号 | 工作 | 难度 | 状态 | 前置 | 下一动作及条件 |',
                  '| --- | --- | --- | --- | --- | --- |']
        for row in report['items']:
            if row['schedule'] != schedule:
                continue
            details = row['next_action']
            if row['blocked_reason']:
                details += '；条件：' + row['blocked_reason']
            lines.append(f"| {row['item_id']} | {cell(row['title'])} | {row['difficulty']} | {state_labels[row['execution_state']]} | {'、'.join(row['depends_on_item_ids']) or '—'} | {cell(details)} |")
    cycle = report['verification']
    lines += ['', '## 检查节奏', '',
              (f"本周期首次完成{cycle['completed_since_check_count']}/{cycle['interval']}项；逐项执行定向检查，累计{cycle['interval']}项或阶段收尾时集中检查。" if report['remaining_count'] else '本期集中与尾批检查已完成；后续修改按影响范围执行定向检查。'), '',
              f"具体实施、GitHub参考和证据要求见[计划]({prefix}plan.md)、[源码参考]({prefix}github-references.md)及[交接]({prefix}handoff.md)。", '']
    return '\n'.join(lines)


def write_outputs(report, output, markdown_path=None, queue_path=None, ranked_path=None):
    outputs = [(output, json.dumps(report, ensure_ascii=False, indent=2) + '\n')]
    if markdown_path:
        outputs.append((markdown_path, markdown(report, generated=True)))
    if queue_path:
        outputs.append((queue_path, json.dumps(queue_snapshot(report), ensure_ascii=False, indent=2) + '\n'))
    if ranked_path:
        outputs.append((ranked_path, markdown(report)))
    for path, body in outputs:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')

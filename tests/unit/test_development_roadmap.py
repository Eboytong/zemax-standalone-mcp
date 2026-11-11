"""Current roadmap counts and scheduling are independent of historical product records."""
import csv
import json

from scripts.development import roadmap


def setup_roadmap(root, rows):
    tracking = root / 'development/tracking'
    tracking.mkdir(parents=True)
    ledger = root / 'development/ledgers/roadmap.csv'
    ledger.parent.mkdir(parents=True)
    config = dict(plan_id='test-plan', baseline_release='1.0.0', target_release='1.1.0',
                  ledger='development/ledgers/roadmap.csv', execution_order=[row['item_id'] for row in rows],
                  verification=dict(interval=10, last_verified_item_ids=[], tail_check_at_stage_close=True))
    (tracking / 'roadmap.json').write_text(json.dumps(config), encoding='utf-8')
    fields = list(rows[0])
    with ledger.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def item(key, state='pending', schedule='active', depends=''):
    return dict(item_id=key, title=key, execution_state=state, schedule=schedule,
                depends_on=depends, next_action='next', blocked_reason='', difficulty='中')


def test_queue_skips_blocked_and_dependent_items_and_keeps_future_separate(tmp_path):
    setup_roadmap(tmp_path, [item('D001', 'blocked'), item('D002', depends='D001'),
                             item('D003'), item('D004', schedule='future')])
    report = roadmap.summarize(tmp_path)
    assert report['next_item'] == 'D003'
    assert report['items'][1]['pending_dependencies'] == ['D001']
    assert report['schedule_counts']['active'] == dict(total=3, completed=0)
    assert report['schedule_counts']['future'] == dict(total=1, completed=0)
    assert not report['items'][3]['ready']


def test_completion_releases_dependency_and_counts_each_new_item_once(tmp_path):
    setup_roadmap(tmp_path, [item('D001', 'done'), item('D002', depends='D001')])
    report = roadmap.summarize(tmp_path)
    assert report['next_item'] == 'D002'
    assert report['completed_count'] == 1
    assert report['verification']['completed_since_check_count'] == 1
    assert [row['item_id'] for row in roadmap.queue_snapshot(report)['items']] == ['D002']


def test_verified_items_leave_cycle_count_but_keep_completion(tmp_path):
    setup_roadmap(tmp_path, [item('D001', 'done'), item('D002', 'done')])
    path = tmp_path / 'development/tracking/roadmap.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    config['verification']['last_verified_item_ids'] = ['D001']
    config['verification']['interval'] = 1
    path.write_text(json.dumps(config), encoding='utf-8')
    report = roadmap.summarize(tmp_path)
    assert report['completed_count'] == 2
    assert report['verification']['completed_since_check_item_ids'] == ['D002']
    assert report['verification']['due']


def test_generated_views_use_current_ids_and_context_relative_links(tmp_path):
    setup_roadmap(tmp_path, [item('D001'), item('D002', 'blocked', 'conditional')])
    report = roadmap.summarize(tmp_path)
    generated = tmp_path / 'development/generated'
    ranked = tmp_path / 'development/remaining-ranked.md'
    roadmap.write_outputs(report, generated / 'status.json', generated / 'remaining.md',
                          generated / 'queue.json', ranked)
    assert json.loads((generated / 'queue.json').read_text(encoding='utf-8'))['next_item'] == 'D001'
    assert '(../ledgers/roadmap.csv)' in (generated / 'remaining.md').read_text(encoding='utf-8')
    assert '(ledgers/roadmap.csv)' in ranked.read_text(encoding='utf-8')

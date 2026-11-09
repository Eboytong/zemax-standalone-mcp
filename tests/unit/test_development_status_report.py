"""Evidence summaries must follow the ledgers and the matching release."""
import csv
import json
import pytest
from pathlib import Path
from tests.support import development_status as status


@pytest.mark.parametrize('body,detail', [
    ('item_id,execution_state\nx,done,extra\n', 'expected 2 columns, got 3'),
    ('item_id,execution_state\nx\n', 'expected 2 columns, got 1'),
    ('item_id,execution_state\nx,success\n', 'unknown execution_state'),
    ('item_id,execution_state\nx,baseline\n', 'unknown execution_state'),
    ('item_id,item_id,execution_state\nx,x,done\n', 'duplicate columns'),
    ('item_id\nx\n', 'missing execution_state'),
    ('', 'empty ledger'),
])
def test_ledger_rejects_invalid_rows_with_location(tmp_path, monkeypatch, body, detail):
    path = tmp_path / 'development/ledgers/operations.csv'
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding='utf-8')
    monkeypatch.setattr(status, 'ROOT', tmp_path)
    with pytest.raises(ValueError) as error:
        status.read_ledger('development-items.csv')
    assert str(path) + ':' in str(error.value)
    assert detail in str(error.value)


def test_ledger_retains_quoted_multiline_actions_and_historical_states(tmp_path, monkeypatch):
    path = tmp_path / 'development/ledgers/analyses.csv'
    path.parent.mkdir(parents=True)
    path.write_text('item_id,execution_state,next_action\nx,baseline,"read, then\nexecute"\ny,documented,retained\n', encoding='utf-8', newline='')
    monkeypatch.setattr(status, 'ROOT', tmp_path)
    rows = status.read_ledger('development-backlog.csv')
    assert rows[0]['next_action'] == 'read, then\nexecute'
    assert rows[1]['execution_state'] == 'documented'


def ledger(root, name, rows):
    keys = sorted(set().union(*(row.keys() for row in rows)))
    with (root / 'development/ledgers' / {'development-tasks.csv':'packages.csv','development-items.csv':'operations.csv','development-backlog.csv':'analyses.csv'}[name]).open('w', encoding='utf-8', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader();writer.writerows(rows)


def test_summary_separates_duplicate_gates_and_current_release(tmp_path,monkeypatch):
    (tmp_path/'development/ledgers').mkdir(parents=True)
    (tmp_path/'development/tracking').mkdir()
    (tmp_path/'pyproject.toml').write_text('[project]\nversion="0.2.0"\n',encoding='utf-8')
    package=dict(task_id='CO-01',execution_state='in_progress',next_action='Run controlled case',blocked_reason='')
    ledger(tmp_path,'development-tasks.csv',[package])
    item=dict(item_id='CO-01.same',work_package='CO-01',execution_state='implemented',next_action='Adopt settings',blocked_reason='',evidence='case.json')
    ledger(tmp_path,'development-items.csv',[item])
    ledger(tmp_path,'development-backlog.csv',[item,dict(item,item_id='CO-01.old',execution_state='baseline')])
    releases=tmp_path/'development/evidence/BASE-04';releases.mkdir(parents=True)
    (releases/'release001.json').write_text(json.dumps(dict(version='0.1.0',ordinary_passed=1700)),encoding='utf-8')
    recorded_action = 'B007 0/10; execute the former batch queue.'
    (releases/'release002.json').write_text(json.dumps(dict(version='0.2.0',ordinary_passed=23,native_wheel_passed=4,next_action=recorded_action)),encoding='utf-8')
    monkeypatch.setattr(status,'ROOT',tmp_path)
    report=status.summarize();text=status.markdown(report)
    assert report['remaining_gate_count']==2
    assert report['unique_remaining_item_count']==1
    assert report['duplicate_remaining_item_ids']==['CO-01.same']
    assert report['historical_scope_count']==1
    assert 'next_action' not in report['release']
    assert report['release']['historical_next_action'] == recorded_action
    assert json.loads((releases/'release002.json').read_text(encoding='utf-8'))['next_action'] == recorded_action
    assert '23 项' in text and '4 项' in text
    assert '1700' not in text and 'startup045' not in text
    assert 'Run controlled case' in text
    (releases/'release002.json').unlink()
    report=status.summarize()
    assert report['release'] is None
    assert '尚无与当前版本对应' in status.markdown(report)


def test_canonical_aliases_and_verification_snapshot(tmp_path, monkeypatch):
    (tmp_path/'development/ledgers').mkdir(parents=True)
    (tmp_path/'development/tracking').mkdir()
    (tmp_path/'pyproject.toml').write_text('[project]\nversion="0.1.60"\n', encoding='utf-8')
    ledger(tmp_path, 'development-tasks.csv', [dict(task_id='MA-01', execution_state='in_progress', next_action='Read profile', blocked_reason='')])
    base=dict(work_package='MA-01', execution_state='in_progress', next_action='Read profile', blocked_reason='', evidence='probe.json')
    ledger(tmp_path, 'development-items.csv', [dict(base,item_id='MA-01.GradiumProfile')])
    ledger(tmp_path, 'development-backlog.csv', [dict(base,item_id='CV-02.GradiumProfile')])
    (tmp_path/'development/tracking/functional-groups.json').write_text(json.dumps(dict(groups=[dict(canonical_item_id='MA-01.GradiumProfile', aliases=['CV-02.GradiumProfile'])])), encoding='utf-8')
    write_group_plan(tmp_path, [('D001', ['MA-01.GradiumProfile'])])
    (tmp_path/'development/tracking/verification-cycle.json').write_text(json.dumps(dict(
        interval=10, last_verified_item_ids=[], next_release='0.1.61')), encoding='utf-8')
    monkeypatch.setattr(status,'ROOT',tmp_path)
    r=status.summarize()
    assert r['remaining_gate_count']==2 and r['unique_remaining_item_count']==2
    assert r['canonical_remaining_count']==1 and r['canonical_remaining_ids']==['MA-01.GradiumProfile']
    assert 'current_batch' not in r
    assert r['verification_cycle']['completed_since_check_count'] == 0
    assert '距下次检查还需10项' in status.markdown(r)
    old=dict(phases=dict(D3='Materials'),items=[dict(canonical_item_id='MA-01.GradiumProfile',phase='D3'),
        dict(canonical_item_id='already-done',phase='D1')])
    queue=status.queue_snapshot(r,old)
    assert queue['source_record_count']==2 and queue['canonical_group_count']==1
    assert len(queue['items'])==1
    assert queue['items'][0]['development_group']=='D001' and queue['group_counts']==dict(D001=1)
    assert 'phases' not in queue and 'phase_counts' not in queue
    assert len(queue['items'][0]['source_records'])==2
    assert queue['items'][0]['source_records'][0]['next_action']=='Read profile'
    assert 'batch_candidate_order' not in queue['items'][0]
    assert queue['candidate_release'] == '0.1.61'


def test_scope_excludes_retired_items_without_changing_their_execution_state(tmp_path, monkeypatch):
    (tmp_path/'development/ledgers').mkdir(parents=True)
    (tmp_path/'development/tracking').mkdir()
    (tmp_path/'pyproject.toml').write_text('[project]\nversion="0.1.62"\n', encoding='utf-8')
    ledger(tmp_path, 'development-tasks.csv', [
        dict(task_id='PO-01', execution_state='in_progress', next_action='Compare phase', blocked_reason=''),
        dict(task_id='EX-01', execution_state='blocked', next_action='Load callback', blocked_reason='ABI')])
    native=dict(item_id='PO-01.PhaseAberration', work_package='PO-01', execution_state='in_progress',
                next_action='Compare phase', blocked_reason='', evidence='phase.json')
    retired=dict(native, item_id='EX-01.CCallback', work_package='EX-01', execution_state='blocked')
    ledger(tmp_path, 'development-items.csv', [native, retired])
    ledger(tmp_path, 'development-backlog.csv', [retired])
    scope=dict(id='ansys-native-only', excluded_item_ids=['EX-01.CCallback'], excluded_package_ids=['EX-01'])
    (tmp_path/'development/tracking/scope.json').write_text(json.dumps(scope), encoding='utf-8')
    monkeypatch.setattr(status, 'ROOT', tmp_path)
    report=status.summarize()
    assert report['canonical_remaining_ids']==['PO-01.PhaseAberration']
    assert report['remaining_gate_count']==1
    assert [r['task_id'] for r in report['remaining_packages']]==['PO-01']
    assert report['development_scope']==scope
    assert status.queue_snapshot(report)['development_scope']==scope
    assert status.read_ledger('development-items.csv')[1]['execution_state']=='blocked'
    assert '官方STAR及HPC' in status.markdown(report)


def write_group_plan(root, definitions):
    groups = [dict(group_id=key, name=key + '关联功能', objective='集中处理对应业务。',
                   items=[dict(canonical_item_id=item_id, title=item_id, difficulty='中',
                               depends_on_item_ids=[]) for item_id in ids])
              for key, ids in definitions]
    (root/'development/tracking/development-groups.json').write_text(json.dumps(dict(
        effective_date='2026-11-08', execution_policy=['按D00x与组内顺序执行'], groups=groups)), encoding='utf-8')


def grouped_report(tmp_path, monkeypatch, definitions, extra=None):
    (tmp_path/'development/ledgers').mkdir(parents=True)
    (tmp_path/'development/tracking').mkdir()
    (tmp_path/'pyproject.toml').write_text('[project]\nversion="0.1.62"\n', encoding='utf-8')
    base=dict(work_package='ED-01', execution_state='implemented', next_action='核对实际采用',
              blocked_reason='', evidence='adoption.json')
    items = [dict(base, item_id=key) for _, ids in definitions for key in ids]
    if extra:
        items += [dict(base, **record) for record in extra]
    ledger(tmp_path, 'development-items.csv', items)
    ledger(tmp_path, 'development-backlog.csv', [dict(base, item_id='history', execution_state='baseline')])
    ledger(tmp_path, 'development-tasks.csv', [dict(task_id='ED-01', execution_state='implemented',
           next_action='完成子项后收口', blocked_reason='')])
    write_group_plan(tmp_path, definitions)
    monkeypatch.setattr(status, 'ROOT', tmp_path)
    return status.summarize()


def test_d00x_order_precedes_batch_candidates_and_legacy_phases(tmp_path, monkeypatch):
    report = grouped_report(tmp_path, monkeypatch, [('D001', ['z-first', 'a-second']), ('D002', ['hpc'])])
    report['current_batch'] = dict(batch_id='B007', completed_item_ids=[], target=10,
                                  current_item='z-first', candidate_item_ids=['hpc', 'a-second'])
    old = dict(phases={'D8': '旧排序'}, items=[dict(canonical_item_id='hpc', phase='D1')])
    queue = status.queue_snapshot(report, old)
    assert [row['canonical_item_id'] for row in queue['items']] == ['z-first', 'a-second', 'hpc']
    assert [row['item_order'] for row in queue['items']] == [1, 2, 1]
    assert all('batch_candidate_order' not in row for row in queue['items'])
    assert 'current_gate' not in queue
    assert queue['current_development_group'] == 'D001'
    assert 'phase' not in queue['items'][0] and 'phases' not in queue
    rendered = status.ranked_markdown(report)
    assert rendered.index('`z-first`') < rendered.index('`a-second`') < rendered.index('`hpc`')
    assert '核对实际采用' in rendered and '已实现待验收' in rendered


def test_verification_cycle_counts_d00x_completions_since_last_check(tmp_path, monkeypatch):
    grouped_report(tmp_path, monkeypatch, [('D001', ['prior', 'new']), ('D002', ['pending', 'new-alias'])])
    rows = status.read_ledger('development-items.csv')
    for row in rows:
        if row['item_id'] != 'pending':
            row['execution_state'] = 'done'
    ledger(tmp_path, 'development-items.csv', rows)
    (tmp_path/'development/tracking/verification-cycle.json').write_text(json.dumps(dict(
        interval=2, last_verified_item_ids=['prior'])), encoding='utf-8')
    report = status.summarize()
    cycle = report['verification_cycle']
    assert cycle['completed_since_check_item_ids'] == ['new', 'new-alias']
    assert cycle['completed_since_check_count'] == 2
    assert cycle['remaining_until_check'] == 0 and cycle['due'] is True
    assert report['development_groups']['current_group'] == 'D002'
    assert 'B007' not in status.ranked_markdown(report)


def test_completion_removes_queue_member_without_changing_group_assignment(tmp_path, monkeypatch):
    grouped_report(tmp_path, monkeypatch, [('D001', ['first']), ('D002', ['second'])])
    rows = status.read_ledger('development-items.csv')
    rows[0]['execution_state'] = 'done'
    ledger(tmp_path, 'development-items.csv', rows)
    report = status.summarize()
    plan = report['development_groups']
    assert plan['planned_function_count'] == 2 and plan['current_group'] == 'D002'
    assert plan['groups'][0]['completed_count'] == 1 and plan['groups'][0]['remaining_count'] == 0
    assert plan['groups'][0]['items'][0]['canonical_item_id'] == 'first'
    queue = status.queue_snapshot(report)
    assert [(row['canonical_item_id'], row['development_group']) for row in queue['items']] == [('second', 'D002')]


def test_unassigned_function_is_visible_and_scope_exclusions_are_not_completions(tmp_path, monkeypatch):
    grouped_report(tmp_path, monkeypatch, [('D001', ['kept']), ('D002', ['removed'])],
                   extra=[dict(item_id='new-native-item')])
    scope = dict(excluded_item_ids=['removed'], excluded_package_ids=[])
    (tmp_path/'development/tracking/scope.json').write_text(json.dumps(scope), encoding='utf-8')
    report = status.summarize()
    plan = report['development_groups']
    assert plan['unassigned_remaining_ids'] == ['new-native-item']
    assert plan['groups'][1]['outside_scope_item_ids'] == ['removed']
    assert plan['groups'][1]['completed_count'] == 0
    queue = status.queue_snapshot(report)
    assert queue['development_scope'] == scope
    assert [row['canonical_item_id'] for row in queue['items']] == ['kept', 'new-native-item']
    assert queue['items'][-1]['development_group'] == 'unassigned'
    assert 'new-native-item' in status.ranked_markdown(report)


@pytest.mark.parametrize('definitions,detail', [
    ([('D001', ['same']), ('D002', ['same'])], 'duplicate canonical item'),
    ([('D002', ['only'])], 'expected D001'),
])
def test_invalid_group_definition_reports_plan_error(tmp_path, monkeypatch, definitions, detail):
    with pytest.raises(ValueError, match=detail):
        grouped_report(tmp_path, monkeypatch, definitions)


def test_native_freeze_preserves_alias_states_evidence_and_completed_functions(tmp_path, monkeypatch):
    grouped_report(tmp_path, monkeypatch, [('D001', ['pending']), ('D002', ['accepted'])],
                   extra=[dict(item_id='pending-alias', execution_state='blocked')])
    rows = status.read_ledger('development-items.csv')
    rows[1]['execution_state'] = 'done'
    ledger(tmp_path, 'development-items.csv', rows)
    (tmp_path/'development/tracking/functional-groups.json').write_text(json.dumps(dict(
        groups=[dict(canonical_item_id='pending', aliases=['pending-alias'])])), encoding='utf-8')
    (tmp_path/'development/tracking/verification-cycle.json').write_text(json.dumps(dict(
        interval=10, last_verified_item_ids=[])), encoding='utf-8')
    freeze_path = tmp_path/'development/tracking/native-freeze.json'
    freeze_path.write_text(json.dumps(dict(active=True, scope='all_remaining_native_functions')),
                           encoding='utf-8')
    report = status.summarize()
    assert report['canonical_remaining_count'] == 1 and report['remaining_gate_count'] == 2
    assert report['verification_cycle']['completed_since_check_item_ids'] == ['accepted']
    assert report['development_groups']['groups'][1]['completed_count'] == 1
    assert report['development_groups']['current_group'] is None
    assert report['development_groups']['resume_priority_group'] == 'D001'
    queue = status.queue_snapshot(report)
    assert queue['current_development_group'] is None
    assert queue['native_freeze']['affected_canonical_item_ids'] == ['pending']
    assert queue['native_freeze']['affected_source_record_count'] == 2
    assert queue['items'][0]['native_scheduling_state'] == 'frozen'
    assert [row['execution_state'] for row in queue['items'][0]['source_records']] == ['implemented', 'blocked']
    assert all(row['evidence'] == 'adoption.json' for row in queue['items'][0]['source_records'])
    assert all(row['next_action'] == '核对实际采用' for row in queue['items'][0]['source_records'])
    assert '原生排期冻结' in status.ranked_markdown(report)
    assert '原生开发与验收排期冻结' in status.markdown(report)
    freeze_path.write_text(json.dumps(dict(active=False, scope='all_remaining_native_functions')),
                           encoding='utf-8')
    resumed = status.summarize()
    assert resumed['development_groups']['current_group'] == 'D001'
    assert resumed['native_freeze']['affected_function_count'] == 0
    assert status.queue_snapshot(resumed)['items'][0]['native_scheduling_state'] == 'planned'


@pytest.mark.parametrize('freeze,detail', [
    (dict(active='false', scope='all_remaining_native_functions'), 'active must be boolean'),
    (dict(active=True, scope='all'), 'unsupported freeze scope'),
])
def test_native_freeze_rejects_ambiguous_scheduling_policy(tmp_path, monkeypatch, freeze, detail):
    grouped_report(tmp_path, monkeypatch, [('D001', ['pending'])])
    (tmp_path/'development/tracking/native-freeze.json').write_text(json.dumps(freeze), encoding='utf-8')
    with pytest.raises(ValueError, match=detail):
        status.summarize()

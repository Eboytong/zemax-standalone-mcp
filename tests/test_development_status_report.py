"""Evidence summaries must follow the ledgers and the matching release."""
import csv
import json
from pathlib import Path
from support import development_status as status


def ledger(root, name, rows):
    keys = sorted(set().union(*(row.keys() for row in rows)))
    with (root / 'docs' / name).open('w', encoding='utf-8', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader();writer.writerows(rows)


def test_summary_separates_duplicate_gates_and_current_release(tmp_path,monkeypatch):
    (tmp_path/'docs').mkdir()
    (tmp_path/'pyproject.toml').write_text('[project]\nversion="0.2.0"\n',encoding='utf-8')
    package=dict(task_id='CO-01',execution_state='in_progress',next_action='Run controlled case',blocked_reason='')
    ledger(tmp_path,'development-tasks.csv',[package])
    item=dict(item_id='CO-01.same',work_package='CO-01',execution_state='implemented',next_action='Adopt settings',blocked_reason='',evidence='case.json')
    ledger(tmp_path,'development-items.csv',[item])
    ledger(tmp_path,'development-backlog.csv',[item,dict(item,item_id='CO-01.old',execution_state='baseline')])
    releases=tmp_path/'verification/development/BASE-04';releases.mkdir(parents=True)
    (releases/'release001.json').write_text(json.dumps(dict(version='0.1.0',ordinary_passed=1700)),encoding='utf-8')
    (releases/'release002.json').write_text(json.dumps(dict(version='0.2.0',ordinary_passed=23,native_wheel_passed=4)),encoding='utf-8')
    monkeypatch.setattr(status,'ROOT',tmp_path)
    report=status.summarize();text=status.markdown(report)
    assert report['remaining_gate_count']==2
    assert report['unique_remaining_item_count']==1
    assert report['duplicate_remaining_item_ids']==['CO-01.same']
    assert report['historical_scope_count']==1
    assert '23 项' in text and '4 项' in text
    assert '1700' not in text and 'startup045' not in text
    assert 'Run controlled case' in text
    (releases/'release002.json').unlink()
    report=status.summarize()
    assert report['release'] is None
    assert '尚无与当前版本对应' in status.markdown(report)


def test_canonical_aliases_and_batch_snapshot(tmp_path, monkeypatch):
    (tmp_path/'docs').mkdir()
    (tmp_path/'pyproject.toml').write_text('[project]\nversion="0.1.60"\n', encoding='utf-8')
    ledger(tmp_path, 'development-tasks.csv', [dict(task_id='MA-01', execution_state='in_progress', next_action='Read profile', blocked_reason='')])
    base=dict(work_package='MA-01', execution_state='in_progress', next_action='Read profile', blocked_reason='', evidence='probe.json')
    ledger(tmp_path, 'development-items.csv', [dict(base,item_id='MA-01.GradiumProfile')])
    ledger(tmp_path, 'development-backlog.csv', [dict(base,item_id='CV-02.GradiumProfile')])
    (tmp_path/'docs/development-functional-groups.json').write_text(json.dumps(dict(groups=[dict(canonical_item_id='MA-01.GradiumProfile', aliases=['CV-02.GradiumProfile'])])), encoding='utf-8')
    (tmp_path/'docs/development-batches.json').write_text(json.dumps(dict(batch_id='B005',completed_item_ids=['done'],target=10,current_item='Read profile')),encoding='utf-8')
    monkeypatch.setattr(status,'ROOT',tmp_path)
    r=status.summarize()
    assert r['remaining_gate_count']==2 and r['unique_remaining_item_count']==2
    assert r['canonical_remaining_count']==1 and r['canonical_remaining_ids']==['MA-01.GradiumProfile']
    assert r['current_batch']['batch_id']=='B005'
    assert '1/10' in status.markdown(r)
    old=dict(phases=dict(D3='Materials'),items=[dict(canonical_item_id='MA-01.GradiumProfile',phase='D3'),
        dict(canonical_item_id='already-done',phase='D1')])
    r['current_batch'].update(next_release='0.1.61',candidate_item_ids=['MA-01.GradiumProfile'])
    queue=status.queue_snapshot(r,old)
    assert queue['source_record_count']==2 and queue['canonical_group_count']==1
    assert len(queue['items'])==1
    assert queue['items'][0]['phase']=='D3' and queue['phase_counts']==dict(D3=1)
    assert len(queue['items'][0]['source_records'])==2
    assert queue['items'][0]['source_records'][0]['next_action']=='Read profile'
    assert queue['items'][0]['batch_role']=='candidate'

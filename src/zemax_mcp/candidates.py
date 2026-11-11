"""Candidate snapshots reuse the worker's native copy, recovery and evaluation paths."""
import copy
import uuid
from pathlib import Path
from types import SimpleNamespace

from .data import clean, utc_now
from .errors import ZemaxError
from .history import read_json, write_json


def evaluation_conditions(settings):
    # Resource selection and material availability are candidate design differences.
    return {k: v for k, v in clean(settings).items()
            if k not in {'title', 'notes', 'author', 'material_catalogs', 'files'}}


def compare_candidates(left, right):
    differences = []
    a, b = left.get('evaluation'), right.get('evaluation')
    if not a or not b or a.get('state') != 'succeeded' or b.get('state') != 'succeeded':
        raise ZemaxError('CANDIDATE_NOT_EVALUATED', '两个候选均须按冻结条件成功评价。')
    if a['contract'] != b['contract']:
        differences.append('冻结评价规格或系统评价条件不同')
    ma = {m['key']: m for m in a['metrics']}
    mb = {m['key']: m for m in b['metrics']}
    if ma.keys() != mb.keys():
        differences.append('指标集合不同')
    metrics = []
    from .evaluation import finite_metric
    for key in sorted(ma.keys() & mb.keys()):
        x, y = ma[key], mb[key]
        if x['unit'] != y['unit']:
            differences.append(f'{key}单位不同')
        metrics.append(dict(key=key, unit=x['unit'], left=x['value'], right=y['value'],
                            delta=finite_metric(y['value'] - x['value'], key)))
    external = []
    ea = {item['key']: item for item in left.get('external_metrics', [])}
    eb = {item['key']: item for item in right.get('external_metrics', [])}
    for key in sorted(ea.keys() | eb.keys()):
        x, y = ea.get(key), eb.get(key)
        valid = x is not None and y is not None and x['unit'] == y['unit']
        external.append(dict(key=key, left=x, right=y, comparable=valid,
                             delta=y['value'] - x['value'] if valid else None))
    return dict(compatible=not differences, differences=differences, external_metrics=external,
                metrics=metrics if not differences else [],
                design_differences=dict(left=left['snapshot'], right=right['snapshot']),
                candidate_ids=[left['candidate_id'], right['candidate_id']])


class CandidatesMixin:
    def get_glass_slots(self, req):
        from .joint_glass import available_slots
        return available_slots(self)

    def _register_saved_candidate(self, design_id, candidate_id, model_path, snapshot, task):
        index, path = self._candidate_index(design_id)
        parent = index['baseline_candidate_id']
        entry = dict(candidate_id=candidate_id, parent_candidate_id=parent,
                     label=f"{task['kind']} {candidate_id}", model_path=str(model_path),
                     created_at=utc_now(), snapshot=clean(snapshot), source_revision=self.revision,
                     source_context=self.context(), checkpoints=[], evaluation=None, state='saved',
                     source_task_id=task['task_id'])
        index['candidates'][candidate_id] = entry
        write_json(path, index)
        return dict(design_id=design_id, candidate_id=candidate_id, parent_candidate_id=parent)
    def _candidate_root(self):
        return (self.config.output_dir / '_designs').resolve()

    def _candidate_index(self, design_id):
        root = self._candidate_root()
        path = (root / design_id / 'index.json').resolve()
        if not path.is_relative_to(root):
            raise ZemaxError('INVALID_CANDIDATE_PATH', '候选索引超出输出目录。')
        value = read_json(path)
        if value.get('schema_version') != 1 or value.get('design_id') != design_id:
            raise ZemaxError('INVALID_CANDIDATE_INDEX', '候选索引身份或版本无效。')
        return value, path

    @staticmethod
    def _find_candidate(index, candidate_id):
        if candidate_id not in index['candidates']:
            raise ZemaxError('UNKNOWN_CANDIDATE', '候选编号不存在。', candidate_id=candidate_id)
        return index['candidates'][candidate_id]

    def _candidate_snapshot(self):
        self._require_sequential()
        surfaces = []
        start = 0
        while start is not None:
            page = self.get_surfaces(SimpleNamespace(start=start, count=200, parameter_start=1, parameter_count=254))
            surfaces.extend(page['surfaces'])
            start = page['next_start']
        configurations = self.get_configurations(SimpleNamespace(start=1, count=1000))
        next_start = configurations['next_start']
        while next_start is not None:
            page = self.get_configurations(SimpleNamespace(start=next_start, count=1000))
            configurations['rows'].extend(page['rows'])
            next_start = page['next_start']
        configurations['next_start'] = None
        return clean(dict(settings=self.get_system_settings(None), surfaces=surfaces,
                          configurations=configurations))

    def _candidate_merit_definition(self):
        from .evaluation import MERIT_DEFINITION_FIELDS
        rows, start = [], 1
        while start is not None:
            page = self.get_merit_function(SimpleNamespace(start=start, count=500))
            rows.extend({key: row[key] for key in MERIT_DEFINITION_FIELDS} for row in page['operands'])
            start = page['next_start']
        return clean(rows)

    def _candidate_save(self, index, label, parent=None, current=True):
        candidate_id = uuid.uuid4().hex
        folder = self._candidate_root() / index['design_id'] / candidate_id
        folder.mkdir(parents=True)
        model = folder / 'model.zos'
        original = Path(str(self.system.SystemFile)).parent if current else Path(parent['model_path']).parent
        self._copy_project_resources(original, folder)
        owned = self.system.CopySystem()
        if owned is None:
            raise ZemaxError('COPY_FAILED', '创建候选系统副本失败。')
        operation_error = None
        try:
            if not current and not owned.LoadFile(parent['model_path'], False):
                raise ZemaxError('LOAD_FAILED', '父候选加载失败。')
            owned.SaveAs(str(model))
        except Exception as exc:
            operation_error = exc
            raise
        finally:
            try:
                if owned.Close(False) is False:
                    raise RuntimeError('候选副本Close返回false。')
            except Exception as exc:
                self.requires_reconnect = True
                raise ZemaxError('CLEANUP_FAILED', '候选副本关闭失败。', reason=str(exc),
                    operation_error=self._evaluation_error(operation_error) if operation_error else None) from exc
        if not model.is_file():
            raise ZemaxError('SAVE_FAILED', '原生候选保存未产生模型文件。')
        entry = dict(candidate_id=candidate_id, parent_candidate_id=parent['candidate_id'] if parent else None,
                     label=label, model_path=str(model), created_at=utc_now(),
                     snapshot=self._candidate_snapshot() if current else copy.deepcopy(parent['snapshot']),
                     source_revision=self.revision, source_context=self.context(),
                     resources=[str(p.relative_to(folder)) for p in folder.iterdir() if p.is_dir()],
                     checkpoints=[], evaluation=None, state='saved')
        index['candidates'][candidate_id] = entry
        return entry

    def _candidate_context(self):
        current = getattr(self, '_selected_candidate', None)
        if current and str(self.work_path) == current['working_file']:
            return {key: current[key] for key in ('design_id', 'candidate_id', 'parent_candidate_id')}
        return {}

    def manage_candidates(self, req):
        q = req.request
        if q.action == 'list':
            if q.design_id:
                index, _ = self._candidate_index(q.design_id)
                return index
            return dict(designs=[dict(design_id=p.parent.name, index_path=str(p))
                                 for p in sorted(self._candidate_root().glob('*/index.json'))])
        if q.action == 'create':
            self._require_work()
            index = dict(schema_version=1, design_id=uuid.uuid4().hex, label=q.label,
                         created_at=utc_now(), contract=dict(evaluation=q.evaluation.model_dump(),
                             conditions=evaluation_conditions(self.get_system_settings(None))), candidates={})
            baseline = self._candidate_save(index, q.label)
            baseline['external_metrics'] = [m.model_dump() for m in q.external_metrics]
            if q.evaluation.merit:
                index['contract']['merit_definition'] = self._candidate_merit_definition()
            index['baseline_candidate_id'] = baseline['candidate_id']
            path = self._candidate_root() / index['design_id'] / 'index.json'
            write_json(path, index)
            return dict(design_id=index['design_id'], candidate=baseline, contract=index['contract'])
        index, path = self._candidate_index(q.design_id)
        if q.action == 'branch':
            parent = self._find_candidate(index, q.parent_candidate_id)
            entry = self._candidate_save(index, q.label, parent, current=False)
            write_json(path, index)
            return dict(design_id=q.design_id, candidate=entry)
        if q.action == 'compare':
            return compare_candidates(self._find_candidate(index, q.left_candidate_id),
                                      self._find_candidate(index, q.right_candidate_id))
        entry = self._find_candidate(index, q.candidate_id)
        if q.action == 'checkpoint':
            if self._candidate_context().get('candidate_id') != q.candidate_id:
                raise ZemaxError('CANDIDATE_NOT_SELECTED', '请先选择当前候选。')
            checkpoint = self._candidate_save(index, q.label, entry)
            checkpoint['modification_summary'] = q.modification_summary
            checkpoint['external_metrics'] = [m.model_dump() for m in q.external_metrics]
            entry['checkpoints'].append(checkpoint['candidate_id'])
            write_json(path, index)
            self._selected_candidate = dict(design_id=q.design_id, candidate_id=checkpoint['candidate_id'],
                parent_candidate_id=q.candidate_id, working_file=str(self.work_path))
            return dict(design_id=q.design_id, candidate=checkpoint)
        before = self._checkpoint('candidate_select') if self.work_path else None
        source, work = self.source_path, self.work_path
        marker = {}
        try:
            self.open_lens(SimpleNamespace(path=entry['model_path']))
        except Exception:
            if before:
                self._restore_model(marker, before, source, work)
            raise
        self._selected_candidate = dict(design_id=q.design_id, candidate_id=q.candidate_id,
            parent_candidate_id=entry['parent_candidate_id'], working_file=str(self.work_path))
        return dict(selected=self._candidate_context(), actual=self._candidate_snapshot(),
                    recovery_checkpoint=before, context=self.context())

    def run_candidate_evaluation(self, req):
        from .models import Evaluation
        index, path = self._candidate_index(req.design_id)
        if len(set(req.candidate_ids)) != len(req.candidate_ids):
            raise ZemaxError('INVALID_ARGUMENT', '候选编号不可重复。')
        entries = [self._find_candidate(index, key) for key in req.candidate_ids]
        spec = Evaluation.model_validate(index['contract']['evaluation'])
        self._require_work()
        def flow(task):
            snapshot = self._checkpoint('candidate_evaluation')
            source, work = self.source_path, self.work_path
            selected = getattr(self, '_selected_candidate', None)
            try:
                for i, entry in enumerate(entries):
                    self._cancel_boundary(task)
                    self.open_lens(SimpleNamespace(path=entry['model_path']))
                    self._selected_candidate = dict(design_id=req.design_id,
                        candidate_id=entry['candidate_id'], parent_candidate_id=entry['parent_candidate_id'],
                        working_file=str(self.work_path))
                    actual = evaluation_conditions(self.get_system_settings(None))
                    if actual != index['contract']['conditions']:
                        raise ZemaxError('EVALUATION_CONDITIONS_CHANGED', '候选系统条件与冻结评价合同不同。',
                            candidate_id=entry['candidate_id'], expected=index['contract']['conditions'], actual=actual)
                    if spec.merit and self._candidate_merit_definition() != index['contract']['merit_definition']:
                        raise ZemaxError('EVALUATION_CONDITIONS_CHANGED', '候选评价函数定义与冻结合同不同。',
                                         candidate_id=entry['candidate_id'])
                    result = yield from self._evaluate(task, spec)
                    entry['evaluation'] = dict(state='succeeded', task_id=task['task_id'],
                        session_id=self.session_id, contract=copy.deepcopy(index['contract']), **result)
                    task['rows'].append(dict(candidate_id=entry['candidate_id'], **result))
                    write_json(path, index)
                    task['progress'] = int(100 * (i + 1) / len(entries))
                    yield
                task['summary'] = dict(design_id=req.design_id, evaluated=len(task['rows']))
            finally:
                self._restore_model(task, snapshot, source, work)
                self._selected_candidate = selected
        return self._composite('candidate_evaluation', req.model_dump(), flow)

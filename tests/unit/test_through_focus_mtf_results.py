from pathlib import Path
from types import SimpleNamespace as N

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


KINDS = ['fft_through_focus_mtf', 'huygens_through_focus_mtf', 'geometric_through_focus_mtf']


class NativeArray:
    def __init__(self, values, rank):
        self.values, self.Rank = values, rank

    def __iter__(self):
        return iter(self.values)

    def GetLength(self, axis):
        return len(self.values) if axis == 0 else len(self.values[0]) if self.values else 0

    def __getitem__(self, indices):
        row, column = indices
        return self.values[row][column]


def task_backend(tmp_path, kind, mode):
    backend = Backend(Config(Path('unused'), tmp_path))
    backend.directory = tmp_path
    messages = [] if mode == 'valid' else [N(ErrorCode='Success', Text='Computation terminated; invalid results!')]

    def export(path):
        text = '计算终止; 无效的结果!\n' if mode != 'valid' else 'Through-focus MTF\nDefocus Tangential Sagittal\n-1 .2 .3\n1 .4 .5\n'
        if kind == 'cardinal_points': text = 'Cardinal Points\nEffective Focal Length: 100 mm\n'
        Path(path).write_text(text, encoding='utf-16')
        return True

    series = N(XData=N(Data=NativeArray([-1., 1.], 1)), YData=N(Data=NativeArray([[.2, .3], [.4, .5]], 2)),
               SeriesLabels=['Tangential', 'Sagittal'], Description='MTF', XLabel='Defocus')
    if mode == 'empty_curve': series.XData.Data = NativeArray([], 1); series.YData.Data = NativeArray([], 2)
    if mode == 'null_curve': series.XData = None
    result = N(IsValid=mode != 'invalid', HeaderData=N(Lines=['native header']),
               NumberOfMessages=len(messages), GetMessageAt=messages.__getitem__, GetTextFile=export,
               NumberOfDataSeries=int(mode in {'valid', 'empty_curve', 'null_curve'}), NumberOfDataGrids=0,
               GetDataSeries=lambda _: series)
    events = []
    native = N(GetResults=lambda: None if mode == 'null_result' else result,
               IsRunning=lambda: False, WaitForCompletion=lambda: events.append('wait'),
               Close=lambda: events.append('close'))
    task = dict(task_id='mtf', kind='analysis', state='running', native=native, analysis=True,
                cancel_requested=False, before={}, context={}, settings=dict(kind=kind), system_settings={},
                can_cancel=False, result=None, collector=backend._collect_general_analysis)
    backend.tasks['mtf'] = task
    backend.active = task
    backend._save_task_result = lambda task, result: task.update(result=result)
    return backend, task, events


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('mode', ['empty', 'invalid', 'empty_curve', 'null_curve', 'null_result'])
def test_through_focus_missing_curve_fails_task_and_closes_native(tmp_path, kind, mode):
    backend, task, events = task_backend(tmp_path, kind, mode)
    backend.tick()
    assert task['state'] == 'failed'
    assert task['error']['code'] == 'NO_RESULT_DATA'
    if mode != 'null_result':
        details = task['error']['details']
        assert details['native_messages'][0]['text'] == 'Computation terminated; invalid results!'
        if mode != 'invalid':
            assert details['native_text'] == str(tmp_path / 'mtf_native.txt')
    assert task['result']['completed'] is False
    assert events == ['wait', 'close']
    assert backend.active is None


@pytest.mark.parametrize('kind', KINDS)
def test_through_focus_native_curves_succeed(tmp_path, kind):
    backend, task, events = task_backend(tmp_path, kind, 'valid')
    backend.tick()
    assert task['state'] == 'succeeded', task.get('error')
    curve = task['result']['series'][0]
    assert curve['x'] == [-1., 1.]
    assert curve['y'] == [[.2, .3], [.4, .5]]
    assert curve['value_units'] == ['dimensionless', 'dimensionless']
    assert events == ['wait', 'close']


def test_valid_native_text_report_without_curves_remains_supported(tmp_path):
    backend, task, events = task_backend(tmp_path, 'cardinal_points', 'valid')
    result = task['native'].GetResults()
    result.NumberOfDataSeries = 0
    backend.tick()
    assert task['state'] == 'succeeded'
    assert task['result']['structured_data_available'] is False
    assert task['result']['artifacts'][0]['kind'] == 'native_text'
    assert events == ['wait', 'close']


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('code,text', [
    ('InvalidResult', 'Native failure'),
    ('Success', 'Computation terminated; invalid results!'),
    ('Success', '计算终止; 无效的结果!'),
])
def test_through_focus_fatal_message_rejects_spurious_curves(tmp_path, kind, code, text):
    backend, task, events = task_backend(tmp_path, kind, 'valid')
    result = task['native'].GetResults()
    result.NumberOfMessages = 1
    result.GetMessageAt = lambda _: N(ErrorCode=code, Text=text)
    backend.tick()
    assert task['state'] == 'failed'
    assert task['error']['code'] == 'NO_RESULT_DATA'
    assert task['error']['details']['native_messages'] == [dict(code=code, text=text)]
    assert events == ['wait', 'close']


def test_native_text_report_error_words_are_not_mtf_validation(tmp_path):
    backend, task, _ = task_backend(tmp_path, 'cardinal_points', 'valid')
    result = task['native'].GetResults()
    result.NumberOfDataSeries = 0
    result.NumberOfMessages = 1
    result.GetMessageAt = lambda _: N(ErrorCode='Success', Text='Invalid results from a prior computation')
    backend.tick()
    assert task['state'] == 'succeeded'


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('code', ['NoError', 'ZeroErrors', 'Success', 'Warning'])
def test_through_focus_nonfatal_native_codes_keep_valid_curves(tmp_path, kind, code):
    backend, task, _ = task_backend(tmp_path, kind, 'valid')
    result = task['native'].GetResults()
    result.NumberOfMessages = 1
    result.GetMessageAt = lambda _: N(ErrorCode=code, Text='Native diagnostic')
    backend.tick()
    assert task['state'] == 'succeeded', task.get('error')

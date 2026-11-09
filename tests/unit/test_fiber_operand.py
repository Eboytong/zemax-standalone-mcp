from types import SimpleNamespace as N

import pytest
from pydantic import ValidationError

from zemax_mcp.errors import ZemaxError
from zemax_mcp.fiber_operand import run_fiber_operand, uses_operand
from zemax_mcp.polarization_topics import FiberCouplingSettings


def request(**kw):
    return FiberCouplingSettings(kind='fiber_coupling_settings', **kw)


@pytest.mark.parametrize('patch', [dict(receiver_na=float('nan')), dict(source_na=float('inf')),
    dict(source_na=0), dict(receiver_na=-1), dict(sampling=65), dict(field=0), dict(wavelength=0)])
def test_request_boundaries(patch):
    with pytest.raises(ValidationError):
        request(**patch)


def test_selection_and_native_rejection():
    assert not uses_operand(request())
    assert uses_operand(request(receiver_na=.1))
    assert uses_operand(request(method='operand'))
    with pytest.raises(ZemaxError, match='正式设置回读'):
        uses_operand(request(method='native', field=1))


class Fake:
    def __init__(self, values=(.25, .3, .4), cancel_at=None):
        self.values = iter(values)
        self.arguments = []
        self.cancel_at = cancel_at
        self.native = N(api=N(Editors=N(MFE=N(MeritOperandType=object()))), enum=lambda *a: 'FICL')
        self.system = N(MFE=N(GetOperandValue=self.query))

    def query(self, code, *args):
        self.arguments.append((code, args))
        return next(self.values)

    def _require_sequential(self):
        pass

    def get_system_settings(self, _):
        return dict(fields=[dict(number=1)], wavelengths=[dict(number=1, wavelength_um=.55)], configuration=2)

    def _composite(self, kind, settings, factory):
        self.task = dict(rows=[])
        self.flow = factory(self.task)
        return self.task

    def _cancel_boundary(self, task):
        if self.cancel_at == len(self.arguments):
            from zemax_mcp.evaluation import Cancelled
            raise Cancelled()


@pytest.mark.parametrize('method,slots', [('fast', [0., 2., 4.]), ('huygens', [1., 3., 5.])])
def test_data_modes_and_recorded_inputs(method, slots):
    b = Fake()
    run_fiber_operand(b, request(method='operand', integration=method))
    list(b.flow)
    assert [args[6] for _, args in b.arguments] == slots
    assert b.arguments[0][1][:6] == (2, 1, 1., 1., .1, .1)
    assert b.task['payload']['consistency']['residual'] == pytest.approx(0, abs=1e-15)
    assert len(b.task['rows']) == 3
    assert b.task['payload']['actual_settings']['configuration'] == 2


def test_bad_result_keeps_native_query():
    b = Fake(values=(float('nan'),))
    run_fiber_operand(b, request(method='operand'))
    with pytest.raises(ZemaxError, match='非有限'):
        list(b.flow)
    assert len(b.task['payload']['native_queries']) == 1


def test_cancel_between_queries():
    from zemax_mcp.evaluation import Cancelled
    b = Fake(cancel_at=1)
    run_fiber_operand(b, request(method='operand'))
    next(b.flow)
    with pytest.raises(Cancelled):
        next(b.flow)
    assert len(b.arguments) == 1


def test_out_of_range_does_not_start_task():
    b = Fake()
    with pytest.raises(ZemaxError, match='越界'):
        run_fiber_operand(b, request(method='operand', wavelength=2))
    assert not b.arguments and not hasattr(b, 'task')

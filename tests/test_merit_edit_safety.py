"""Offline merit edits: native column types and honest partial-update diagnostics.

No native application is created. The two bad payloads below reproduce the
arguments in user call records eac1ba1b... and 21485da5... (2026-10-28).
"""
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import MeritPatch


class Cell:
    def __init__(self, kind="Integer", header="面1", active=True, readonly=False):
        self.DataType, self.Header = kind, header
        self.IsActive, self.IsReadOnly = active, readonly
        self.value = 0
        self.writes = []
        self.failure = None

    @property
    def IntegerValue(self):
        return self.value

    @IntegerValue.setter
    def IntegerValue(self, value):
        assert type(value) is int
        self.writes.append(("integer", value))
        self.value = value
        if self.failure:
            raise self.failure

    @property
    def DoubleValue(self):
        return self.value

    @DoubleValue.setter
    def DoubleValue(self, value):
        assert type(value) is float
        self.writes.append(("double", value))
        self.value = value
        if self.failure:
            raise self.failure

    @property
    def Value(self):
        return str(self.value)


class Row:
    def __init__(self, kind="BLNK", target=0, weight=1):
        self.Target, self.Weight = target, weight
        self.Value = self.Contribution = 0
        self.changes = []
        self.ChangeType(kind)
        self.changes.clear()
        self.reject_change = False

    def ChangeType(self, kind):
        if getattr(self, "reject_change", False):
            return False
        self.Type = kind
        self.cells = {i: Cell(active=False) for i in range(2, 10)}
        if kind in {"MNEG", "MNCT", "REAY"}:
            self.cells[2] = Cell("Integer", "面1")
            self.cells[3] = Cell("Integer", "面2")
        if kind=='CONF':self.cells[2]=Cell('Integer','结构#')
        if kind == "REAY":
            self.cells[4] = Cell("Double", "Px")
            self.cells[5] = Cell("Double", "Py")
        self.changes.append(kind)

    def GetCellAt(self, column):
        return self.cells[column]


class Editor:
    def __init__(self, rows):
        self.rows = rows
        self.remove_calls = []
        self.fail_remove = None

    @property
    def NumberOfOperands(self):
        return len(self.rows)

    def GetOperandAt(self, number):
        return self.rows[number - 1]

    def AddOperand(self):
        row = Row()
        self.rows.append(row)
        return row

    def RemoveOperandAt(self, number):
        self.remove_calls.append(number)
        if self.fail_remove == number:
            raise RuntimeError("native delete failed")
        if len(self.rows) == 1:
            self.rows[0].ChangeType("BLNK")
        else:
            self.rows.pop(number - 1)


def setup(tmp_path, rows=None):
    editor = Editor(rows if rows is not None else [Row("PMAG", target=2, weight=3)])
    system = NS(Mode="Sequential", MFE=editor,MCE=NS(NumberOfConfigurations=1))
    native = NS(system=system, api=NS(Editors=NS(MFE=NS(MeritOperandType=object()))),
                enum=lambda _enum, name: name)
    backend = Backend(Config(Path("unused"), tmp_path), native)
    backend.tick = lambda: None
    backend.work_path, backend.directory = tmp_path / "work.zos", tmp_path
    backend.checkpoints = []
    def checkpoint(label):
        backend.checkpoints.append(label)
        backend.last_checkpoint = str(tmp_path / "before.zos")
    backend._checkpoint = checkpoint
    return backend, editor


BAD_FIRST = {
    "mode": "append", "operands": [
        {"type": "PMAG", "target": -10, "weight": 50},
        {"type": "MNEG", "target": 0, "weight": 1, "parameters": {"2": 0, "3": .4}},
        {"type": "MNCT", "target": 0, "weight": 1, "parameters": {"2": .6}},
    ],
}
BAD_SECOND = {
    "mode": "append", "operands": [
        {"type": "MNEG", "target": 0, "weight": 1, "parameters": {"2": 0, "3": .4}},
        {"type": "MNCT", "target": 0, "weight": 1, "parameters": {"2": 0, "3": .6}},
    ],
}


def test_request_numeric_values_do_not_imply_double_native_cells():
    item = MeritPatch.model_validate(BAD_SECOND).operands[0]
    assert item.parameters == {2: 0., 3: .4}
    assert type(item.parameters[2]) is float  # Pydantic storage is not native DataType.


def test_valid_integer_indices_and_double_parameters_use_distinct_setters(tmp_path):
    backend, editor = setup(tmp_path)
    response = backend.dispatch("update_merit_function", {"mode": "append", "operands": [
        {"type": "REAY", "target": .4, "parameters": {"2": 1, "3": 2, "4": .125, "5": -.25}},
    ]})
    assert response["ok"]
    row = editor.rows[-1]
    assert row.cells[2].writes == [("integer", 1)]
    assert row.cells[4].writes == [("double", .125)]
    assert row.Target == .4


@pytest.mark.parametrize("payload,index,completed,total", [
    (BAD_FIRST, 1, [2], 3),
    (BAD_SECOND, 0, [], 2),
])
def test_actual_bad_payloads_report_wrong_column_and_partial_effects(tmp_path, payload, index, completed, total):
    original = Row("PMAG", target=2, weight=3)
    backend, editor = setup(tmp_path, [original])
    response = backend.dispatch("update_merit_function", payload)
    assert not response["ok"] and response["error"]["code"] == "INVALID_ARGUMENT"
    details = response["error"]["details"]
    assert details["column"] == 3 and details["header"] == "面2"
    assert details["requested"] == .4 and details["data_type"] == "Integer"
    assert details["failed_index"] == index
    assert details["completed_operands"] == completed
    assert details["partial_changes_possible"] and not details["rollback_performed"]
    assert details["phase"] == "validate_parameters"
    assert details["failed_operation"]["operand_type"] == "MNEG"
    assert details["failed_operation"]["applied_fields"] == ["type"]
    assert details["operand_count_after_error"] == total
    assert editor.rows[0] is original and original.Target == 2
    assert not editor.remove_calls  # No hidden rollback or full-design load.
    assert not editor.rows[-1].cells[2].writes  # Validate .4 before writing index 0.
    assert all(row.Type != "MNCT" for row in editor.rows)
    if completed:
        assert editor.rows[1].Type == "PMAG"
        assert (editor.rows[1].Target, editor.rows[1].Weight) == (-10, 50)


def test_correct_boundary_thresholds_belong_to_target_not_surface_columns(tmp_path):
    backend, editor = setup(tmp_path)
    response = backend.dispatch("update_merit_function", {"mode": "append", "operands": [
        {"type": "MNEG", "target": .4, "parameters": {"2": 1, "3": 8}},
        {"type": "MNCT", "target": .6, "parameters": {"2": 1, "3": 8}},
    ]})
    assert response["ok"]
    assert [row.Target for row in editor.rows[1:]] == [.4, .6]
    assert [row.cells[3].value for row in editor.rows[1:]] == [8, 8]


def test_unchanged_type_updates_are_all_preflighted_before_any_mutation(tmp_path):
    rows = [Row("MNEG", target=2), Row("MNCT", target=3)]
    backend, editor = setup(tmp_path, rows)
    response = backend.dispatch("update_merit_function", {"mode": "update", "updates": [
        {"operand": 1, "target": 9},
        {"operand": 2, "parameters": {"3": .4}},
    ]})
    details = response["error"]["details"]
    assert not response["ok"] and details["phase"] == "preflight"
    assert not details["partial_changes_possible"] and not details["mutation_started"]
    assert not backend.checkpoints and backend.revision == 0
    assert editor.rows[0].Target == 2 and not editor.rows[1].cells[3].writes


@pytest.mark.parametrize("readonly,active", [(True, True), (False, False)])
def test_unwritable_parameter_is_preflight_error(tmp_path, readonly, active):
    row = Row("MNEG")
    row.cells[2].IsReadOnly, row.cells[2].IsActive = readonly, active
    backend, _ = setup(tmp_path, [row])
    response = backend.dispatch("update_merit_function", {"mode": "update", "updates": [
        {"operand": 1, "target": .4, "parameters": {"2": 1}},
    ]})
    assert response["error"]["code"] == "CELL_NOT_WRITABLE"
    assert backend.revision == 0 and row.Target == 0


@pytest.mark.parametrize('kind', ['BLNK', 'PMAG'])
def test_last_operand_false_return_accepts_confirmed_retained_blank(tmp_path, kind):
    backend, editor = setup(tmp_path, [Row(kind)])
    remove = editor.RemoveOperandAt
    def native_remove(number):
        remove(number)
        return False
    editor.RemoveOperandAt = native_remove
    response = backend.dispatch('update_merit_function', {'mode': 'delete', 'operand_numbers': [1]})
    assert response['ok']
    assert editor.NumberOfOperands == 1 and editor.rows[0].Type == 'BLNK'


def test_last_operand_false_return_with_retained_nonblank_is_rejected(tmp_path):
    backend, editor = setup(tmp_path, [Row('PMAG')])
    editor.RemoveOperandAt = lambda number: False
    response = backend.dispatch('update_merit_function', {'mode': 'delete', 'operand_numbers': [1]})
    assert not response['ok'] and response['error']['code'] == 'SETTING_REJECTED'


def test_changed_type_failure_is_explicit_without_reverting_design(tmp_path):
    row = Row("PMAG", target=7, weight=3)
    backend, _ = setup(tmp_path, [row])
    response = backend.dispatch("update_merit_function", {"mode": "update", "updates": [
        {"operand": 1, "type": "MNCT", "target": .6, "parameters": {"3": .6}},
    ]})
    assert row.Type == "MNCT" and row.Target == 7 and row.Weight == 3
    details = response["error"]["details"]
    assert details["partial_changes_possible"] and details["failed_operation"]["applied_fields"] == ["type"]
    assert not details["rollback_performed"]


def test_native_setter_can_change_then_throw_so_attempted_field_remains_uncertain(tmp_path):
    row = Row("REAY")
    row.cells[4].failure = RuntimeError("native setter failed after assignment")
    backend, _ = setup(tmp_path, [row])
    response = backend.dispatch("update_merit_function", {"mode": "update", "updates": [
        {"operand": 1, "target": 9, "parameters": {"2": 1, "4": .25, "5": .5}},
    ]})
    details = response["error"]["details"]
    assert response["error"]["code"] == "NATIVE_ERROR"
    assert details["failed_operation"]["attempted_field"] == "parameters.4"
    assert details["failed_operation"]["applied_fields"] == ["target", "parameters.2"]
    assert row.cells[4].value == .25 and not row.cells[5].writes
    assert details["partial_changes_possible"] and not details["rollback_performed"]


def test_replace_failure_reports_removed_rows_not_a_silent_restore(tmp_path):
    backend, editor = setup(tmp_path, [Row("PMAG", 5), Row("REAY", 7)])
    response = backend.dispatch("update_merit_function", {**BAD_SECOND, "mode": "replace"})
    details = response["error"]["details"]
    assert not response["ok"] and details["removed_operands"] == [2, 1]
    assert editor.rows[0].Type == "MNEG" and len(editor.rows) == 1
    assert not details["rollback_performed"] and details["partial_changes_possible"]


def test_delete_failure_reports_completed_deletions(tmp_path):
    backend, editor = setup(tmp_path, [Row("PMAG"), Row("REAY"), Row("MNCT")])
    editor.fail_remove = 2
    response = backend.dispatch("update_merit_function", {"mode": "delete", "operand_numbers": [2, 3]})
    details = response["error"]["details"]
    assert not response["ok"] and details["removed_operands"] == [3]
    assert details["failed_operation"]["operand"] == 2
    assert details["partial_changes_possible"] and len(editor.rows) == 2


def test_same_type_update_does_not_reset_untouched_parameters(tmp_path):
    row = Row("REAY")
    row.cells[4].value = .75
    backend, _ = setup(tmp_path, [row])
    response = backend.dispatch("update_merit_function", {"mode": "update", "updates": [
        {"operand": 1, "type": "REAY", "target": 2},
    ]})
    assert response["ok"] and row.cells[4].value == .75 and not row.changes


def test_rejected_type_change_reports_native_result(tmp_path):
    row = Row("PMAG")
    row.reject_change = True
    backend, _ = setup(tmp_path, [row])
    response = backend.dispatch("update_merit_function", {"mode": "update", "updates": [
        {"operand": 1, "type": "MNCT", "target": .6},
    ]})
    assert response["error"]["code"] == "SETTING_REJECTED"
    assert response["error"]["details"]["actual"] == "PMAG"
    assert row.Target == 0


def test_initial_blank_row_partial_failure_is_reported_even_without_added_row(tmp_path):
    backend, editor = setup(tmp_path, [Row()])
    response = backend.dispatch("update_merit_function", BAD_SECOND)
    details = response["error"]["details"]
    assert not response["ok"] and details["added_operands"] == []
    assert details["failed_operation"]["operand"] == 1
    assert details["partial_changes_possible"] and editor.rows[0].Type == "MNEG"


def test_readback_failure_is_not_reported_as_success(tmp_path):
    backend, editor = setup(tmp_path)
    backend.get_merit_function = lambda _: (_ for _ in ()).throw(RuntimeError("readback unavailable"))
    response = backend.dispatch("update_merit_function", {"mode": "append", "operands": [
        {"type": "PMAG", "target": -10, "weight": 50},
    ]})
    details = response["error"]["details"]
    assert response["error"]["code"] == "NATIVE_ERROR" and details["phase"] == "readback"
    assert details["completed_operands"] == [2] and details["partial_changes_possible"]
    assert editor.rows[-1].Target == -10 and not details["rollback_performed"]


def test_delete_with_no_native_effect_returns_explicit_failure(tmp_path):
    backend, editor = setup(tmp_path, [Row("PMAG"), Row("REAY")])
    editor.RemoveOperandAt = lambda _: None
    response = backend.dispatch("update_merit_function", {"mode": "delete", "operand_numbers": [2]})
    assert response["error"]["code"] == "SETTING_REJECTED"
    assert response["error"]["details"]["removed_operands"] == []


def test_wizard_failure_keeps_deleted_row_impact_and_does_not_restore(tmp_path):
    backend, editor = setup(tmp_path, [Row("PMAG"), Row("REAY")])
    wizard = NS(ResetSettings=lambda: None,
                Apply=lambda: (_ for _ in ()).throw(RuntimeError("wizard failed")))
    editor.SEQOptimizationWizard2 = wizard
    backend.system.MCE = NS(CurrentConfiguration=1)
    backend.native.set_enum = lambda target, key, value: setattr(target, key, value)
    response = backend.dispatch("update_merit_function", {"mode": "rms_spot_wizard"})
    details = response["error"]["details"]
    assert not response["ok"] and details["phase"] == "wizard"
    assert details["removed_operands"] == [2, 1]
    assert details["failed_operation"]["attempted_field"] == "wizard"
    assert editor.rows[0].Type == "BLNK" and not details["rollback_performed"]


def test_enum_failure_precedes_checkpoint_and_all_operand_writes(tmp_path):
    backend, editor = setup(tmp_path)
    def enum(_kind, name):
        if name == "BAD":
            raise ValueError("unknown native operand")
        return name
    backend.native.enum = enum
    response = backend.dispatch("update_merit_function", {"mode": "append", "operands": [
        {"type": "PMAG", "target": -10}, {"type": "BAD"},
    ]})
    details = response["error"]["details"]
    assert not response["ok"] and details["phase"] == "preflight"
    assert details["failed_index"] == 1 and not details["partial_changes_possible"]
    assert not backend.checkpoints and len(editor.rows) == 1


def test_multi_configuration_replace_requires_explicit_conf_before_mutation(tmp_path):
    backend,editor=setup(tmp_path);backend.system.MCE.NumberOfConfigurations=2
    response=backend.dispatch('update_merit_function',dict(mode='replace',operands=[dict(type='PMAG')]))
    assert response['error']['code']=='INVALID_ARGUMENT'
    assert not backend.checkpoints and editor.rows[0].Type=='PMAG'


def test_conf_implicit_fields_remain_native_and_explicit_fields_are_rejected(tmp_path):
    row=Row('CONF',target=float('inf'),weight=float('inf'));backend,editor=setup(tmp_path,[row])
    response=backend.dispatch('update_merit_function',dict(mode='update',updates=[dict(operand=1,parameters={'2':2})]))
    assert response['ok']and row.Target==row.Weight==float('inf')
    rejected=backend.dispatch('update_merit_function',dict(mode='append',operands=[dict(type='CONF',target=0)]))
    assert rejected['error']['code']=='INACTIVE_SETTING'and len(editor.rows)==1


def test_final_native_row_rewrite_returns_readback_failure(tmp_path):
    backend,editor=setup(tmp_path,[Row('BLNK')]);add=editor.AddOperand
    def corrupt():
        row=add();editor.rows[0].ChangeType('CONF');return row
    editor.AddOperand=corrupt
    response=backend.dispatch('update_merit_function',dict(mode='replace',operands=[dict(type='PMAG'),dict(type='PMAG')]))
    assert response['error']['code']=='SETTING_REJECTED'
    assert response['error']['details']['phase']=='readback'
    assert response['error']['details']['mutation_started']

"""State-dependent Hologram2 persistence guards at both public write entries."""
from types import SimpleNamespace as NS

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


class Cell:
    IsActive = True
    IsReadOnly = False
    Header = "test parameter"

    def __init__(self, value=0, mode="Fixed", integer=False):
        self.value, self.Solve = value, mode
        self.DataType = "Integer" if integer else "Double"
        self.writes = []
        self.ignore_value = False
        self.ignore_mode = False

    @property
    def IntegerValue(self):
        return self.value

    @IntegerValue.setter
    def IntegerValue(self, value):
        self.writes.append(("value", value))
        if not self.ignore_value:
            self.value = value

    @property
    def DoubleValue(self):
        return self.value

    @DoubleValue.setter
    def DoubleValue(self, value):
        self.IntegerValue = value

    def IsSolveTypeSupported(self, mode):
        return True

    def GetAvailableSolveTypes(self):
        return ["Fixed", "Variable", "SurfacePickup", "ZPLMacro"]

    def apply(self, mode):
        self.writes.append(("mode", mode))
        if not self.ignore_mode:
            self.Solve = mode
        return True

    def MakeSolveVariable(self):
        return self.apply("Variable")

    def MakeSolveFixed(self):
        return self.apply("Fixed")


def backend(tmp_path, value=0, mode="Fixed", kind="Hologram2"):
    cells = {"parameter_1": Cell(), "parameter_13": Cell(value, mode, True)}
    row = NS(Type=kind, SurfaceNumber=1, IsObject=False, IsImage=False, IsStop=False, Comment="before",
             ApertureData=NS(IsPickedUp=False), AvailableSurfaceTypes=lambda: ["Standard", "Hologram2"])
    def change_type(settings):
        if row.Type != settings:
            row.Type = settings
            cells["parameter_13"].value = 0
            cells["parameter_13"].Solve = "Fixed"
        return True
    row.GetSurfaceTypeSettings = lambda kind: kind
    row.ChangeType = change_type
    native = NS(system=NS(Mode="Sequential"), enum=lambda kind, name: name,
                api=NS(Editors=NS(SolveType=NS(), LDE=NS(SurfaceType=NS()))))
    b = Backend(Config(tmp_path, tmp_path), native)
    b._row = lambda i: row
    b._cell = lambda row, name: cells[name]
    b._cells = lambda row, start=1, count=254: ((name,cell)for name,cell in cells.items()
        if start<=int(name.removeprefix('parameter_'))<start+count)
    b._surface_properties = lambda row: {}
    b.get_variables = lambda _: dict(variables=[name for name, cell in cells.items() if cell.Solve == "Variable"])
    b.checkpoints = []
    b._checkpoint = lambda label: b.checkpoints.append(label)
    return b, row, cells


@pytest.mark.parametrize("command", ["set_variables", "update_surfaces"])
def test_zero_variable_rejected_before_whole_batch(tmp_path, command):
    b, row, cells = backend(tmp_path)
    args = dict(variables=[dict(surface=1, cell="parameter_1"), dict(surface=1, cell="parameter_13")]) if command == "set_variables" else dict(changes=[
        dict(surface=2, comment="must not write"), dict(surface=1, solves={"parameter_13": dict(mode="variable")})])
    result = b.dispatch(command, args)
    assert not result["ok"] and result["error"]["code"] == "UNSUPPORTED_SOLVE"
    assert result["error"]["details"]["value"] == 0
    assert not result["error"]["details"]["partial_changes_possible"]
    assert b.revision == 0 and not b.checkpoints
    assert row.Comment == "before" and all(not c.writes for c in cells.values())


@pytest.mark.parametrize("command", ["set_variables", "update_surfaces"])
@pytest.mark.parametrize("value", [0, 1])
def test_fixed_values_and_enabled_variable(tmp_path, command, value):
    b, row, cells = backend(tmp_path, value)
    variable = value == 1
    args = dict(variables=[dict(surface=1, cell="parameter_13", variable=variable)]) if command == "set_variables" else dict(changes=[
        dict(surface=1, solves={"parameter_13": dict(mode="variable" if variable else "fixed")})])
    result = b.dispatch(command, args)
    assert result["ok"], result
    assert cells["parameter_13"].Solve == ("Variable" if variable else "Fixed")
    data = b._surface_data(1)["cells"]["parameter_13"]
    assert "Variable" in data["available_solves"]
    assert data["solve_persistence"]["variable_persists"] == variable


@pytest.mark.parametrize("kind", ["Standard", "Hologram2"])
def test_enable_and_variable_in_one_patch(tmp_path, kind):
    b, row, cells = backend(tmp_path, kind=kind)
    result = b.dispatch("update_surfaces", dict(changes=[dict(surface=1, surface_type="Hologram2",
        parameters={13: 1}, solves={"parameter_13": dict(mode="variable")}, replace_solves=True)]))
    assert result["ok"], result
    assert row.Type == "Hologram2" and cells["parameter_13"].value == 1
    assert cells["parameter_13"].Solve == "Variable"


def test_type_switch_rejected_before_mutation(tmp_path):
    b, row, cells = backend(tmp_path, kind="Standard")
    result = b.dispatch("update_surfaces", dict(changes=[dict(surface=1, surface_type="Hologram2",
        solves={"parameter_13": dict(mode="variable")}, replace_solves=True)]))
    assert result["error"]["code"] == "UNSUPPORTED_SOLVE"
    assert row.Type == "Standard" and b.revision == 0 and not b.checkpoints


@pytest.mark.parametrize("fixed", [False, True])
def test_disabling_variable_requires_explicit_fixed(tmp_path, fixed):
    b, row, cells = backend(tmp_path, 1, "Variable")
    change = dict(surface=1, parameters={13: 0})
    if fixed:
        change["solves"] = {"parameter_13": dict(mode="fixed")}
    result = b.dispatch("update_surfaces", dict(changes=[change]))
    assert result["ok"] == fixed
    assert cells["parameter_13"].value == (0 if fixed else 1)
    assert b.revision == int(fixed)


@pytest.mark.parametrize("value", [-1, .5, 2])
def test_invalid_boolean_is_preflight_error(tmp_path, value):
    b, row, cells = backend(tmp_path)
    result = b.dispatch("update_surfaces", dict(changes=[dict(surface=1, parameters={13: value})]))
    assert result["error"]["code"] == "INVALID_ARGUMENT" and b.revision == 0
    assert not cells["parameter_13"].writes


def test_type_switched_value_ignored_prevents_variable_write(tmp_path):
    b, row, cells = backend(tmp_path, kind="Standard")
    cells["parameter_13"].ignore_value = True
    result = b.dispatch("update_surfaces", dict(changes=[dict(surface=1, surface_type="Hologram2", replace_solves=True,
        parameters={13: 1}, solves={"parameter_13": dict(mode="variable")})]))
    assert result["error"]["code"] == "PARTIAL_UPDATE"
    assert result["error"]["details"]["cause"]["code"] == "SETTING_REJECTED"
    assert b.revision == 1 and cells["parameter_13"].Solve == "Fixed"


@pytest.mark.parametrize("command", ["set_variables", "update_surfaces"])
def test_enabled_mode_false_success_is_still_checked(tmp_path, command):
    b, row, cells = backend(tmp_path, 1)
    cells["parameter_13"].ignore_mode = True
    args = dict(variables=[dict(surface=1, cell="parameter_13")]) if command == "set_variables" else dict(changes=[
        dict(surface=1, solves={"parameter_13": dict(mode="variable")})])
    result = b.dispatch(command, args)
    error = result["error"]["details"]["cause"] if command == "update_surfaces" else result["error"]
    assert error["code"] == "SOLVE_UPDATE_FAILED"


@pytest.mark.parametrize("command", ["set_variables", "update_surfaces"])
def test_continuous_parameter_remains_variable(tmp_path, command):
    b, row, cells = backend(tmp_path)
    args = dict(variables=[dict(surface=1, cell="parameter_1")]) if command == "set_variables" else dict(changes=[
        dict(surface=1, solves={"parameter_1": dict(mode="variable")})])
    assert b.dispatch(command, args)["ok"]
    assert cells["parameter_1"].Solve == "Variable"

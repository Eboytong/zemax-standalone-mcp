"""Deterministic sequential backend for composite-task failure tests."""
from types import SimpleNamespace
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def fake_backend(tmp_path):
    system = SimpleNamespace(Mode="Sequential", value=4., fail_restore=False)
    snapshots = {}
    def save(path):
        snapshots[path] = system.value
    def load(path, save):
        if system.fail_restore:
            return False
        if path not in snapshots:
            return False
        system.value = snapshots[path]
        return True
    system.SaveAs, system.LoadFile = save, load
    backend = Backend(Config(tmp_path, tmp_path), SimpleNamespace(system=system))
    backend.directory = tmp_path
    backend.work_path = tmp_path/"original.zos"
    backend.source_path = "source.zos"
    backend.get_system_settings = lambda _: {"lens_units": "Millimeters", "material_catalogs": [], "files": {}, "polarization": {}, "ray_aiming": {}, "field_normalization": "Radial", "fields": []}
    def checkpoint(label):
        path = str(tmp_path/"baseline.zos")
        save(path)
        backend.last_checkpoint = path
        return path
    backend._checkpoint = checkpoint
    backend._row = lambda _: None
    backend._cell = lambda row, name: SimpleNamespace(IsReadOnly=False, IsActive=True, Solve="Fixed")
    backend.update_surfaces = lambda req: setattr(system, "value", req.changes[0].thickness)
    def evaluate(task, spec):
        yield
        if system.value < 0:
            raise RuntimeError("bad point")
        return {"metrics": [{"key": "value", "value": system.value, "unit": "mm"}], "conditions": {"focus": None}}
    backend._evaluate = evaluate
    return backend, system


def finish(backend):
    for _ in range(100):
        if not backend.active:
            return
        backend.tick()
    raise AssertionError("task did not finish")


def start(backend, values):
    response = backend.dispatch("run_parameter_scan", {"surface": 1, "cell": "thickness", "values": values, "evaluation": {"merit": True}})
    assert response["ok"], response
    return response["data"]["task_id"]


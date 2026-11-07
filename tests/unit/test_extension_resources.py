from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from zemax_mcp.extension_resources import EXTENSION_FOLDERS, extension_files
from zemax_mcp.models import SystemResources
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize('payload', [
    {'kind': 'extension_files'},
    {'kind': 'catalogs', 'extension_role': 'surface'},
    {'kind': 'extension_files', 'extension_role': '../DLL'},
    {'kind': 'extension_files', 'extension_role': 'unknown'},
])
def test_extension_resource_type_constraints(payload):
    with pytest.raises(ValidationError):
        SystemResources(**payload)


@pytest.mark.parametrize('role', EXTENSION_FOLDERS)
def test_extension_file_roles_use_native_data_root(tmp_path, role):
    folder, extensions = EXTENSION_FOLDERS[role]
    target = tmp_path / folder
    target.mkdir(parents=True)
    (target / 'Example.DLL').write_bytes(b'fixture')
    (target / 'Example.cpp').write_text('source fixture')
    (target / 'subfolder.dll').mkdir()
    app = SimpleNamespace(ZemaxDataDir=str(tmp_path))
    req = SystemResources(kind='extension_files', extension_role=role, query='EXAMPLE')
    assert SystemResources.model_validate(req.model_dump()) == req
    result = extension_files(app, req)
    assert result['items'] == ['Example.DLL']
    assert result['directory'] == str(target)
    assert result['directory_exists'] is True


def test_extension_file_paging_and_missing_directory(tmp_path):
    app = SimpleNamespace(ZPLDir=str(tmp_path))
    for name in ['b.ZPL', 'a.zpl', 'c.zpl']:
        (tmp_path / name).write_text('! fixture')
    req = SystemResources(kind='extension_files', extension_role='zpl', count=2)
    result = extension_files(app, req)
    assert result['items'] == ['a.zpl', 'b.ZPL']
    assert result['total'] == 3 and result['next_start'] == 2
    app.ZPLDir = str(tmp_path / 'missing')
    result = extension_files(app, req)
    assert result['items'] == [] and result['directory_exists'] is False


def test_extension_resources_require_native_connection():
    with pytest.raises(ZemaxError) as exc:
        extension_files(None, SystemResources(kind='extension_files', extension_role='zpl'))
    assert exc.value.code == 'NOT_CONNECTED'

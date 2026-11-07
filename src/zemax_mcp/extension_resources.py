"""Discover extension files under the active application's resource directories."""
from pathlib import Path

from .errors import ZemaxError

EXTENSION_FOLDERS = {
    'surface': ('DLL/Surfaces', {'.dll'}),
    'source': ('DLL/Sources', {'.dll'}),
    'object': ('DLL/Objects', {'.dll'}),
    'surface_scatter': ('DLL/SurfaceScatter', {'.dll'}),
    'bulk_scatter': ('DLL/BulkScatter', {'.dll'}),
    'physical_optics': ('DLL/PhysicalOptics', {'.dll'}),
    'gradient_index': ('DLL/GradientIndex', {'.dll'}),
    'birefringence': ('DLL/Birefringence', {'.dll'}),
    'diffractive': ('DLL/Diffractive', {'.dll'}),
    'user_analysis': ('ZOS-API/User Analysis', {'.exe', '.dll'}),
    'user_operand': ('ZOS-API/Operands', {'.exe', '.dll'}),
    'extension': ('ZOS-API/Extensions', {'.exe', '.dll'}),
    'library': ('ZOS-API/Libraries', {'.dll'}),
}


def extension_files(application, request):
    if application is None:
        raise ZemaxError('NOT_CONNECTED', '请先调用 connect。')
    role = request.extension_role
    if role == 'zpl':
        directory = Path(str(application.ZPLDir))
        suffixes = {'.zpl'}
        source = 'application.ZPLDir'
    else:
        folder, suffixes = EXTENSION_FOLDERS[role]
        directory = Path(str(application.ZemaxDataDir)) / folder
        source = 'application.ZemaxDataDir/' + folder
    if not directory.is_absolute():
        raise ZemaxError('INVALID_RESOURCE_DIRECTORY', 'Native resource directory is not absolute.',
                         role=role, directory=str(directory))
    try:
        names = sorted((p.name for p in directory.iterdir()
                        if p.is_file() and p.suffix.lower() in suffixes
                        and request.query.casefold() in p.name.casefold()), key=str.casefold) if directory.is_dir() else []
    except OSError as exc:
        raise ZemaxError('RESOURCE_DISCOVERY_FAILED', str(exc), role=role, directory=str(directory)) from exc
    end = min(len(names), request.start + request.count)
    return dict(kind='extension_files', extension_role=role, directory=str(directory),
                directory_exists=directory.is_dir(), items=names[request.start:end], total=len(names),
                next_start=end if end < len(names) else None, resource_source=source,
                discovery_scope='files in active resource directory; native selection and execution checked by each consumer')

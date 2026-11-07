"""Ray database viewer through the formal native reader tool."""
from typing import Literal
from pathlib import Path
from pydantic import field_validator
from .nsc_models import ZrdRead


class RayDatabaseViewer(ZrdRead):
    kind: Literal['ray_database_viewer']

    @field_validator('path')
    @classmethod
    def owned_zrd_path(cls, value):
        path=Path(value)
        if not path.is_absolute() or path.suffix.lower()!='.zrd':
            raise ValueError('path须为现有绝对路径的ZRD文件。')
        return value


def run_viewer(b, q):
    view = b.read_zrd(ZrdRead(**q.model_dump(exclude={'kind'})))
    task = b.tasks[view['task_id']]
    task['kind'] = q.kind
    task['settings'] = q.model_dump()
    task['payload'] = dict(analysis_kind=q.kind, computation_method='native_RayDatabaseReader',
        thematic_interface='RayDatabaseViewer AS_Default has no typed file/filter selectors; formal tool used',
        actual_settings=dict(filter=q.filter, start_ray=q.start_ray, start_segment=q.start_segment, max_segments=q.max_segments),
        file_setting_status='ZRDFile is write-only; requested absolute path passed to reader; Run/Succeeded and ray results retained',
        series=[], grids=[])
    return b._task_view(task)

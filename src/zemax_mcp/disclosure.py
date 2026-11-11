"""Stable disclosure modes and shared MCP handler contracts."""
import os
from dataclasses import dataclass
from functools import lru_cache

from mcp.server.mcpserver.tools.base import Tool
from pydantic import ValidationError

from .errors import ZemaxError

BOOTSTRAP = frozenset({'connect', 'disconnect', 'get_status', 'search_capabilities',
    'get_capabilities', 'get_task_status', 'get_task_result', 'cancel_task', 'get_request_status'})

# Reviewed operations: these read model/task data, or perform offline discovery.
READ_ONLY = frozenset({
    'get_status', 'get_capabilities', 'search_capabilities', 'get_system_summary',
    'get_system_settings', 'get_surfaces', 'get_variables', 'get_merit_function',
    'get_task_status', 'get_task_result', 'get_request_status', 'list_task_history',
    'get_historical_result', 'get_glass_slots', 'get_system_resources',
    'get_editor_metadata', 'get_configurations', 'get_nsc_objects', 'get_detector_data',
    'get_coating_layers', 'get_material_properties', 'get_lens_catalogs',
    'get_coating_rta', 'get_surface_geometry',
    'get_hpc_settings', 'get_beam_file', 'compare_results', 'get_project_settings', 'get_external_dependencies',
    'get_constraint_coverage', 'get_tolerances', 'get_design_tool_options',
    'get_optimization_wizard_options', 'get_nsc_object_geometry',
})


def mode_value(mode=None):
    value = mode or os.environ.get('ZEMAX_TOOL_MODE', 'full')
    if value not in {'full', 'compact'}:
        raise ValueError('ZEMAX_TOOL_MODE must be full or compact')
    return value


@dataclass
class Handler:
    tool: Tool

    @property
    def schema(self):
        return self.tool.parameters

    async def invoke(self, arguments):
        unknown = set(arguments) - set(self.schema.get('properties', {}))
        if unknown:
            raise ZemaxError('INVALID_ARGUMENT', '工具参数包含未知字段。', fields=sorted(unknown))
        validated = self.tool.fn_metadata.validate_arguments(arguments)
        return await self.tool.fn_metadata.call_fn(self.tool.fn, True, validated, {})


@lru_cache(maxsize=1)
def contracts():
    from .server import create_server
    return create_server(mode='full').zemax_handlers


def resolve(handlers, capability_id):
    parts = capability_id.split(':')
    if len(parts) == 2 and parts[0] == 'tool' and parts[1] in handlers:
        return dict(tool_name=parts[1])
    if len(parts) == 2 and parts[0] == 'analysis':
        name, field, value = 'run_analysis', 'kind', parts[1]
    elif len(parts) == 3 and parts[0] == 'action' and parts[1] in handlers:
        name, field, value = parts[1], 'action', parts[2]
    else:
        raise ZemaxError('UNKNOWN_CAPABILITY', '能力编号不存在。', capability_id=capability_id)
    mapping = handlers[name].schema.get('properties', {}).get('request', {}).get('discriminator', {})
    if mapping.get('propertyName') == field and value in mapping.get('mapping', {}):
        return dict(tool_name=name, selector=[field,value])
    raise ZemaxError('UNKNOWN_CAPABILITY', '能力编号不存在。', capability_id=capability_id)


async def invoke(handlers, capability_id, arguments, query=False):
    try:
        entry = resolve(handlers, capability_id)
        name = entry['tool_name']
        if query and name not in READ_ONLY:
            raise ZemaxError('READ_ONLY_REQUIRED', '该能力通过 execute_capability 调用。', capability_id=capability_id)
        values = dict(arguments)
        selector = entry.get('selector')
        if selector:
            if not isinstance(values.get('request', {}), dict):
                raise ZemaxError('INVALID_ARGUMENT', 'request 须为对象。', field='request')
            request = dict(values.get('request', {}))
            key, expected = selector
            if key in request and request[key] != expected:
                raise ZemaxError('CAPABILITY_MISMATCH', '请求分支与能力编号不一致。', field=key, expected=expected)
            request[key] = expected
            values['request'] = request
        return await handlers[name].invoke(values)
    except (ZemaxError, ValidationError) as exc:
        from .models import ToolResponse
        error = exc.as_dict() if isinstance(exc, ZemaxError) else dict(code='INVALID_ARGUMENT',
            message='能力参数校验失败。', details={'fields': exc.errors(include_context=False, include_url=False, include_input=False)})
        return ToolResponse(ok=False, data=None, error=error, warnings=[], context={}, artifacts=[])

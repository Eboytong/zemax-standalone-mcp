"""Native HPC configuration selection and existing-tool factory adaptation."""
from .errors import ZemaxError
from .detectors import check_setting_value

HPC_FACTORIES = {'OpenNSCRayTrace','OpenTolerancing','OpenGlobalOptimization','OpenHammerOptimization'}


def prepare_hpc(backend, selection, require_configured=True):
    if selection is None: return None
    owner = backend.system.Tools
    method = 'GetHPCSettingsFromPrefs' if selection.mode == 'preferences' else 'GetHPCSettingsCustom'
    factory = getattr(owner, method, None)
    if factory is None:
        raise ZemaxError('UNSUPPORTED_INTERFACE','本机缺少HPC设置接口。',native_method=method)
    try:
        if selection.mode == 'preferences': settings = factory()
        else:
            enum_type = backend.native.api.Tools.HPCNodeSize
            settings = factory(selection.node_count,backend.native.enum(enum_type,selection.instance_type))
        if settings is None:
            raise ZemaxError('HPC_SETTINGS_UNAVAILABLE','原生HPC设置工厂返回空对象。',native_method=method)
        actual = dict(is_configured=bool(settings.IsHPCConfigured),node_count=int(settings.NodeCount),
                      max_node_count=int(settings.MaxNodeCount),instance_type=str(settings.InstanceType),
                      threads_per_task=int(settings.ThreadsPerTask),shutdown_time_ticks=int(settings.ShutdownTimeTicks),
                      selection=selection.model_dump(),source=method)
    except ZemaxError: raise
    except Exception as exc:
        raise ZemaxError('HPC_SETTINGS_ERROR',str(exc),native_method=method,
                         selection=selection.model_dump(),native_type=type(exc).__name__) from exc
    if selection.mode == 'custom':
        if settings.NodeCount != selection.node_count:
            raise ZemaxError('SETTING_REJECTED','HPC节点数未采用请求值。',requested=selection.node_count,actual=actual)
        if selection.instance_type != 'Default':
            expected = backend.native.enum(backend.native.api.Tools.HPCNodeSize,selection.instance_type)
            if not settings.InstanceType.Equals(expected):
                raise ZemaxError('SETTING_REJECTED','HPC节点规格未采用请求值。',requested=selection.instance_type,actual=actual)
        actual['default_instance_resolved'] = (selection.instance_type == 'Default' and
            not settings.InstanceType.Equals(backend.native.enum(backend.native.api.Tools.HPCNodeSize,'Default')))
    if require_configured and not actual['is_configured']:
        raise ZemaxError('HPC_NOT_CONFIGURED','原生HPC设置报告尚未配置。',actual=actual)
    return dict(native=settings,actual=actual)


def open_execution_tool(backend, method, prepared):
    if method not in HPC_FACTORIES:
        raise ZemaxError('UNSUPPORTED_INTERFACE','此工具没有登记HPC工厂。',native_method=method)
    owner = backend.system.Tools
    if prepared is None: return getattr(owner,method)()
    hpc_method = method+'_HPC'
    factory = getattr(owner,hpc_method,None)
    if factory is None:
        raise ZemaxError('UNSUPPORTED_INTERFACE','本机缺少请求的HPC工具工厂。',native_method=hpc_method,hpc=prepared['actual'])
    try: tool = factory(prepared['native'])
    except Exception as exc:
        raise ZemaxError('HPC_TOOL_ERROR',str(exc),native_method=hpc_method,hpc=prepared['actual'],
                         native_type=type(exc).__name__) from exc
    if tool is None:
        raise ZemaxError('HPC_TOOL_UNAVAILABLE','原生HPC工厂未返回工具。',native_method=hpc_method,hpc=prepared['actual'])
    return tool


def check_tool_values(backend, tool, values):
    for name, value in values.items():
        actual = getattr(tool,name)
        prop = tool.GetType().GetProperty(name)
        if prop is None:
            raise ZemaxError('UNSUPPORTED_SETTING','HPC工具缺少请求的原生设置。',setting=name)
        if prop.PropertyType.IsEnum:
            if not actual.Equals(backend.native.enum(prop.PropertyType,value)):
                raise ZemaxError('SETTING_REJECTED','HPC工具枚举未采用请求值。',setting=name,requested=value,actual=str(actual))
        else: check_setting_value(name,value,actual)


def close_failed_setup(backend, tool, original):
    try: backend._release_owned(tool)
    except Exception as cleanup:
        backend.requires_reconnect = True
        error = original if isinstance(original,ZemaxError) else ZemaxError('NATIVE_ERROR',str(original),native_type=type(original).__name__)
        error.details['cleanup_error'] = cleanup.as_dict() if isinstance(cleanup,ZemaxError) else dict(message=str(cleanup))
        raise error from cleanup


class HpcMixin:
    def get_hpc_settings(self, req):
        prepared = prepare_hpc(self,req.request,require_configured=False)
        return dict(**prepared['actual'],
                    ownership='IHPCSettings has no Close method; no SystemTool opened by this query',
                    readiness='Native configured flag only; actual node/license/job availability is checked during execution')

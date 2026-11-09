"""Owned-copy Speos exports through the installed native SystemTool APIs."""
from pathlib import Path
import uuid

from .analyses import scalar_settings, native_setting
from .imaging import checked, check
from .errors import ZemaxError
from .files import output_path


class OwnedCopyTool:
    def __init__(self, system):
        self.system = system
        self.tool = None
        self.tool_closed = False
        self.system_closed = False

    def __getattr__(self, name):
        return getattr(self.tool, name)

    def Close(self):
        if self.tool is not None and not self.tool_closed:
            if self.tool.Close() is False: return False
            self.tool_closed = True
        if not self.system_closed:
            if self.system.Close(False) is False: return False
            self.system_closed = True
        return True


def source_state(system):
    mode = str(system.Mode)
    return dict(system_id=int(system.SystemID),file=str(system.SystemFile),mode=mode,
                configuration=int(system.MCE.CurrentConfiguration),
                lens_units=str(system.SystemData.Units.LensUnits),
                row_count=int(system.LDE.NumberOfSurfaces if mode=='Sequential' else system.NCE.NumberOfObjects))


def lens_values(q, path):
    values = dict(AssumeRadialSymmetry=q.assume_radial_symmetry,SkipSystemReversal=q.skip_system_reversal,
                  SensorWidth=q.sensor_width,SensorHeight=q.sensor_height,
                  SampleSize=q.sampling,OPTDistortionFilename=str(path))
    if q.assume_radial_symmetry: values['SamplePoints'] = q.sample_points or 21
    else: values.update(XSampling=q.x_sampling or 11,YSampling=q.y_sampling or 11)
    return values


def check_configuration(tool, requested, current):
    actual = int(tool.Configuration)
    if actual != requested and not (requested==0 and actual==current):
        raise ZemaxError('SETTING_REJECTED','Speos配置未采用请求值。',requested=requested,actual=actual,current=current)


def native_whitebox_path(value, directory):
    if not str(value or '').strip():
        raise ZemaxError('NO_RESULT_DATA','Whitebox未提供原生输出文件名。')
    path = Path(str(value))
    if not path.is_absolute(): path = directory/path
    path = path.resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ZemaxError('UNSUPPORTED_OUTPUT_LOCATION','Whitebox原生输出位置未落在请求的独立目录内。',
                         actual=str(path),output_directory=str(directory))
    return path


def run_speos_export(backend, q):
    system = backend.system
    backend._require_work()
    if q.kind == 'lens_system':
        backend._require_sequential()
        if q.configuration > system.MCE.NumberOfConfigurations:
            raise ZemaxError('INDEX_OUT_OF_RANGE','Speos导出配置越界。',configuration=q.configuration)
        target = output_path(q.path,{'.optdistortion'},q.overwrite)
        # OpticStudio 2024 R2 normalizes this native filename suffix to uppercase.
        target = target.with_suffix('.OPTDistortion')
        directory = backend.directory/('speos_input_'+uuid.uuid4().hex)
    else:
        target = None
        directory = Path(q.output_directory)
        if not directory.is_absolute() or directory.exists():
            raise ZemaxError('INVALID_OUTPUT_DIRECTORY','Whitebox需要尚不存在的绝对输出目录。')
        directory = directory.resolve()
    before = source_state(system)
    directory.mkdir(parents=True,exist_ok=False)
    copy = system.CopySystem()
    if copy is None:
        raise ZemaxError('COPY_FAILED','未能创建Speos导出的独立系统副本。')
    owned = OwnedCopyTool(copy)
    method = 'OpenExportToSpeosLensSystem' if q.kind=='lens_system' else 'OpenExportToSpeosWhitebox'
    try:
        if bool(getattr(system,'IsProjectDirectory',False)):
            backend._copy_project_resources(Path(before['file']).parent,directory)
        input_lens = directory/'input.zos'
        copy.SaveAs(str(input_lens))
        factory = getattr(copy.Tools,method,None)
        if factory is None: raise ZemaxError('UNSUPPORTED_INTERFACE','本机缺少Speos导出工厂。',native_method=method)
        owned.tool = factory()
        if owned.tool is None:
            raise ZemaxError('SPEOS_TOOL_UNAVAILABLE','Speos工厂未返回原生工具。',native_method=method)
        tool = owned.tool
        values = None
        initial_output_error = None
        if q.kind == 'lens_system':
            native_setting(backend.native,tool,'Configuration',q.configuration)
            check_configuration(tool,q.configuration,before['configuration'])
            values = lens_values(q,target)
            for name,value in values.items(): checked(backend.native,tool,name,value)
            for name,value in values.items(): check(backend.native,tool,name,value)
            target.parent.mkdir(parents=True,exist_ok=True)
        else:
            try: initial = str(tool.OutputFilename or '')
            except Exception as exc:
                initial = ''
                initial_output_error = str(exc)
            if initial.strip(): native_whitebox_path(initial,directory)
        actual = dict(kind=q.kind,requested=q.model_dump(),native=scalar_settings(tool),
                      source_system=before,copy_system_id=int(copy.SystemID),input_working_lens=str(input_lens),
                      position_unit=before['lens_units'],configuration_selection='0=current configuration' if q.kind=='lens_system' else 'copied current configuration')
        if initial_output_error is not None:actual['initial_output_unavailable']=initial_output_error
    except Exception as original:
        try: backend._release_owned(owned)
        except Exception as cleanup:
            backend.requires_reconnect = True
            error = original if isinstance(original,ZemaxError) else ZemaxError('SPEOS_SETUP_ERROR',str(original),native_type=type(original).__name__)
            error.details['cleanup_error'] = cleanup.as_dict() if isinstance(cleanup,ZemaxError) else dict(message=str(cleanup))
            raise error from original
        raise

    def collect(task):
        if not tool.Succeeded:
            details = dict(native_method=method)
            if q.kind=='whitebox': details['native_error_code']=int(tool.ErrorCode)
            raise ZemaxError('SPEOS_EXPORT_FAILED',str(tool.ErrorMessage),**details)
        if q.kind=='lens_system':
            for name,value in values.items(): check(backend.native,tool,name,value)
            check_configuration(tool,q.configuration,before['configuration'])
            path = Path(str(tool.OPTDistortionFilename)).resolve()
            version = int(tool.FileFormatVersion)
            native_result = dict(file_format_version=version)
        else:
            path = native_whitebox_path(tool.OutputFilename,directory)
            native_result = dict(native_error_code=int(tool.ErrorCode),native_output_filename=str(tool.OutputFilename))
        final_settings = scalar_settings(tool)
        if not backend._close_task_native(task):
            raise ZemaxError('CLEANUP_FAILED','Speos工具或系统副本关闭未确认。',warnings=task.get('cleanup_warnings'))
        if not path.is_file():
            raise ZemaxError('NO_RESULT_DATA','Speos报告成功但输出文件不可读取。',path=str(path),native_result=native_result)
        after = source_state(system)
        if after != before:
            backend.revision += 1
            backend.requires_reconnect = True
            backend._engineering_mapping_valid = False
            raise ZemaxError('SOURCE_MODEL_CHANGED','Speos导出期间源系统状态发生变化。',before=before,after=after)
        artifacts = [dict(kind='speos_export',path=str(path))]
        if q.kind=='whitebox':
            artifacts.extend(dict(kind='speos_support_file',path=str(p)) for p in sorted(directory.rglob('*'))
                             if p.is_file() and p.resolve()!=path and p.resolve()!=input_lens.resolve())
        return dict(kind=q.kind,path=str(path),output_directory=str(directory) if q.kind=='whitebox' else str(path.parent),
                    actual_settings=final_settings,source_system=before,source_state_after=after,
                    source_metadata_preserved=True,source_validation_scope='identity/file/mode/configuration/units/row count; independent-copy execution',
                    copy_closed=owned.system_closed,tool_closed=owned.tool_closed,
                    input_working_lens=str(input_lens),native_result=native_result,artifacts=artifacts,
                    receiver_import='pending separate Speos receiver acceptance')
    return backend._start_task('speos_export',owned,actual,collector=collect)

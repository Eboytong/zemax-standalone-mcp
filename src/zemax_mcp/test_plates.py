"""Read native test-plate reports and documented TPD resource files."""
import math
from pathlib import Path
from typing import Literal
from pydantic import field_validator, model_validator
from .schema import Request
from .errors import ZemaxError
from .data import unwrap


class TestPlateList(Request):
    kind: Literal['test_plate_list']
    catalog_file: str | None = None
    method: Literal['auto', 'native', 'file'] = 'auto'
    native_settings_file: str | None = None

    @field_validator('native_settings_file')
    @classmethod
    def cfg_filename(cls, value):
        if value is not None and (not value.strip() or not Path(value).is_absolute() or Path(value).suffix.lower() != '.cfg'):
            raise ValueError('native_settings_file须为原生CFG文件的绝对路径。')
        return value

    @field_validator('catalog_file')
    @classmethod
    def filename(cls, value):
        if value is not None and (not value.strip() or '/' in value or '\\' in value or ':' in value or not value.lower().endswith('.tpd')):
            raise ValueError('catalog_file须为Testplate目录内的TPD文件名。')
        return value

    @model_validator(mode='after')
    def file_required(self):
        if self.native_settings_file is not None and self.method == 'file':
            raise ValueError('native_settings_file要求auto或native方法。')
        if self.method == 'file' and self.catalog_file is None:
            raise ValueError('file方法要求catalog_file。')
        return self


def catalog_resources(application):
    directory = Path(str(application.ZemaxDataDir)) / 'Testplate'
    names = sorted((p.name for p in directory.glob('*') if p.is_file() and p.suffix.lower() == '.tpd'), key=str.casefold)
    return directory, names


def parse_tpd(text):
    headers, rows = [], []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith('!'):
            headers.append(line[1:].strip())
            continue
        parts = line.split()
        try:
            if len(parts) != 4:
                raise ValueError('expected four columns')
            radius, diameter = map(float, parts[1:3])
            code = int(parts[3])
            if not all(math.isfinite(x) and x > 0 for x in [radius, diameter]) or code not in [-1, 0, 1]:
                raise ValueError('invalid radius, diameter or availability code')
        except ValueError as exc:
            raise ZemaxError('INVALID_RESOURCE_DATA', 'TPD目录行格式无效。', source_line=number, raw_line=line, reason=str(exc)) from exc
        rows.append(dict(index=len(rows), plate_id=parts[0], radius_mm=radius, diameter_mm=diameter,
                         concave=code in [-1, 0], convex=code in [0, 1], availability_code=code, source_line=number))
    if not rows:
        raise ZemaxError('NO_RESULT_DATA', 'TPD目录没有样板数据。')
    return headers, rows


def parse_native(text, names):
    first = text.splitlines()[0] if text.splitlines() else ''
    selected = [name for name in names if first.casefold().endswith(name.casefold())]
    if len(selected) != 1:
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告没有可确认的TPD目录身份。', header=first)
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        fields = [s.strip() for s in line.split('\t')]
        candidate = len(fields) >= 4 and any(v.upper() == 'X' for v in fields[3:])
        if not candidate:
            if rows and line.strip():
                raise ZemaxError('INVALID_RESULT_DATA', '原生样板报告包含无法解析的数据行。', source_line=number, raw_line=line)
            continue
        try:
            radius, diameter = float(fields[1]), float(fields[2])
            if not all(math.isfinite(v) and v > 0 for v in [radius, diameter]):
                raise ValueError('nonpositive or nonfinite dimensions')
            cc = fields[3].upper() == 'X'
            cx = len(fields) > 4 and fields[4].upper() == 'X'
            if not cc and not cx:
                raise ValueError('missing availability')
        except ValueError as exc:
            raise ZemaxError('INVALID_RESULT_DATA', '原生样板报告行无效。', source_line=number, raw_line=line) from exc
        rows.append(dict(index=len(rows), plate_id=fields[0], radius_mm=radius, diameter_mm=diameter,
                         concave=cc, convex=cx, availability_code=0 if cc and cx else -1 if cc else 1, source_line=number))
    if not rows:
        raise ZemaxError('NO_RESULT_DATA', '原生样板报告没有数据行。')
    return selected[0], rows


def run_test_plates(b, q):
    b._require_sequential()
    b._require_work()
    cfg = Path(q.native_settings_file) if q.native_settings_file else None
    if cfg is not None and not cfg.is_file():
        raise ZemaxError('INVALID_RESOURCE', '原生CFG文件不存在。', path=str(cfg))
    directory, names = catalog_resources(b.native.application)
    requested = next((n for n in names if q.catalog_file and n.casefold() == q.catalog_file.casefold()), None)
    if q.catalog_file and requested is None:
        raise ZemaxError('INVALID_RESOURCE', 'TPD目录文件不存在。', requested=q.catalog_file, directory=str(directory), available=names)

    def flow(task):
        b._cancel_boundary(task)
        payload = task['payload'] = dict(analysis_kind=q.kind, actual_settings=dict(request=q.model_dump()),
            units=dict(radius='millimeters', diameter='millimeters'), series=[], artifacts=[],
            native_selection_status='AS_Default has no typed catalog selection/readback; native active catalog identified from report header')
        actual, rows = None, None
        if q.method != 'file':
            tool, original = None, None
            try:
                tool = b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM, 'TestPlateList'))
                native_settings = unwrap(tool.GetSettings())
                payload['settings_type'] = str(native_settings.GetType().FullName)
                if cfg is not None:
                    payload['native_configuration'] = dict(path=str(cfg), source='native LoadFrom', loaded=False,
                                                          adoption_source='native report catalog header')
                    if not native_settings.LoadFrom(str(cfg)):
                        raise ZemaxError('CFG_LOAD_FAILED', '原生样板配置加载被拒绝。', path=str(cfg))
                    payload['native_configuration']['loaded'] = True
                tool.Apply()
                while tool.IsRunning():
                    b._cancel_boundary(task)
                    yield
                b._cancel_boundary(task)
                result = tool.GetResults()
                path = b.directory / (task['task_id'] + '_test_plates.txt')
                payload['native_messages'] = [str(result.GetMessageAt(i).Text) for i in range(result.NumberOfMessages)]
                if not result.GetTextFile(str(path)):
                    raise ZemaxError('NO_RESULT_DATA', 'TestPlateList原生文本导出失败。')
                payload['artifacts'].append(dict(kind='native_text', path=str(path)))
                actual, rows = parse_native(path.read_text(encoding='utf-16'), names)
                payload['native_catalog_file'] = actual
                if cfg is not None:
                    payload['native_configuration']['actual_catalog_file'] = actual
            except BaseException as exc:
                original = exc
                raise
            finally:
                if tool is not None:
                    owner = dict(native=tool)
                    payload['native_closed'] = b._close_task_native(owner)
                    if not payload['native_closed']:
                        warnings = owner.get('cleanup_warnings', [])
                        if isinstance(original, ZemaxError):
                            original.details['cleanup_warnings'] = warnings
                        elif original is None:
                            raise ZemaxError('CLEANUP_FAILED', 'TestPlateList原生关闭未确认。', cleanup_warnings=warnings)
            if requested is not None and actual != requested:
                if q.method == 'native' or cfg is not None:
                    raise ZemaxError('SETTING_NOT_SUPPORTED', '原生接口不能确认请求目录的选择。', requested=requested, actual=actual, native_text=payload['artifacts'][0]['path'])
                payload['fallback_reason'] = dict(reason='native active catalog differs from requested catalog; no typed selection interface', requested=requested, actual=actual)
                rows = None
        if rows is None:
            b._cancel_boundary(task)
            path = directory / requested
            try:
                # Installed vendor resources are ASCII/Windows text; preserve local names.
                raw = path.read_bytes()
                try:
                    text = raw.decode('utf-8-sig')
                except UnicodeDecodeError:
                    text = raw.decode('mbcs')
                headers, rows = parse_tpd(text)
            except (OSError, UnicodeError) as exc:
                raise ZemaxError('RESOURCE_READ_FAILED', str(exc), path=str(path), exception_type=type(exc).__name__) from exc
            actual = requested
            payload.update(computation_method='documented_TPD_file', vendor_header=headers, resource_path=str(path))
        else:
            payload['computation_method'] = 'native_TestPlateList_text'
        payload['actual_settings'].update(catalog_file=actual, source=payload['computation_method'])
        for row in rows:
            b._cancel_boundary(task)
            task['rows'].append(row)
            if len(task['rows']) % 100 == 0:
                yield
        task['summary'] = dict(catalog_file=actual, plates=len(rows), concave=sum(r['concave'] for r in rows), convex=sum(r['convex'] for r in rows))
    return b._composite(q.kind, q.model_dump(), flow)

"""Typed entry points for the two native text reports that expose only AS_Default settings.

Both ``PrescriptionDataSettings`` and ``SurfaceDataSettings`` have no documented
typed selector: the runtime settings object is ``ZemaxUI.ZOSAPI.Analysis.AS_Default``
implementing the empty ``IAS_`` base, whose only properties are
``Analysis``/``TheDataID``/``IsValid``/``IsActiveWindow``/``Parent``. There is no
``IAS_PrescriptionData``/``IAS_SurfaceData`` in the installed interface surface and
no documented ``ModifySettings`` key for either analysis.

The prescription request can select sections from the exported native text. This
is output processing with source line attribution, separate from native settings.
The surface request retains its default native scope.

Failure layering follows the existing convention:
``NO_RESULT_DATA`` when the native task produced no text, ``INVALID_RESULT_DATA``
when the text cannot be decoded or does not carry the expected report identity.
The original text (or its byte prefix when it cannot be decoded) is always kept.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .errors import ZemaxError
from .schema import Request

REPORT_ANALYSES = {
    'prescription_data': 'PrescriptionDataSettings',
    'surface_data': 'SurfaceDataSettings',
}

SELECTION_SUPPORT = 'default_only'
SELECTION_NOTE = ('官方接口未暴露章节或面号选择（AS_Default/空 IAS_ 基类，无 IAS_PrescriptionData/'
                  'IAS_SurfaceData，无文档化 ModifySettings 键）；原生设置保持默认，处方章节输出选择单独记录来源。')

#: Report document header keys (top of every native report, before the first section).
HEADER_KEYS = {'文件', '题目', '日期', 'File', 'Title', 'Date'}

#: Section titles observed in the real Chinese report plus the documented English
#: names from the OpticStudio manual (Prescription Data, sequential/NSC). Titles are
#: matched after stripping the trailing colon; matching is case-insensitive.
PRESCRIPTION_SECTIONS = {
    '常用透镜数据': 'general_data', 'General Data': 'general_data',
    '面数据概要': 'surface_data', 'Surface Data': 'surface_data',
    '详细面数据': 'surface_detail', 'Surface Detail': 'surface_detail',
    '边缘厚度数据': 'edge_thickness', 'EdgeThickness': 'edge_thickness', 'Edge Thickness': 'edge_thickness',
    '多配置数据': 'multi_config_data', 'Multi-Config Data': 'multi_config_data',
    '求解及变量数据': 'solves_variables', 'Solves/Variables': 'solves_variables',
    '折射率数据': 'index_data', 'Index Data': 'index_data',
    '热膨胀系数数据': 'thermal_expansion_data', 'Thermal Expansion Data': 'thermal_expansion_data',
    '全局顶点坐标, 方向, 以及旋转/偏移矩阵': 'global_vertex', 'GlobalVertex': 'global_vertex',
    '全局表面曲率中心顶点': 'center_of_curvature', 'Center Of Curvature': 'center_of_curvature',
    '元件体积数据': 'element_volume', 'ElementVolume': 'element_volume',
    'F/# 数据': 'f_numbers', 'F/ Numbers': 'f_numbers', 'F/# Data': 'f_numbers',
    '主要顶点': 'cardinal_points', 'Cardinal Points': 'cardinal_points',
    '物理光学传播设置概要': 'pop_settings', 'POP Settings': 'pop_settings',
    '用过的文件': 'files_used', 'Files Used': 'files_used',
}

#: Sections documented for the prescription report (informational only: a report may
#: legitimately omit some of them, e.g. Multi-Config Data for a single configuration).
DOCUMENTED_PRESCRIPTION_SECTIONS = tuple(dict.fromkeys(PRESCRIPTION_SECTIONS.values()))
PrescriptionSection = Literal[
    'general_data', 'surface_data', 'surface_detail', 'edge_thickness',
    'multi_config_data', 'solves_variables', 'index_data', 'thermal_expansion_data',
    'global_vertex', 'center_of_curvature', 'element_volume', 'f_numbers',
    'cardinal_points', 'pop_settings', 'files_used',
]

SURFACE_SECTIONS = {
    '边缘厚度': 'edge_thickness', 'Edge Thickness': 'edge_thickness',
    '折射率': 'index', 'Index of Refraction': 'index', 'Index': 'index',
    '表面光焦 (在特定环境下)': 'power_in_situ', 'Surface Power (in situ)': 'power_in_situ',
    '表面光焦 (在空气中)': 'power_in_air', 'Surface Power (in air)': 'power_in_air',
}

_SURFACE_TITLE = re.compile(r'^(?:表面|Surface)\s*(\d+)\s*(?:数据概要|Data\s*Summary)$', re.IGNORECASE)
_POWER_ROW = re.compile(r'^(?:面|Surface)\s*(\d+)\s*:\s*(.*)$', re.IGNORECASE)
_COLON = re.compile(r'[:：]')


class PrescriptionDataReport(Request):
    """Native report with optional section selection from its exported text."""

    kind: Literal['prescription_data']
    sections: list[PrescriptionSection] | None = Field(default=None, min_length=1, max_length=15)

    @model_validator(mode='after')
    def distinct_sections(self):
        if self.sections is not None and len(set(self.sections)) != len(self.sections):
            raise ValueError('sections 不可重复。')
        return self


class SurfaceDataReport(Request):
    """Kind-only request for the native surface-data text report."""

    kind: Literal['surface_data']


def decode_native_text(raw):
    """Decode native report bytes; UTF-16 BOMs win, UTF-8 is the fallback."""
    if not isinstance(raw, (bytes, bytearray)):
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告内容不是字节流。', native_type=type(raw).__name__)
    data = bytes(raw)
    if not data:
        raise ZemaxError('NO_RESULT_DATA', '原生报告返回空文本。', native_bytes=0)
    for bom, encoding in ((b'\xff\xfe', 'utf-16'), (b'\xfe\xff', 'utf-16'), (b'\xef\xbb\xbf', 'utf-8-sig')):
        if data.startswith(bom):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError as exc:
                raise ZemaxError('INVALID_RESULT_DATA', '原生报告文本无法按声明的编码解码。',
                                 encoding=encoding, native_bytes=len(data),
                                 native_prefix=data[:64].hex(), native_error=str(exc)) from exc
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        pass
    else:
        # A BOM-less UTF-16 export decodes as UTF-8 with interleaved NULs; native report
        # text never contains NUL, so that pattern is treated as UTF-16LE instead.
        if '\x00' not in text:
            return text
    try:
        return data.decode('utf-16-le')
    except UnicodeDecodeError as exc:
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告文本无法解码。',
                         native_bytes=len(data), native_prefix=data[:64].hex(),
                         native_error=str(exc)) from exc


def _title_of(line):
    """Return the section-style title of a column-0 ``title:`` line, else None."""
    if not line or line[:1].isspace():
        return None
    stripped = line.strip()
    if not stripped or stripped[-1] not in ':：':
        return None
    title = stripped[:-1].strip()
    if not title or _COLON.search(title):
        return None
    return title


def _normalise(title):
    return ' '.join(title.split())


def section_title(title, table):
    """Map a report title to its canonical section id, or None when unrecognised."""
    if title is None:
        return None
    key = _normalise(title)
    if key in table:
        return table[key]
    folded = key.casefold()
    for name, identifier in table.items():
        if _normalise(name).casefold() == folded:
            return identifier
    return None


def split_sections(text, table):
    """Split a report into document header lines and recognised sections.

    Only column-0 ``title:`` lines whose title is in ``table`` start a section. Every
    line is retained: sections carry their own ``lines`` and the caller also keeps the
    complete ``lines`` list. Titles that look like sections but are not in ``table``
    are reported as ``candidate_titles`` for audit; they are never dropped.
    """
    lines = text.splitlines()
    header, sections, candidates = [], [], []
    current = None
    for number, line in enumerate(lines, 1):
        title = _title_of(line)
        identifier = section_title(title, table) if title is not None else None
        if identifier is not None:
            current = dict(index=len(sections), section_id=identifier, title=title,
                           start_line=number, end_line=number, lines=[])
            sections.append(current)
            continue
        if title is not None and _normalise(title) not in HEADER_KEYS and current is not None:
            candidates.append(dict(line=number, title=title))
        if current is None:
            header.append(line)
        else:
            current['lines'].append(line)
            current['end_line'] = number
    return header, sections, candidates


def document_header(header_lines):
    """Extract the native report document identity (file/title/date) from header lines."""
    document = {}
    for line in header_lines:
        if not line or line[:1].isspace():
            continue
        match = re.match(r'^([^:：]+)\s*[:：]\s*(.*)$', line.strip())
        if not match:
            continue
        key, value = match.group(1).strip(), match.group(2).strip()
        if key in HEADER_KEYS:
            document[key] = value
    return document


def _report_title(header_lines):
    for line in header_lines:
        stripped = line.strip()
        if stripped and _title_of(line) is None and not _COLON.search(stripped):
            return stripped
    return None


def _number(text, field, line_number, raw_line):
    value = text.strip()
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告数值字段无法解析。',
                         field=field, source_line=line_number, raw_line=raw_line) from exc
    if not math.isfinite(number):
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告数值字段非有限。',
                         field=field, source_line=line_number, raw_line=raw_line)
    return number


def _field_value(line):
    """Split ``key : value`` retaining the original value text."""
    match = re.match(r'^\s*([^:：]+?)\s*[:：]\s*(.*)$', line)
    if not match:
        return None, None
    return match.group(1).strip(), match.group(2).strip()


PRESCRIPTION_TITLES = ('系统/详细数据', 'System/Detail Data', 'System/Detail data', 'Prescription Data')


def _prescription_title_ok(title):
    if not title:
        return False
    key = ' '.join(title.split())
    return any(key.casefold() == candidate.casefold() for candidate in PRESCRIPTION_TITLES)


def parse_prescription_report(text):
    """Parse the native prescription report into typed sections.

    The report identity is confirmed from its documented title before the sections are
    trusted: another native report that happens to use familiar section names is
    rejected instead of being reported as a prescription.
    """
    header, sections, candidates = split_sections(text, PRESCRIPTION_SECTIONS)
    lines = text.splitlines()
    if not any(line.strip() for line in lines):
        raise ZemaxError('NO_RESULT_DATA', '原生处方报告返回空文本。', native_chars=len(text))
    title = _report_title(header)
    if not _prescription_title_ok(title):
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告身份不符：标题不是系统说明文本报告。',
                         report_title=title, expected_titles=list(PRESCRIPTION_TITLES),
                         native_lines=len(lines), native_preamble=[line for line in lines[:20]])
    if not sections:
        raise ZemaxError('INVALID_RESULT_DATA', '原生处方报告没有可识别的章节标题。',
                         report_title=title, native_lines=len(lines),
                         candidate_titles=[c['title'] for c in candidates],
                         native_preamble=[line for line in lines[:20]])
    present = [section['section_id'] for section in sections]
    return dict(
        kind='prescription_data',
        report_title=_report_title(header),
        document=document_header(header),
        section_count=len(sections),
        section_ids=present,
        sections=[dict(index=s['index'], section_id=s['section_id'], title=s['title'],
                       start_line=s['start_line'], end_line=s['end_line'], lines=s['lines'])
                  for s in sections],
        documented_sections=list(DOCUMENTED_PRESCRIPTION_SECTIONS),
        missing_documented_sections=[name for name in DOCUMENTED_PRESCRIPTION_SECTIONS if name not in present],
        duplicate_sections=sorted({name for name in present if present.count(name) > 1}),
        candidate_titles=candidates,
        lines=[dict(line=number, text=line) for number, line in enumerate(lines, 1)],
        line_count=len(lines),
        section_detection='documented title table (observed native Chinese titles + manual English names)',
        raw_text_retained=True,
        selection_support=SELECTION_SUPPORT,
    )


def parse_surface_data_report(text):
    """Parse the native surface-data report, including the adopted surface identity."""
    header, sections, candidates = split_sections(text, SURFACE_SECTIONS)
    lines = text.splitlines()
    if not any(line.strip() for line in lines):
        raise ZemaxError('NO_RESULT_DATA', '原生表面数据报告返回空文本。', native_chars=len(text))
    title_surface = None
    for line in lines:
        match = _SURFACE_TITLE.match(line.strip())
        if match:
            title_surface = int(match.group(1))
            break
    if title_surface is None:
        raise ZemaxError('INVALID_RESULT_DATA', '原生表面数据报告缺少面号标题，无法确认采用身份。',
                         native_lines=len(lines), native_preamble=[line for line in lines[:20]])
    fields, unit, glass = {}, None, None
    index_rows, power = [], {'power_in_situ': None, 'power_in_air': None}
    power_components = {name: [] for name in power}
    # Header key lines (lens units, thickness, diameter) precede the first section, so
    # the whole document is walked in order rather than only the section bodies.
    ordered = [(None, number, line) for number, line in enumerate(header, 1)]
    for section in sections:
        for offset, line in enumerate(section['lines'], 1):
            ordered.append((section['section_id'], section['start_line'] + offset, line))
    for section_id, number, line in ordered:
        key, value = _field_value(line)
        if key is None or key in HEADER_KEYS:
            continue
        if key in ('透镜单位', 'Lens units', 'Lens Units'):
            unit = value
            continue
        if section_id == 'index' and key in ('玻璃', 'Glass'):
            glass = value
            continue
        if section_id in power:
            match = _POWER_ROW.match(line.strip())
            if match:
                power_components[section_id].append(dict(surface=int(match.group(1)),
                                         value=_number(match.group(2), section_id, number, line),
                                         value_text=match.group(2).strip()))
            continue
        if key not in fields:
            fields[key] = dict(value_text=value, line=number, section_id=section_id)
    for section in sections:
        if section['section_id'] != 'index':
            continue
        for offset, line in enumerate(section['lines'], 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            cells = stripped.split()
            if len(cells) != 3 or not cells[0].isdigit():
                continue
            index_rows.append(dict(
                number=int(cells[0]),
                wavelength_um=_number(cells[1], 'wavelength_um', section['start_line'] + offset, line),
                index=_number(cells[2], 'index', section['start_line'] + offset, line),
                wavelength_text=cells[1], index_text=cells[2]))
    for name, components in power_components.items():
        # Element reports list both bounding faces in each power section.
        # Preserve every component and select the face named by the report title.
        power[name] = next((row for row in components if row['surface'] == title_surface),
                           components[-1] if components else None)
    power_surfaces = [block['surface'] for block in power.values() if block]
    conflicting = [value for value in power_surfaces if value != title_surface]
    if conflicting:
        # The title and the power blocks disagree about the reported surface: the adopted
        # identity cannot be confirmed, so the report is rejected with the parsed result
        # kept in the error details for triage.
        raise ZemaxError('INVALID_RESULT_DATA', '表面数据报告面号身份冲突：标题面号与表面光焦块面号不一致。',
                         title_surface=title_surface, power_surfaces=power_surfaces,
                         native_lines=len(lines),
                         native_preamble=[line for line in lines[:20]],
                         partial=dict(surface=title_surface, unit=unit, glass=glass, fields=fields,
                                      index_rows=index_rows, surface_power=power,
                                      surface_power_components=power_components,
                                      section_ids=[section['section_id'] for section in sections],
                                      lines=[dict(line=number, text=line)
                                             for number, line in enumerate(lines, 1)]))
    return dict(
        kind='surface_data',
        report_title=_report_title(header),
        document=document_header(header),
        surface=title_surface,
        surface_source='report title',
        unit=unit,
        glass=glass,
        fields=fields,
        index_rows=index_rows,
        surface_power=power,
        surface_power_components=power_components,
        identity_check=dict(
            title_surface=title_surface,
            power_surfaces=power_surfaces,
            consistent=all(value == title_surface for value in power_surfaces) if power_surfaces else None,
            basis='title surface number versus the surface numbers of the power blocks'),
        sections=[dict(index=s['index'], section_id=s['section_id'], title=s['title'],
                       start_line=s['start_line'], end_line=s['end_line'], lines=s['lines'])
                  for s in sections],
        candidate_titles=candidates,
        lines=[dict(line=number, text=line) for number, line in enumerate(lines, 1)],
        line_count=len(lines),
        section_detection='documented title table (observed native Chinese titles + manual English names)',
        raw_text_retained=True,
        selection_support=SELECTION_SUPPORT,
    )


PARSERS = {'prescription_data': parse_prescription_report, 'surface_data': parse_surface_data_report}


def parse_report(kind, text):
    """Dispatch to the report parser; unknown kinds are a programming error."""
    try:
        parser = PARSERS[kind]
    except KeyError as exc:
        raise ZemaxError('INVALID_ARGUMENT', '未知的原生文本报告类型。', kind=kind) from exc
    return parser(text)


def native_text_path(result):
    artifacts = result.get('artifacts', [])
    path = next((a['path'] for a in artifacts if a.get('kind') == 'native_text'), None)
    if path is None:
        raise ZemaxError('NO_RESULT_DATA', '原生报告未返回原生文本。',
                         artifacts=artifacts, native_messages=result.get('native_messages', []))
    return path


def select_prescription_sections(parsed, text, requested, native_text):
    """Select exact native line intervals in document order, retaining identity."""
    available = parsed['section_ids']
    missing = [name for name in requested if name not in available]
    ambiguous = [name for name in requested if name in parsed['duplicate_sections']]
    if missing or ambiguous:
        raise ZemaxError('INVALID_RESULT_DATA', '原生处方报告未唯一包含所选章节。',
                         requested_sections=requested, available_sections=available,
                         missing_sections=missing, ambiguous_sections=ambiguous,
                         native_text=str(native_text), source='native_report_section_selection')
    selected = [section for section in parsed['sections'] if section['section_id'] in requested]
    # splitlines(keepends=True) preserves every original title, blank and line ending.
    original = text.splitlines(keepends=True)
    header_end = parsed['sections'][0]['start_line'] - 1
    rows = [dict(line=i + 1, section_id=None, text=parsed['lines'][i]['text'])
            for i in range(header_end)]
    indices = list(range(header_end))
    for section in selected:
        for i in range(section['start_line'] - 1, section['end_line']):
            indices.append(i)
            rows.append(dict(line=i + 1, section_id=section['section_id'],
                             text=parsed['lines'][i]['text']))
    output = Path(native_text).with_name(Path(native_text).stem + '.selected.txt')
    try:
        with output.open('w', encoding='utf-8', newline='') as stream:
            stream.write(''.join(original[i] for i in indices))
    except OSError as exc:
        raise ZemaxError('EXPORT_FAILED', '所选处方章节写出失败。',
                         path=str(output), native_text=str(native_text),
                         native_error=str(exc), source='native_report_section_selection') from exc
    return dict(
        selected_sections=selected, selected_section_ids=[s['section_id'] for s in selected],
        selected_text=str(output), rows=rows, row_count=len(rows),
        selection=dict(source='native_report_section_selection', requested=list(requested),
                       actual=[s['section_id'] for s in selected], order='native_document',
                       header_included=True, native_settings_modified=False,
                       source_line_numbers='one-based original native report'),
    )


def report_payload(result, kind, sections=None):
    """Read, decode and parse the native report; the original text is always retained.

    Native messages and the native text path are attached to every failure so the
    existing error layering stays uniform with the other report readers.
    """
    path = native_text_path(result)
    messages = result.get('native_messages', [])
    artifacts = result.get('artifacts', [])
    try:
        with open(path, 'rb') as handle:
            raw = handle.read()
    except OSError as exc:
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告文本读取失败。',
                         native_text=str(path), analysis_kind=kind, native_messages=messages,
                         native_error=str(exc), artifacts=artifacts) from exc
    try:
        text = decode_native_text(raw)
        parsed = parse_report(kind, text)
        if sections is not None:
            parsed.update(select_prescription_sections(parsed, text, sections, path))
    except ZemaxError as exc:
        exc.details.setdefault('native_text', str(path))
        exc.details.setdefault('native_messages', messages)
        exc.details.setdefault('analysis_kind', kind)
        raise
    result.update(parsed)
    result['analysis_kind'] = kind
    result['native_text'] = str(path)
    result['structured_data_available'] = True
    result['acceptance_scope'] = 'default_report_only'
    result['selection_scope'] = dict(status='blocked', supported=SELECTION_SUPPORT,
                                     reason=SELECTION_NOTE,
                                     unlock_condition='官方章节或面号选择接口，以及采用值的可靠回读')
    result['diagnostic_semantics'] = ('task success indicates report generation; the report describes the '
                                      'native default scope because no typed selector is available')
    if sections is not None:
        result['artifacts'].append(dict(kind='selected_text', path=result['selected_text']))
        result['acceptance_scope'] = 'exported_report_sections'
        result['selection_support'] = 'exported_report_sections'
        result['diagnostic_semantics'] = 'selected native text sections; original native settings and complete report retained'
    return result


def run_text_report(backend, q):
    """Create the native report analysis, read back its settings and parse the text."""
    from .imaging import new_analysis
    from .analyses import scalar_settings
    backend._require_work()
    name = REPORT_ANALYSES[q.kind]
    tool = new_analysis(backend, name)
    if tool is None:
        raise ZemaxError('NATIVE_INTERFACE_UNAVAILABLE', '原生文本报告工厂未创建分析。', analysis=name)
    try:
        actual = scalar_settings(tool.GetSettings())
        if actual.get('unavailable_fields'):
            raise ZemaxError('SETTING_UNAVAILABLE', '原生报告基础设置回读失败。',
                             unavailable_fields=actual['unavailable_fields'])
        settings = dict(kind=q.kind, requested=q.model_dump(), native=actual,
                        analysis=name,
                        settings_source='AS_Default/base IAS_; no documented section or surface selector',
                        selection_support=SELECTION_SUPPORT,
                        selection_note=SELECTION_NOTE)
        sections = getattr(q, 'sections', None)
        if sections is not None:
            settings['output_selection'] = dict(source='native_report_section_selection',
                                              requested=list(sections), native_settings_modified=False)
    except Exception as exc:
        holder = dict(native=tool)
        if not backend._close_task_native(holder):
            failure = exc if isinstance(exc, ZemaxError) else ZemaxError('NATIVE_ERROR', str(exc))
            failure.details['cleanup_warnings'] = holder.get('cleanup_warnings', [])
            if failure is not exc:
                raise failure from exc
        raise
    def collect(task):
        result = report_payload(backend._collect_general_analysis(task), q.kind, sections)
        if sections is not None:
            settings['output_selection']['actual'] = result['selected_section_ids']
        return result

    return backend._start_task(q.kind, tool, settings, analysis=True, collector=collect)

"""Shared semantic metadata for saved series, figures and reports."""
import csv


def series_axes(series):
    units = series.get('value_units') or []
    return dict(x=dict(label=series.get('x_label'), unit=series.get('x_unit') or series.get('frequency_unit')),
                y=[dict(label=label, unit=units[i] if i < len(units) else series.get('y_unit'))
                   for i, label in enumerate(series.get('labels', []))])


def grid_axes(grid):
    return {axis: dict(label=grid.get(axis+'_label'), unit=grid.get(axis+'_unit'))
            for axis in ('x', 'y', 'value')}


def axis_caption(axis, default):
    label, unit = axis.get('label'), axis.get('unit')
    return f'{label if label not in (None, "", "None") else default} ({unit or "单位未知"})'


def result_metadata(result):
    task = result.get('task') or {}
    context = result.get('context') or task.get('context') or {}
    settings = task.get('settings') or {}
    provenance = result.setdefault('provenance', dict(
        source_task_id=task.get('task_id'), session_id=context.get('session_id'),
        model_revision=context.get('model_revision'), calculation_source=(result.get('source') or result.get('computation_method') or
            ('native_opticstudio' if task.get('kind') in {'fft_mtf', 'spot'} else None)),
        actual_settings=result.get('actual_settings', settings.get('actual')),
        settings_record=bool(settings)))
    for series in result.get('series', []):
        series.setdefault('axes', series_axes(series))
        series.setdefault('calculation_source', series.get('source') or provenance['calculation_source'])
    for grid in result.get('grids', []):
        grid.setdefault('axes', grid_axes(grid))
        grid.setdefault('calculation_source', grid.get('source') or provenance['calculation_source'])
    for artifact in result.get('artifacts', []):
        artifact.setdefault('source_task_id', provenance.get('source_task_id'))
        artifact.setdefault('model_revision', provenance.get('model_revision'))
        artifact.setdefault('calculation_source', artifact.get('image_source') or provenance.get('calculation_source'))
        if artifact.get('kind') == 'series_csv':
            artifact.setdefault('axes', [s['axes'] for s in result.get('series', [])])
            artifact.setdefault('actual_settings', provenance.get('actual_settings'))
    return result


def write_series_csv(path, series_list):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['series', 'description', 'x_label', 'x_unit', 'x_value', 'y_label', 'y_unit', 'y_value'])
        for series in series_list:
            axes = series.get('axes') or series_axes(series)
            for x, values in zip(series['x'], series['y'], strict=True):
                for axis, y in zip(axes['y'], values, strict=True):
                    writer.writerow([series['series'], series.get('description'), axes['x']['label'],
                                     axes['x']['unit'], x, axis['label'], axis['unit'], y])

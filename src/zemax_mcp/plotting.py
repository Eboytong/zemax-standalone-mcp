"""Single-image exports from saved data, with explicit rendering provenance."""
import math
import shutil
from pathlib import Path
from .errors import ZemaxError
from .result_metadata import axis_caption, grid_axes, series_axes


def _native_images(result):
    return [item for item in result.get('artifacts', []) if item.get('kind') == 'native_image']


def _intercept_plots(result):
    task = result.get('task', {})
    settings = task.get('settings', {})
    if task.get('kind') != 'batch_ray_trace' or settings.get('ray_type') != 'Real':
        return []
    fields = {}
    for row in result.get('rows', []):
        ray = row.get('input', {})
        position = row.get('position')
        if (row.get('state') != 'succeeded' or row.get('vignette_code') != 0 or
                not {'hx', 'hy', 'wavelength'} <= ray.keys() or not position or
                len(position) < 2 or not all(math.isfinite(v) for v in position[:2])):
            continue
        field = (ray['hx'], ray['hy'])
        points = fields.setdefault(field, [])
        points.append(dict(x=position[0], y=position[1], wavelength=ray['wavelength']))
    units = result.get('summary', {}).get('position_unit') or result.get('context', {}).get('lens_units') or 'lens units'
    target_surface = settings.get('target_surface')
    return [dict(field=list(field), unit=units, points=points, target_surface=target_surface)
            for field, points in sorted(fields.items())]


def _plot_items(result):
    items = [('series', item) for item in result.get('series', [])]
    items.extend(('grid', item) for item in result.get('grids', []))
    items.extend(('scatter', item) for item in result.get('scatter', []) if item.get('points'))
    items.extend(('ray_intercepts', item) for item in _intercept_plots(result))
    if not items:
        rows = [row for row in result.get('rows', []) if row.get('metrics')]
        if rows:
            items.append(('metrics', rows))
    return items


def image_exports(result):
    """Describe renderable outputs before result pagination strips point data."""
    images = _native_images(result)
    items = _plot_items(result)
    sources = [source for source, available in [('native', images), ('data_plot', items)] if available]
    response = dict(available_sources=sources, native_images=images, data_plot_items=len(items))
    if not images:
        response['native_unavailable_reason'] = '任务未保存原生图像，Standalone 通用分析接口提供数据和文本。'
        if items:
            response['alternative'] = dict(capability_id='tool:export_analysis_image', source='data_plot')
        elif result.get('task', {}).get('kind') == 'spot':
            response['alternative'] = dict(capability_id='tool:run_batch_ray_trace', next_capability_id='tool:export_analysis_image', source='data_plot')
    return response


def export_image(result,request,path):
    if request.source=="native":
        images=_native_images(result)
        if not images:
            metadata = image_exports(result)
            raise ZemaxError('UNSUPPORTED_NATIVE_IMAGE', metadata['native_unavailable_reason'], **metadata)
        if request.item>=len(images):raise ZemaxError("INDEX_OUT_OF_RANGE","原生图片编号越界。")
        source=Path(images[request.item]["path"])
        if not source.is_file():raise ZemaxError("MISSING_ARTIFACT","原生图片不存在。",path=str(source))
        path.parent.mkdir(parents=True,exist_ok=True)
        if source.resolve()!=path:
            if source.suffix.lower()==path.suffix.lower():shutil.copy2(source,path)
            else:
                try:from PIL import Image
                except ImportError as exc:raise ZemaxError('MISSING_DEPENDENCY','原生图片格式转换需要reports依赖。')from exc
                with Image.open(source)as bitmap:bitmap.save(path)
        return dict(image_source="native",source_file=str(source),plotting_settings=None,
            artifacts=[dict(kind="native_image",path=str(path),image_source="native")])
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:raise ZemaxError("MISSING_DEPENDENCY","绘图需要项目reports依赖。") from exc
    items=_plot_items(result)
    if not items:raise ZemaxError("NO_PLOTTABLE_DATA","结果没有可绘制的曲线、网格、散点或指标。")
    if request.item>=len(items):raise ZemaxError("INDEX_OUT_OF_RANGE","绘图数据编号越界。",count=len(items))
    kind,data=items[request.item]
    plot_settings=dict(item=request.item,data_kind=kind,width=request.width,height=request.height)
    with plt.rc_context({"font.family":"Microsoft YaHei","axes.unicode_minus":False}):
        fig,ax=plt.subplots(figsize=(request.width/100,request.height/100),dpi=100,layout="constrained")
        try:
            if kind=="series":
                for i,label in enumerate(data["labels"]):
                    if data.get('plot_kind')=='bar':
                        width=.8/len(data['labels'])
                        ax.bar([x-.4+width*(i+.5) for x in data['x']],[row[i] for row in data['y']],width=width,label=label)
                    else:ax.plot(data['x'],[row[i] for row in data['y']],label=label,marker='o' if data.get('point_labels') else None)
                if data.get('plot_kind')=='bar':
                    ax.set_xticks(data['x'],data.get('tick_labels',data['x']))
                    ax.set_frame_on(not data.get('suppress_frame',False))
                    plot_settings.update(plot_kind='bar',suppress_frame=data.get('suppress_frame',False))
                axes = data.get('axes') or series_axes(data)
                plot_settings.update(axes=axes, calculation_source=data.get('calculation_source'))
                ax.set(xlabel=axis_caption(axes['x'], 'X'), title=data.get('description',''));ax.legend();ax.grid(alpha=.25)
                if data.get('y_label'):ax.set_ylabel(axis_caption(dict(label=data['y_label'], unit=data.get('y_unit')), 'Y'))
                if data.get('axis_limits'):
                    ax.set_xlim(*data['axis_limits']);ax.set_ylim(*data['axis_limits'])
                    plot_settings['axis_limits']=data['axis_limits']
                if data.get('y_limits'):
                    ax.set_ylim(*data['y_limits']);plot_settings['y_limits']=data['y_limits']
                if data.get('aspect'):
                    ax.set_aspect(data['aspect'],adjustable='box');plot_settings['aspect']=data['aspect']
                for i,(x,y,label) in enumerate(zip(data['x'],data['y'],data.get('point_labels',[]))):
                    ax.annotate(label,(x,y[0]),xytext=(4,6 if i%2==0 else -12),textcoords='offset points')
            elif kind=="grid":
                values=np.asarray([[float("nan") if v is None else v for v in row] for row in data["values"]])
                extent=[data["min_x"]-.5*data["dx"],data["min_x"]+(data["nx"]-.5)*data["dx"],data["min_y"]-.5*data["dy"],data["min_y"]+(data["ny"]-.5)*data["dy"]]
                image=ax.imshow(values,origin="lower",extent=extent,aspect="auto")
                axes = data.get('axes') or grid_axes(data)
                ax.set(xlabel=axis_caption(axes['x'], 'X'), ylabel=axis_caption(axes['y'], 'Y'), title=data.get('description',''))
                fig.colorbar(image, ax=ax, label=axis_caption(axes['value'], '数值'))
                plot_settings.update(axes=axes, calculation_source=data.get('calculation_source'))
                plot_settings.update(extent=extent,origin="lower",array_order="values[y][x]",x_unit=data.get("x_unit"),y_unit=data.get("y_unit"),value_unit=data.get("value_unit"))
            elif kind=="scatter":
                points=data["points"]
                if any("value" in p for p in points):
                    image=ax.scatter([p["x"] for p in points],[p["y"] for p in points],c=[p.get("value",0) for p in points])
                    fig.colorbar(image,ax=ax)
                else:ax.scatter([p["x"] for p in points],[p["y"] for p in points])
                ax.set(xlabel=data.get("x_label","X"),ylabel=data.get("y_label","Y"))
                if data.get("x_axis_direction")=="decreasing_left_to_right":ax.invert_xaxis()
            elif kind == 'ray_intercepts':
                points = data['points']
                for wavelength in sorted({point['wavelength'] for point in points}):
                    selected = [point for point in points if point['wavelength'] == wavelength]
                    ax.scatter([point['x'] for point in selected], [point['y'] for point in selected],
                               s=12, label=f'Wavelength #{wavelength}')
                hx, hy = data['field']
                unit = data['unit']
                target_surface = data['target_surface']
                title = 'Ray intercepts' if target_surface is None else f'Surface {target_surface} ray intercepts'
                ax.set(title=f'{title} · Hx={hx:g}, Hy={hy:g}', xlabel=f'X ({unit})', ylabel=f'Y ({unit})', aspect='equal')
                ax.legend()
                ax.grid(alpha=.25)
                plot_settings.update(field=data['field'], position_unit=unit, point_count=len(points))
                if target_surface is not None:
                    plot_settings['target_surface'] = target_surface
            else:
                for key in dict.fromkeys(m["key"] for row in data for m in row["metrics"]):
                    selected=[(r.get("index",i),m) for i,r in enumerate(data) for m in r["metrics"] if m["key"]==key]
                    ax.plot([x for x,m in selected],[m["value"] for x,m in selected],marker="o",label=key+" ("+str(selected[0][1].get("unit",""))+")")
                ax.set_xlabel("结果行号");ax.legend();ax.grid(alpha=.25)
            task_kind = result.get('task', {}).get('kind')
            if task_kind == 'fft_mtf' or kind == 'ray_intercepts':
                plot_settings['data_source'] = 'OpticStudio FFT MTF' if task_kind == 'fft_mtf' else 'OpticStudio batch ray trace'
                fig.supxlabel(f"{plot_settings['data_source']} · rendered from data", fontsize=8)
            path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=100)
        finally:plt.close(fig)
    return dict(image_source="data_plot",plotting_settings=plot_settings,
        artifacts=[dict(kind="plot",path=str(path),image_source="data_plot")])

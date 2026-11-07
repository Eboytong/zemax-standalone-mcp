"""Installed extended-scene analyses with checked settings and RGB grids."""
import math
import uuid
from pathlib import PurePath, Path
from .analyses import scalar_settings, native_setting
from .data import unwrap, dotnet_array
from .detectors import check_setting_value
from .errors import ZemaxError

IDS={'image_simulation':'ImageSimulation','geometric_image':'GeometricImageAnalysis',
     'geometric_bitmap_image':'GeometricBitmapImageAnalysis',
     'fft_line_edge_spread':'FftPsfLineEdgeSpread', 'geometric_line_edge_spread':'GeometricLineEdgeSpread',
     'extended_source_encircled_energy':'ExtendedSourceEncircledEnergy'}
LIMIT = 4_000_000
EXTRA = {
    'fft_line_edge_spread': dict(sampling='SampleSize', spread='Spread', data_type='Type', use_coherent_psf='UseCoherentPSF', use_polarization='UsePolarization', plot_scale='PlotScale'),
    'geometric_line_edge_spread': dict(sampling='SampleSize', data_type='Type', use_polarization='UsePolarization', radius_maximum='RadiusMaximum'),
    'extended_source_encircled_energy': dict(image_name='ImageName', data_type='Type', reference='ReferTo', rays_x1000='RaysX1000', multiply_by_diffraction_limit='MultiplyByDiffractionLimit', remove_vignetting_factors='RemoveVignettingFactors', use_dashes='UseDashes', use_polarization='UsePolarization', maximum_distance='MaximumDistance', field_size='FieldSize', rotation='Rotation'),
}

def new_analysis(backend, analysis_id):
    analyses=backend.system.Analyses
    factory=getattr(analyses, 'New_Analysis_SettingsFirst', analyses.New_Analysis)
    return factory(backend.native.enum(backend.native.api.Analysis.AnalysisIDM, analysis_id))


def resource_names(backend, kind):
    analysis_kind = 'image_simulation' if kind == 'image_simulation_files' else 'geometric_image'
    tool = new_analysis(backend, IDS[analysis_kind])
    owner = {'native': tool}
    try:
        s = unwrap(tool.GetSettings())
        return [str(x) for x in (s.GetInputFileNames() if analysis_kind == 'image_simulation' else s.GetFileNames())]
    finally:
        if not backend._close_task_native(owner):
            raise ZemaxError('RESOURCE_CLOSE_FAILED', '图像资源查询未能关闭原生分析。', cleanup_warnings=owner.get('cleanup_warnings', []))


def configure_extra(backend, s, q):
    requested = {name: getattr(q, key) for key, name in EXTRA[q.kind].items()}
    if q.kind == 'extended_source_encircled_energy':
        available = resource_names(backend, 'geometric_image_files')
        matches = [x for x in available if x.casefold() == q.image_name.casefold() and PurePath(x).suffix.lower() in {'.ima', '.bim'}]
        if len(matches) != 1:
            raise ZemaxError('INVALID_RESOURCE', '扩展源图像须从原生IMA/BIM资源中选择。', requested=q.image_name, available=available)
        requested['ImageName'] = matches[0]
    select(s.Field, 'Field', q.field)
    select(s.Wavelength, 'Wavelength', q.wavelength)
    if hasattr(q, 'surface'):
        select(s.Surface, 'Surface', q.surface if q.surface is not None else backend.system.LDE.NumberOfSurfaces - 1)
    for name, value in requested.items():
        checked(backend.native, s, name, value)
    for name, value in requested.items():
        check(backend.native, s, name, value)
    result = final_settings(s, q)
    if hasattr(q, 'surface'):
        check_setting_value('Surface', q.surface if q.surface is not None else backend.system.LDE.NumberOfSurfaces - 1, int(s.Surface.GetSurfaceNumber()))
    return result


def select(selector, name, number):
    getattr(selector, 'Set' + name + 'Number')(number)
    check_setting_value(name, number, int(getattr(selector, 'Get' + name + 'Number')()))


def final_settings(s, q):
    actual = scalar_settings(s)
    if actual.get('unavailable_fields'):
        raise ZemaxError('SETTING_UNAVAILABLE', '图像分析设置读取失败。', details=actual['unavailable_fields'])
    # Recheck selectors after all dependent settings have been applied.
    check_setting_value('Field', q.field, int(s.Field.GetFieldNumber()))
    if q.kind != 'image_simulation':
        check_setting_value('Wavelength', q.wavelength, int(s.Wavelength.GetWavelengthNumber()))
    actual['wavelength_selection'] = q.wavelength
    return dict(kind=q.kind, requested=q.model_dump(), native=actual)

SIM=dict(input_file='InputFile',field_height='FieldHeight',flip_source='FlipSource',rotation_source='RotationSource',oversampling='Oversampling',guard_band='GuardBand',pupil_sampling='PupilSampling',image_sampling='ImageSampling',aberrations='Aberrations',psf_x_points='PSFXPoints',psf_y_points='PSFYPoints',use_polarization='UsePolarization',apply_fixed_apertures='ApplyFixedApertures',use_relative_illumination='UseRelativeIllumination',show_as='ShowAs',reference='Reference',flip_image='FlipImage',pixel_size='PixelSize',x_pixels='XPixels',y_pixels='YPixels',suppress_frame='SuppressFrame')
GEO=dict(input_file='File',field_size='FieldSize',image_size='ImageSize',rotation='Rotation',rays_x1000='RaysX1000',show_as='ShowAs',source='Source',number_of_pixels='NumberOfPixels',na='NA',total_watts='TotalWatts',parity='Parity',reference='Reference',use_symbols='UseSymbols',use_polarization='UsePolarization',remove_vignetting_factors='RemoveVignettingFactors',scatter_rays='ScatterRays',delete_vignetted='DeleteVignetted',use_pixel_interpolation='UsePixelInterpolation',row_column_number='RowColumnNumber')

def checked(native,s,name,value):
    native_setting(native,s,name,value)
    check(native,s,name,value)

def check(native,s,name,value):
    actual=getattr(s,name);prop=s.GetType().GetProperty(name)
    if prop.PropertyType.IsEnum:
        if not actual.Equals(native.enum(prop.PropertyType,value)):
            raise ZemaxError('SETTING_REJECTED','图像分析枚举未采用。',setting=name,requested=value,actual=str(actual))
    else:check_setting_value(name,value,actual)

def configure(backend,s,q):
    if q.kind in EXTRA:return configure_extra(backend,s,q)
    if q.kind=='geometric_bitmap_image' and not callable(getattr(s,'GetFileNames',None)):
        raise ZemaxError('UNSUPPORTED_INTERFACE','本机几何位图分析未公开专题设置接口。',
            kind=q.kind,analysis_id=IDS[q.kind],runtime_settings_type=str(s.GetType().FullName),
            missing_method='GetFileNames',next_action='Inspect native CFG settings adoption and a formal result export before enabling this request.')
    available=[str(x)for x in (s.GetInputFileNames()if q.kind=='image_simulation'else s.GetFileNames())]
    matches=[name for name in available if name.casefold()==q.input_file.casefold()]
    extensions={'.bmp','.jpg','.png','.ima','.bim'}if q.kind=='image_simulation'else {'.ima','.bim'}
    if len(matches)!=1 or PurePath(q.input_file).suffix.lower()not in extensions:
        raise ZemaxError('INVALID_RESOURCE','输入图像须从当前原生Images资源列表中选择。',requested=q.input_file,available=available)
    mapping=SIM if q.kind=='image_simulation'else GEO
    requested={name:matches[0]if key=='input_file'else getattr(q,key)for key,name in mapping.items()}
    # Clear persistent native output destinations; output is retained through task artifacts.
    checked(backend.native,s,'OutputFile'if q.kind=='image_simulation'else 'SaveAsBIMFile','')
    s.Field.SetFieldNumber(q.field)
    check_setting_value('Field',q.field,int(s.Field.GetFieldNumber()))
    if q.kind=='image_simulation':
        if q.wavelength=='RGB':s.SetWavelengthRGB()
        elif q.wavelength=='1+2+3':s.SetWavelength123()
        else:s.SetWavelengthNumber(q.wavelength)
        actual_wavelength='RGB'if s.GetWavelengthRGB()else '1+2+3'if s.GetWavelength123()else int(s.GetWavelengthNumber())
        check_setting_value('Wavelength',q.wavelength,actual_wavelength)
    else:
        s.Wavelength.SetWavelengthNumber(q.wavelength)
        check_setting_value('Wavelength',q.wavelength,int(s.Wavelength.GetWavelengthNumber()))
        surface=q.surface if q.surface is not None else backend.system.LDE.NumberOfSurfaces-1
        s.Surface.SetSurfaceNumber(surface)
        check_setting_value('Surface',surface,int(s.Surface.GetSurfaceNumber()))
    center=q.kind in {'geometric_image','geometric_bitmap_image'} and q.row_column_number==0
    if center:requested.pop('RowColumnNumber')
    for name,value in requested.items():checked(backend.native,s,name,value)
    if center:s.UseColumnRowCenter()
    for name,value in requested.items():check(backend.native,s,name,value)
    result=final_settings(s,q)
    if q.kind=='image_simulation':
        wavelength='RGB' if s.GetWavelengthRGB() else '1+2+3' if s.GetWavelength123() else int(s.GetWavelengthNumber())
        check_setting_value('Wavelength',q.wavelength,wavelength)
    else:
        check_setting_value('Surface',surface,int(s.Surface.GetSurfaceNumber()))
    if q.kind in {'geometric_image','geometric_bitmap_image'}:
        result['row_column_selection']=dict(mode='native_center' if center else 'explicit',actual=int(s.RowColumnNumber))
    result['input_resource']=matches[0]
    return result

def run_imaging(backend,q):
    backend._require_sequential(focused=True)
    if q.field>backend.system.SystemData.Fields.NumberOfFields:
        raise ZemaxError('INDEX_OUT_OF_RANGE','图像中心视场编号越界。')
    waves=backend.system.SystemData.Wavelengths.NumberOfWavelengths
    if isinstance(q.wavelength,int)and q.wavelength>waves or q.wavelength=='1+2+3'and waves<3:
        raise ZemaxError('INDEX_OUT_OF_RANGE','图像分析波长选择超出当前系统。')
    if getattr(q,'surface',None) is not None:backend._row(q.surface)
    tool=new_analysis(backend,IDS[q.kind])
    try:
        settings=unwrap(tool.GetSettings());actual=configure(backend,settings,q)
        if q.kind=='image_simulation':
            path=backend.directory/('native_image_'+uuid.uuid4().hex+'.bmp')
            checked(backend.native,settings,'OutputFile',str(path))
            actual['native']['OutputFile']=str(settings.OutputFile)
            actual['native_output_file']=str(path)
    except Exception:
        backend._close_task_native({'native':tool});raise
    return backend._start_task('analysis',tool,actual,analysis=True,collector=lambda task:collect_imaging(backend,task))

def grid_values(grid,rgb=False):
    values=grid.Values;nx=int(grid.Nx);ny=int(grid.Ny)
    a,b=int(values.GetLength(0)),int(values.GetLength(1))
    if nx<1 or ny<1 or nx*ny>LIMIT:
        raise ZemaxError('INVALID_RESULT_DATA','图像网格尺寸无效或超过结构化读取上限。',nx=nx,ny=ny,cell_limit=LIMIT)
    if (a,b)==(ny,nx):transposed=False
    elif (a,b)==(nx,ny):transposed=True
    else:raise ZemaxError('INVALID_RESULT_DATA','图像数组尺寸与原生Nx/Ny不匹配。',nx=nx,ny=ny,array_shape=[a,b])
    def read(x,y):
        value=values[x,y]if transposed else values[y,x]
        return [float(getattr(value,c))for c in 'RGB']if rgb else float(value)
    array=[[read(x,y)for x in range(nx)]for y in range(ny)]
    return array,dict(native_array_shape=[a,b],transposed=transposed,array_order='values[y][x]',orientation_validation='dimension-based; square-grid axis orientation awaits native asymmetric fixture'if nx==ny else 'non-square dimensions identify axes')

def geometric_grid_coordinates(array,axes,nx,ny):
    native_axes=dict(axes)
    dx=abs(axes['dx']);dy=abs(axes['dy'])
    return list(reversed(array)),dict(dx=dx,dy=dy,
        min_x=axes['min_x']+dx/2,min_y=axes['min_y']-(ny-.5)*dy,
        native_axes=native_axes,coordinate_definition='pixel centers; native top-down rows reversed to increasing local Y')


def finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def fft_spread_text_series(text, requested):
    """Read the native indexed position/value table when IAR has no arrays."""
    import re
    from .analyses import parse_psf_section
    if not re.search(r'FFT\s*(?:线扩散|边(?:缘)?扩散|(?:Line|Edge)\s*Spread)',text,re.I):
        return None
    series=parse_psf_section(text)
    if series is None:return None
    data_type=requested.get('data_type','X_Linear')
    suffix=data_type.split('_',1)[1]
    unit='degrees' if suffix=='Phase' else 'relative amplitude' if suffix in {'RealPart','ImaginaryPart'} else 'relative intensity'
    orientation=data_type.split('_',1)[0]
    scan_axis='Y' if orientation=='X' else 'X'
    native_axis=re.search(r'方位值在\s*([XY])\s*方向',text,re.I)
    if native_axis and native_axis[1].upper()!=scan_axis:
        raise ZemaxError('INVALID_RESULT_DATA','FFT line/edge scan axis conflicts with requested orientation.',
                         requested_orientation=orientation,native_scan_axis=native_axis[1])
    series.update(description='native FFT '+requested.get('spread','Line')+' spread',
        labels=[data_type],x_label='image position '+scan_axis,
        value_units=[unit],
        source='native formatted FFT line/edge spread text',
        precision='native displayed digits; position and value retained without renormalization',
        orientation=orientation,scan_axis=scan_axis,
        orientation_definition='line/edge parallel to orientation axis; position scans the perpendicular axis',
        scan_axis_source='native text' if native_axis else 'documented line/edge orientation and request',
        native_interpolation='native table interpolates each scalar representation independently; complex identities apply at original FFT knots',
        logarithmic_display=suffix=='Logarithmic',
        value_representation='native raw values; logarithmic selection controls display, not a log transform of exported intensities')
    return series


def collect_series(result, data):
    for rgb, count, getter in [
        (False, int(result.NumberOfDataSeries), result.GetDataSeries),
        (True, int(result.NumberOfDataSeriesRgb), result.GetDataSeriesRgb),
    ]:
        for i in range(count):
            native = getter(i)
            x = dotnet_array(native.XData.Data)
            raw_labels=native.SeriesLabels
            values=None if rgb else dotnet_array(native.YData.Data)
            width=int(native.NumSeries) if rgb else len(values[0]) if values else 0
            labels=[str(label) for label in raw_labels] if raw_labels is not None else ['column_'+str(j+1) for j in range(width)]
            if len(x) * max(1, len(labels)) > LIMIT:
                raise ZemaxError('RESULT_TOO_LARGE', '曲线超过结构化读取上限。', limit=LIMIT)
            if any(not math.isfinite(v) for v in x):
                raise ZemaxError('INVALID_RESULT_DATA', '曲线横轴包含非有限值。', series=i)
            if rgb:
                if len(x) != int(native.NumberOfRows) or len(labels) != int(native.NumSeries):
                    raise ZemaxError('INVALID_RESULT_DATA', 'RGB曲线维度不一致。', series=i)
                values = [[native.GetYPoint(row, col) for col in range(len(labels))] for row in range(len(x))]
            else:
                if len(x) != len(values) or any(len(row) != len(labels) for row in values):
                    raise ZemaxError('INVALID_RESULT_DATA', '曲线维度与标签不一致。', series=i)
            for channel in 'RGB' if rgb else [None]:
                y = [[finite(getattr(v, channel) if rgb else v) for v in row] for row in values]
                data['series'].append(dict(series=len(data['series']), native_series=i,
                    channel=channel, description=str(native.Description), x_label=str(native.XLabel),
                    labels=labels, x=x, y=y, invalid_count=sum(v is None for row in y for v in row),
                    labels_source='native' if raw_labels is not None else 'generated column indices; native SeriesLabels is null',
                    units_source='native labels and native_header'))


def describe_geometric_spread(data,text,requested):
    import re
    header=re.search(r'X[^\r\n]*Y[^\r\n]*\r?\n[^\r\n]*LSF[^\r\n]*ERF[^\r\n]*LSF[^\r\n]*ERF',text,re.I)
    if not header or not data.get('series'):
        raise ZemaxError('INVALID_RESULT_DATA','Geometric spread native X/Y LSF/ERF column header is unavailable.',
                         native_header=data.get('native_header'))
    for series in data['series']:
        if any(len(row)!=4 for row in series['y']):
            raise ZemaxError('INVALID_RESULT_DATA','Geometric spread requires four native X/Y LSF/ERF columns.')
        series.update(native_labels=series['labels'],labels=['X_LSF','X_ESF','Y_LSF','Y_ESF'],
                      x_label='image position',x_unit='micrometers',
                      value_units=['relative intensity','fraction','relative intensity','fraction'],
                      labels_source='native text X/Y LSF/ERF header',native_column_header=header[0],
                      orientation_definition='line/edge direction X or Y; position scans perpendicular to that direction',
                      position_reference='chief ray',display_selection=requested['data_type'],
                      data_selection='native exports all four columns for LineEdge, Line and Edge display selections')
    return data


def collect_scatter(result, data):
    for rgb, count, getter in [
        (False, int(result.NumberOfDataScatterPoints), result.GetDataScatterPoint),
        (True, int(result.NumberOfDataScatterPointsRgb), result.GetDataScatterPointRgb),
    ]:
        for i in range(count):
            native = getter(i)
            if int(native.NumPoints) > LIMIT:
                raise ZemaxError('RESULT_TOO_LARGE', '散点超过结构化读取上限。', limit=LIMIT)
            points = [native.GetPoint(j) for j in range(int(native.NumPoints))]
            for channel in 'RGB' if rgb else [None]:
                rows = [dict(dataset=i, native_rgb=rgb, channel=channel, point=j, x=finite(p.X), y=finite(p.Y),
                    value=finite(getattr(p.Value, channel) if rgb else p.Value)) for j, p in enumerate(points)]
                valid = [p for p in rows if all(p[k] is not None for k in ('x','y','value'))]
                data['rows'].extend(rows)
                data['scatter'].append(dict(scatter=len(data['scatter']), native_scatter=i, channel=channel,
                    description=str(native.Description), x_label=str(native.XLabel), y_label=str(native.YLabel),
                    value_label=str(native.ValueLabel), points=valid, invalid_count=len(rows)-len(valid),
                    units_source='native labels and native_header'))


def collect_imaging(backend, task):
    r = unwrap(task['native'].GetResults())
    if r is None or not r.IsValid:
        raise ZemaxError('ANALYSIS_FAILED', '图像分析没有有效原生结果。')
    path = backend.directory / (task['task_id'] + '_native.txt')
    data = dict(analysis_kind=task['settings']['kind'], computation_method='native_analysis',
        native_header=[str(x) for x in r.HeaderData.Lines],
        native_messages=[dict(code=str(r.GetMessageAt(i).ErrorCode), text=str(r.GetMessageAt(i).Text)) for i in range(r.NumberOfMessages)],
        grids=[], series=[], scatter=[], rows=[], artifacts=[],
        units_source='native axis labels, ValueLabel and native_header')
    try:
        if r.GetTextFile(str(path)):
            data['artifacts'].append(dict(kind='native_text', path=str(path)))
        else:
            data['native_export_error'] = 'GetTextFile returned false'
    except Exception as exc:
        data['native_export_error'] = dict(type=type(exc).__name__, message=str(exc))
    for rgb, count, getter in [(False, int(r.NumberOfDataGrids), r.GetDataGrid), (True, int(r.NumberOfDataGridsRgb), r.GetDataGridRgb)]:
        for i in range(count):
            g = getter(i)
            array, orientation = grid_values(g, rgb)
            axes = dict(dx=float(g.Dx), dy=float(g.Dy), min_x=float(g.MinX), min_y=float(g.MinY))
            if any(not math.isfinite(v) for v in axes.values()):
                raise ZemaxError('INVALID_RESULT_DATA', '图像网格坐标包含非有限值。', grid=i)
            if task['settings']['kind'] in {'geometric_image','geometric_bitmap_image'}:
                array,axes=geometric_grid_coordinates(array,axes,int(g.Nx),int(g.Ny))
                orientation['orientation_validation']='v242 geometric image native top-down rows; asymmetric ideal source reference'
            for c, channel in enumerate('RGB' if rgb else [None]):
                plane = [[finite(v[c] if rgb else v) for v in row] for row in array]
                data['grids'].append(dict(grid=len(data['grids']), native_grid=i, channel=channel,
                    description=str(g.Description) + ((' '+channel) if channel else ''),
                    x_label=str(g.XLabel), y_label=str(g.YLabel), value_label=str(g.ValueLabel), nx=int(g.Nx), ny=int(g.Ny),
                    **axes, values=plane, invalid_count=sum(v is None for row in plane for v in row),
                    x_unit='see native XLabel/header', y_unit='see native YLabel/header',
                    value_unit='native RGB intensity' if rgb else str(g.ValueLabel), **orientation))
    if task['settings']['kind'] in {'geometric_image','geometric_bitmap_image'}:
        for grid in data['grids']:
            grid.update(x_unit=backend.context()['lens_units'],y_unit=backend.context()['lens_units'],
                        value_unit=grid['description'],units_source='native geometric image unit description and current lens units')
    collect_series(r, data)
    collect_scatter(r, data)
    if task['settings']['kind']=='geometric_line_edge_spread':
        describe_geometric_spread(data,path.read_text(encoding='utf-16') if path.is_file() else '',task['settings']['requested'])
    if task['settings']['kind']=='extended_source_encircled_energy':
        from .extended_source import describe_extended_source
        try:describe_extended_source(data,task['settings']['requested'],task.get('system_settings',{}))
        except ZemaxError as exc:
            exc.details.update(native_text=str(path),artifacts=data['artifacts'],native_messages=data['native_messages'])
            raise
    if task['settings']['kind']=='fft_line_edge_spread' and not data['series'] and path.is_file():
        parsed=fft_spread_text_series(path.read_text(encoding='utf-16'),task['settings']['requested'])
        if parsed is not None:data['series'].append(parsed)
    output=task['settings'].get('native_output_file')
    if output:
        check_setting_value('OutputFile',output,str(unwrap(task['native'].GetSettings()).OutputFile))
        if Path(output).is_file():
            data['artifacts'].append(dict(kind='native_image',path=output,image_source='native'))
            if not data['grids']:
                from .native_bitmap import read_bitmap
                try:bitmap=read_bitmap(output,LIMIT)
                except ZemaxError as exc:
                    exc.details['artifacts']=data['artifacts'];raise
                data['native_bitmap']={k:v for k,v in bitmap.items()if k!='channels'}
                data['native_bitmap']['source']='native ImageSimulation OutputFile'
                data['native_bitmap']['quantity']='native selected-view display samples; physical detector mapping not assigned'
                data['native_bitmap']['output_view']=task['settings']['requested']['show_as']
                data['native_bitmap']['requested_show_as']=task['settings']['requested']['show_as']
                for channel,values in bitmap['channels'].items():
                    data['grids'].append(dict(grid=len(data['grids']),native_grid=None,channel=channel,
                        description='Native '+task['settings']['requested']['show_as']+' display '+channel,x_label='Output X',y_label='Output Y',value_label=channel,
                        nx=bitmap['nx'],ny=bitmap['ny'],dx=1,dy=1,min_x=.5,min_y=.5,values=values,invalid_count=0,
                        x_unit='output_pixel',y_unit='output_pixel',value_unit='8-bit display RGB',array_order='values[y][x]',
                        data_source='native_output_bitmap',coordinate_definition=bitmap['coordinate_definition']))
        else:data['native_file_export_error']=dict(path=output,reason='Native OutputFile was adopted but no file was produced')
    data['structured_data_available'] = bool(data['grids'] or data['series'] or data['scatter'])
    kind = task['settings']['kind']
    if kind == 'image_simulation':
        data['normalization'] = dict(SimulatedImage='native peak output brightness matches input peak',SourceBitmap='native processed source bitmap display',PSFGrid='native PSF-grid display scaling; no PSF amplitude or power inferred')[task['settings']['requested'].get('show_as','SimulatedImage')]
        data['wavelength_conditions'] = dict(selection=task['settings']['requested']['wavelength'],
            rgb_wavelengths_um=[0.606, 0.535, 0.465], wavelength_123_channels=dict(R=3,G=2,B=1),
            diffraction_fallback='native may use geometric PSF for severe aberration; consult native messages')
    elif kind in {'geometric_image','geometric_bitmap_image'}:
        data['normalization'] = 'native TotalWatts source normalization; grid definition retained from native label'
    else:
        data['normalization'] = 'native analysis definition; retain native header and curve labels'
    if not data['structured_data_available'] and not (kind=='coating_listing' and data['artifacts']):
        raise ZemaxError('NO_RESULT_DATA', '分析没有可读取的原生网格、曲线或散点。',
            artifacts=data['artifacts'], native_header=data['native_header'], messages=data['native_messages'],
            native_export_error=data.get('native_export_error'),native_file_export_error=data.get('native_file_export_error'))
    if not data['rows']:data.pop('rows')
    return data

"""Native first-order queries and section-preserving text tables."""
import math
import re
from .errors import ZemaxError

CARD_NAMES=('object_focal_length','image_focal_length','object_focal_plane','image_focal_plane',
    'object_principal_plane','image_principal_plane','object_antiprincipal_plane','image_antiprincipal_plane',
    'object_nodal_plane','image_nodal_plane','object_antinodal_plane','image_antinodal_plane')


def cardinal_points(backend,q):
    backend._require_sequential()
    end=q.end_surface if q.end_surface is not None else backend.system.LDE.NumberOfSurfaces-2
    if end<q.start_surface:raise ZemaxError('INVALID_ARGUMENT','结束面必须不早于起始面。')
    backend._row(q.start_surface);backend._row(end)
    if q.wavelength>backend.system.SystemData.Wavelengths.NumberOfWavelengths:raise ZemaxError('INDEX_OUT_OF_RANGE','波长越界。')
    def flow(task):
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_CARD_operand',
            position_unit=task['context']['lens_units'],start_surface=q.start_surface,end_surface=end,
            reference='object positions relative to start surface; image positions relative to end surface')
        operand=backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType,'CARD')
        for orientation in ('YZ','XZ') if q.orientation=='both' else (q.orientation,):
            for code,name in enumerate(CARD_NAMES):
                backend._cancel_boundary(task)
                value=float(backend.system.MFE.GetOperandValue(operand,q.start_surface,end,q.wavelength,0 if orientation=='YZ' else 1,code,0.,0.,0.))
                task['rows'].append(dict(index=len(task['rows']),orientation=orientation,key=name,value=value if math.isfinite(value) else None,
                    native_value=str(value),state='finite' if math.isfinite(value) else 'undefined',unit=task['context']['lens_units']))
                yield
    return backend._composite(q.kind,q.model_dump(),flow)


def parse_native_tables(text,kind):
    rows=[];headings=[];section=0;previous_data=False;columns=[];ray_section=None
    number=re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?$')
    coefficient=re.compile(r'\b(?:SPHA|COMA|ASTI|FCUR|DIST|CLA|CTR|W[0-9]{3}[A-Z]?|TSPH|TSCO|TTCO|TAST|TPFC|TSFC|TTFC|TDIS|TAXC|TLAC|LSPH|LSCO|LTCO|LAST|LPFC|LSFC|LTFC|LDIS|LAXC|LLAC)\b')
    for line_number,line in enumerate(text.splitlines(),1):
        tokens=line.split()
        if not tokens:continue
        if '近轴' in line or 'paraxial ray' in line.lower():ray_section='paraxial'
        elif '实际光线' in line or 'real ray' in line.lower():ray_section='real'
        cleaned=[t.rstrip('%') for t in tokens]
        numeric=sum(bool(number.fullmatch(t)) for t in cleaned)
        is_data=numeric>=2 and (number.fullmatch(cleaned[0]) or numeric==len(tokens)-1)
        if is_data:
            cells=[float(t) if number.fullmatch(t) and math.isfinite(float(t)) else original for t,original in zip(cleaned,tokens)]
            row=dict(index=len(rows),section=section,headers=list(headings[-3:]),cells=cells,source_line=line_number,raw=line)
            if kind=='seidel_coefficients' and columns and len(cells)==len(columns)+1:
                row.update(row_label=tokens[0],coefficients=dict(zip(columns,cells[1:])),unit='waves' if columns[0].startswith('W') else 'lens units')
            if kind=='single_ray_trace':
                row.update(ray_section=ray_section,surface=int(cells[0]) if isinstance(cells[0],float) else None)
                if len(cells)>=7:row.update(position=cells[1:4],direction_values=cells[4:7])
            if kind=='grid_distortion' and len(cells)==10:
                row.update(grid_index=cells[:2],field=cells[2:4],predicted=cells[5:7],actual=cells[7:9],distortion_percent=cells[9])
            rows.append(row);previous_data=True
        else:
            if previous_data:section+=1;headings=[];columns=[]
            previous_data=False;headings.append(line)
            found=coefficient.findall(line)
            if found:columns=found
    if not rows:raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','原生文本表格未识别。',analysis=kind)
    result=dict(rows=rows,structured_data_available=True,table_format='native columns with section headers',units_source='per-section native headers')
    if kind=='grid_distortion':
        result['scatter']=[dict(description=name+' image coordinates',x_label='image X',y_label='image Y',points=[dict(x=r[key][0],y=r[key][1],value=r['distortion_percent']) for r in rows if key in r]) for key,name in [('predicted','Predicted'),('actual','Actual')]]
    return result

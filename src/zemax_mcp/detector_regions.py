"""Bounded native scalar detector reads without allocating a full detector array."""
import json,uuid,math
from .data import unwrap
from .detector_readers import checked_scalar
from .detectors import detector_metadata
from .errors import ZemaxError


def axis_region(name,half,total,start,end,unit):
    half=float(half)
    if not math.isfinite(half)or half<=0:raise ZemaxError('INVALID_DETECTOR_DATA','探测器半宽无效。',axis=name,half_width=half)
    step=2*half/total
    return dict(name=name,unit=unit,native_start=start,total=total,centers=[-half+(i+.5)*step for i in range(start,end)],bounds=[[-half+i*step,-half+(i+1)*step]for i in range(start,end)])


def read_region(backend,q,row):
    kind=str(row.Type);volume=kind=='DetectorVolume'
    if kind not in ['DetectorRectangle','DetectorVolume']:raise ZemaxError('UNSUPPORTED_DETECTOR_DATA','region支持矩形非相干与体积探测器。',detector_type=kind)
    if q.include_geometry or q.color_channel or q.angle_space or q.coherent_type is not None:raise ZemaxError('INVALID_ARGUMENT','region不接受几何、颜色、角空间或相干选项。')
    if q.kind not in (['flux','absorbed_flux','absorbed_density']if volume else['flux','irradiance','intensity']):raise ZemaxError('UNSUPPORTED_DETECTOR_DATA','当前探测器region数据类型不支持。',detector_type=kind,kind=q.kind)
    if not volume and(q.z_start or q.depth!=1):raise ZemaxError('INVALID_ARGUMENT','矩形探测器region没有Z维度。')
    data=unwrap(row.ObjectData);units=backend.system.SystemData.Units
    if not volume and int(data.DataType)!=0:raise ZemaxError('UNSUPPORTED_DETECTOR_DATA','矩形region目前要求空间DataType=0。',actual=int(data.DataType))
    nx,ny=int(data.NumberXPixels),int(data.NumberYPixels);nz=int(data.NumberZPixels)if volume else 1
    if min(nx,ny,nz)<1 or nx*ny*nz>2147483647:raise ZemaxError('UNSUPPORTED_DETECTOR_SIZE','探测器尺寸无效或像素编号超过原生Int32。',nx=nx,ny=ny,nz=nz)
    if q.x_start>=nx or q.y_start>=ny or q.z_start>=nz:raise ZemaxError('INDEX_OUT_OF_RANGE','region起点超出探测器。',nx=nx,ny=ny,nz=nz)
    xe,ye,ze=min(nx,q.x_start+q.width),min(ny,q.y_start+q.height),min(nz,q.z_start+q.depth)
    x_axis=axis_region('X',data.XHalfWidth,nx,q.x_start,xe,str(units.LensUnits))
    y_axis=axis_region('Y',data.YHalfWidth,ny,q.y_start,ye,str(units.LensUnits))
    z_axis=axis_region('Z',data.ZHalfWidth,nz,q.z_start,ze,str(units.LensUnits))if volume else None
    code=({'flux':0,'absorbed_flux':1,'absorbed_density':2}if volume else{'flux':0,'irradiance':1,'intensity':2})[q.kind]
    values=[[[checked_scalar(backend.system.NCE.GetDetectorData(q.detector,1+x+nx*(y+ny*z),code,0.),detector=q.detector,pixel=1+x+nx*(y+ny*z))for x in range(q.x_start,xe)]for y in range(q.y_start,ye)]for z in range(q.z_start,ze)]
    invalid=sum(v is None for p in values for line in p for v in line)
    result=dict(detector=q.detector,detector_type=kind,kind=q.kind,read_mode='region',nx=nx,ny=ny,nz=nz if volume else None,
        values=values if volume else values[0],native_data_type=code,x_start=q.x_start,y_start=q.y_start,z_start=q.z_start,
        next_x=xe if xe<nx else None,next_y=ye if ye<ny else None,next_z=ze if ze<nz else None,
        array_order='values[z][y][x]'if volume else'values[y][x]',native_pixel_formula='1+x+nx*(y+ny*z)',
        invalid_count=invalid,total_flux=None,scope='requested region only',artifact_scope='requested region only; full detector not read',
        source_units=str(units.SourceUnits),source_unit_prefix=str(units.SourceUnitPrefix),analysis_units=str(units.AnalysisUnits),analysis_unit_prefix=str(units.AnalysisUnitPrefix),
        coordinate_system='detector local spatial',context=backend.context(),**backend._detector_provenance(q.detector),
        x_axis=x_axis,y_axis=y_axis)
    if volume:
        result.update(z_axis=z_axis,quantity={'flux':'incident voxel flux, repeated along ray','absorbed_flux':'absorbed bulk flux per voxel','absorbed_density':'absorbed bulk flux per lens-unit volume'}[q.kind],value_unit=str(units.SourceUnits)+('/'+str(units.LensUnits)+'^3'if q.kind=='absorbed_density'else''),value_unit_prefix=str(units.SourceUnitPrefix))
    else:result.update(detector_metadata(q.kind,None,str(units.SourceUnits),str(units.SourceUnitPrefix),str(units.AnalysisUnits),str(units.AnalysisUnitPrefix),detector_type=kind))
    result['region_sum']=sum(v for p in values for line in p for v in line if v is not None)if q.kind in ['flux','absorbed_flux']else None
    result['sum_definition']='sum within requested region; incident volume flux repeats along paths'
    path=backend.directory/('detector_region_'+uuid.uuid4().hex+'.json')
    path.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    result['artifacts']=[dict(kind='json',path=str(path))]
    return result

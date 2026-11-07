"""2024 R2 detector-specific quantities; native scalar success is mandatory."""
import json
import math
import uuid
from .data import unwrap,dotnet_array
from .errors import ZemaxError

COLOR_CHANNELS={"radiometric_flux":1,"radiometric_density":2,"photometric_flux":3,
    "photometric_density":4,"chromaticity_x":5,"chromaticity_y":6,"u_prime":7,"v_prime":8,
    "tristimulus_x":9,"tristimulus_y":10,"tristimulus_z":11}


def axis(name,half,count,unit):
    step=2*half/count
    return dict(name=name,unit=unit,centers=[-half+(i+.5)*step for i in range(count)],
                bounds=[[-half+i*step,-half+(i+1)*step] for i in range(count)])


def checked_scalar(result,**details):
    if not result or not result[0]:raise ZemaxError("DETECTOR_READ_FAILED","原生探测器数据读取失败。",**details)
    value=float(result[1])
    return value if math.isfinite(value) else None


def read_special(backend,req,row):
    editor=backend.system.NCE;kind=str(row.Type);data=unwrap(row.ObjectData)
    if req.include_geometry and kind!='DetectorSurface':raise ZemaxError('UNSUPPORTED_DETECTOR_GEOMETRY','include_geometry仅用于DetectorSurface。')
    units=backend.system.SystemData.Units
    if req.color_channel and kind!="DetectorColor":raise ZemaxError("UNSUPPORTED_DETECTOR_DATA","color_channel仅适用于DetectorColor。")
    if kind!="DetectorVolume" and (req.z_start or req.depth!=1):raise ZemaxError("INVALID_ARGUMENT","Z区域仅适用于DetectorVolume。")
    full=dict(detector=req.detector,detector_type=kind,kind=req.kind,context=backend.context(),
              **backend._detector_provenance(req.detector))
    if kind=="DetectorColor":
        if req.kind=="coherent" or req.kind.startswith("absorbed"):
            raise ZemaxError("UNSUPPORTED_DETECTOR_DATA","Color不提供该数据类型。",kind=req.kind)
        if req.kind=="spectral":
            if not getattr(row.TypeData,"RecordSpectralData",False):
                raise ZemaxError("UNSUPPORTED_DETECTOR_DATA","光谱箱数据需要启用RecordSpectralData。")
            names={17:"centroid_x",18:"centroid_y",19:"rms_radius",20:"rms_x",21:"rms_y"}
            rows=[dict(wavelength_um=w,**{name:checked_scalar(editor.GetColorDetectorData(
                req.detector,0,False,code,0,w,0.),detector=req.detector,channel=code,wavelength_um=w)
                for code,name in names.items()}) for w in req.spectral_wavelengths_um]
            full.update(rows=rows,quantity="native spectral-bin spatial centroid and RMS",value_unit=str(units.LensUnits),
                spectral_definition="wavelength selects its native spectral bin; centroid uses detector pixel centers; this is not a spectral power density",
                actual_detector_settings={k:str(getattr(row.TypeData,k)) for k in ("RecordSpectralData",)})
            response=full
        else:
            channel=req.color_channel or ("radiometric_flux" if req.kind=="flux" else "radiometric_density")
            angle=req.angle_space or req.kind=="intensity"
            array=editor.GetAllColorDetectorDataSafe(req.detector,angle,COLOR_CHANNELS[channel])
            if array is None or getattr(array,"Rank",None)!=2:raise ZemaxError("INVALID_DETECTOR_DATA","Color未返回二维矩阵。")
            raw=dotnet_array(array);ny=int(data.NumberYPixels);nx=int(data.NumberXPixels)
            if len(raw)!=nx*ny or any(len(r)!=1 for r in raw):
                raise ZemaxError("INVALID_DETECTOR_DATA","本机Color应返回[Npixels,1]数组。",expected=[nx*ny,1],actual=[len(raw),len(raw[0])if raw else 0])
            values=[[raw[y*nx+x][0] for x in range(nx)] for y in range(ny)]
            if not nx or not ny or req.x_start>=nx or req.y_start>=ny:raise ZemaxError("INDEX_OUT_OF_RANGE","Color区域起点越界。")
            invalid=sum(not math.isfinite(v) for r in values for v in r)
            values=[[v if math.isfinite(v) else None for v in r] for r in values]
            density=channel.endswith("density") or channel.startswith("tristimulus")
            photometric=channel.startswith("photometric") or channel.startswith("tristimulus")
            chromatic=channel in {"chromaticity_x","chromaticity_y","u_prime","v_prime"}
            base=("Talbots" if photometric else "Joules") if str(units.SourceUnits)=="Joules" else ("Lumens" if photometric else "Watts")
            value_unit="dimensionless" if chromatic else base
            if density:value_unit=base+"/sr" if angle else str(units.AnalysisUnits).replace("Watts",base).replace("Lumens",base)
            full.update(nx=nx,ny=ny,values=values,invalid_count=invalid,color_channel=channel,native_data_type=COLOR_CHANNELS[channel],
                angle_space=angle,value_unit=value_unit,value_unit_prefix="None" if chromatic else str(units.AnalysisUnitPrefix if density else units.SourceUnitPrefix),
                total_flux=sum(v for r in values for v in r if v is not None) if channel.endswith("_flux") else None,
                array_order="rows local Y, columns local X; native flat pixels reshaped x-fast",
                native_array_shape=[nx*ny,1],
                coordinate_system="detector-local angular" if angle else "detector-local spatial")
            if not angle:
                full.update(x_axis=axis("X",float(data.XHalfWidth),nx,str(units.LensUnits)),
                            y_axis=axis("Y",float(data.YHalfWidth),ny,str(units.LensUnits)))
            else:
                def angular_axis(key,count):
                    lo,hi=float(getattr(data,key+"AngleMin")),float(getattr(data,key+"AngleMax"))
                    if not math.isfinite(lo+hi)or hi<=lo:raise ZemaxError("INVALID_DETECTOR_DATA","Color角度范围无效。",axis=key)
                    step=(hi-lo)/count
                    return dict(name=key+" radial-angle projection",unit="degrees",centers=[lo+(i+.5)*step for i in range(count)],bounds=[[lo+i*step,lo+(i+1)*step]for i in range(count)])
                full.update(x_axis=angular_axis("X",nx),y_axis=angular_axis("Y",ny),
                    angle_definition="theta=acos(local N); X=theta*L/sqrt(1-N^2), Y=theta*M/sqrt(1-N^2); on-axis limit zero; not independent XZ/YZ angles")
            xend=min(nx,req.x_start+req.width);yend=min(ny,req.y_start+req.height)
            response={**full,"values":[r[req.x_start:xend] for r in values[req.y_start:yend]],
                "x_start":req.x_start,"y_start":req.y_start,"next_x":xend if xend<nx else None,"next_y":yend if yend<ny else None}
    elif kind=="DetectorSurface":
        if req.kind not in {"flux","irradiance"} or req.angle_space or req.color_channel:
            raise ZemaxError("UNSUPPORTED_DETECTOR_DATA","Surface三角像素支持flux和irradiance。")
        size=int(editor.GetDetectorSize(req.detector))
        if size<1 or size>1000000:raise ZemaxError("UNSUPPORTED_DETECTOR_SIZE","无有效三角像素或超过1000000像素。")
        if req.start>size:raise ZemaxError("INDEX_OUT_OF_RANGE","三角像素分页起点越界。")
        code=0 if req.kind=="flux" else 1
        rows=[dict(index=i,pixel=i+1,value=checked_scalar(editor.GetDetectorData(req.detector,i+1,code,0.),
            detector=req.detector,pixel=i+1)) for i in range(size)]
        full.update(rows=rows,total=size,native_data_type=code,coordinate_system="native triangular detector pixels",
            pixel_definition="native one-based triangle index; FastRayTrace may reorder triangles",
            triangle_coordinate_status="per-pixel vertex mapping not available through this scalar API",
            value_unit=str(units.SourceUnits) if code==0 else str(units.AnalysisUnits).replace("Watts","Joules").replace("Lumens","Talbots")if str(units.SourceUnits)=="Joules"else str(units.AnalysisUnits),
            value_unit_prefix=str(units.SourceUnitPrefix if code==0 else units.AnalysisUnitPrefix),
            total_flux=sum(r["value"] for r in rows if r["value"]is not None) if code==0 else None,
            invalid_count=sum(r["value"]is None for r in rows))
        if req.include_geometry:
            from .facets import read_facet_geometry
            faces=read_facet_geometry(row,req.geometry_frame)
            if len(faces)!=size:raise ZemaxError('INVALID_DETECTOR_DATA','原生面数与三角像素数量不符。',faces=len(faces),pixels=size)
            # Face/pixel association is exposed with its native pair and checked
            # against each face's own radiometric value. Live hit tests qualify it.
            for item,face in zip(rows,faces,strict=True):
                native=face['facet_flux'if code==0 else'facet_irradiance']
                if native is None or item['value']is None or not math.isclose(native,item['value'],rel_tol=1e-10,abs_tol=1e-12):
                    raise ZemaxError('DETECTOR_PIXEL_MAPPING_UNVERIFIED','原生面值与对应探测像素不符。',face=face['face'],pixel=item['pixel'])
                item.update(geometry=face)
            full.update(geometry_frame=req.geometry_frame,geometry_unit=str(units.LensUnits),area_unit=str(units.LensUnits)+'^2',
                triangle_coordinate_status='native IFaceData; face/pixel values cross-checked',geometry_source='INCERow.GetFacetedObjectData/IFaceData')
        end=min(size,req.start+req.count)
        response={**full,"rows":rows[req.start:end],"start":req.start,"next_start":end if end<size else None}
    elif kind=="DetectorVolume":
        if req.kind not in {"flux","absorbed_flux","absorbed_density"} or req.angle_space or req.color_channel:
            raise ZemaxError("UNSUPPORTED_DETECTOR_DATA","Volume支持flux(入射)、absorbed_flux、absorbed_density。")
        nx,ny,nz=(int(getattr(data,name)) for name in ("NumberXPixels","NumberYPixels","NumberZPixels"))
        if min(nx,ny,nz)<1 or nx*ny*nz>1000000:raise ZemaxError("UNSUPPORTED_DETECTOR_SIZE","Volume全量JSON当前支持最多1000000体素。")
        if req.x_start>=nx or req.y_start>=ny or req.z_start>=nz:raise ZemaxError("INDEX_OUT_OF_RANGE","体素区域起点越界。")
        code={"flux":0,"absorbed_flux":1,"absorbed_density":2}[req.kind]
        # Scalar API and documented one-based x-fast voxel numbering.
        values=[[[checked_scalar(editor.GetDetectorData(req.detector,1+x+nx*(y+ny*z),code,0.),
            detector=req.detector,voxel=1+x+nx*(y+ny*z)) for x in range(nx)] for y in range(ny)] for z in range(nz)]
        full.update(nx=nx,ny=ny,nz=nz,values=values,native_data_type=code,
            array_order="values[z][y][x]; one-based native pixel = 1+x+nx*(y+ny*z)",
            coordinate_system="detector-local spatial",x_axis=axis("X",float(data.XHalfWidth),nx,str(units.LensUnits)),
            y_axis=axis("Y",float(data.YHalfWidth),ny,str(units.LensUnits)),z_axis=axis("Z",float(data.ZHalfWidth),nz,str(units.LensUnits)),
            quantity={0:"incident flux entering each voxel; repeated along one ray path",1:"absorbed bulk flux per voxel",2:"absorbed bulk flux per unit volume"}[code],
            value_unit=str(units.SourceUnits) if code<2 else str(units.SourceUnits)+"/"+str(units.LensUnits)+"^3",
            value_unit_prefix=str(units.SourceUnitPrefix),
            total_flux=None,invalid_count=sum(v is None for p in values for r in p for v in r),
            volume_sum_interpretation="incident voxel flux must not be summed as unique detector input power")
        xend=min(nx,req.x_start+req.width);yend=min(ny,req.y_start+req.height);zend=min(nz,req.z_start+req.depth)
        response={**full,"values":[[r[req.x_start:xend] for r in p[req.y_start:yend]] for p in values[req.z_start:zend]],
            "x_start":req.x_start,"y_start":req.y_start,"z_start":req.z_start,
            "next_x":xend if xend<nx else None,"next_y":yend if yend<ny else None,"next_z":zend if zend<nz else None}
    else:raise ZemaxError("UNSUPPORTED_DETECTOR","探测器尚无可靠数值适配。",detector_type=kind)
    path=backend.directory/("detector_"+uuid.uuid4().hex+".json")
    path.write_text(json.dumps(full,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return {**response,"artifacts":[dict(kind="json",path=str(path))]}

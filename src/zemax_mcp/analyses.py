"""Typed sequential analyses and native series/grid result adapters."""
import math,re
from pathlib import Path
from .data import unwrap, dotnet_array
from .errors import ZemaxError
from .surface_slopes import SLOPE_ANALYSES, configure_surface_slope, describe_surface_slope
from .polarization_topics import TOPIC_KINDS, parse_topic_text

ANALYSES = {
    "ray_database_viewer":"RayDatabaseViewer",
    "ima_bim_viewer":"IMABIMFileViewer",
    "test_plate_list":"TestPlateList",
    "biocular_field_of_view":"BiocularFieldOfViewAnalysis",
    "biocular_dipvergence_convergence":"BiocularDipvergenceConvergence",
    "yybar_diagram":"YYbarDiagram", "incident_angle_vs_image_height":"IncidentAnglevsImageHeight",
    "sag_table":"SagTable",
    'paraxial_gaussian_beam':'ParaxialGaussianBeam','skew_gaussian_beam':'SkewGaussianBeam',
    "universal_plot_1d":"UniversalPlot1D", "universal_plot_2d":"UniversalPlot2D",
    "system_data":"SystemData", "system_check":"SystemCheck", "file_comparator":"FileComparatorSettings", "pupil_aberration_fan":"PupilAberrationFan",
    "polarization_pupil_map":"PolarizationPupilMap",
    "phase_aberration":"PhaseAberration","polarization_ray_trace":"PolarizationRayTrace",
    "polarization_transmission":"Transmission","fiber_coupling_settings":"FiberCouplingSettings",
    "rms_vs_field":"RMSField","rms_field_map":"RMSFieldMap","rms_vs_focus":"RMSFocus","through_focus_spot":"ThroughFocusSpot",
    "contrast_loss":"ContrastLoss", "rms_vs_wavelength":"RMSLambdaDiagram",
    "single_ray_trace":"RayTrace","cardinal_points":"CardinalPoints","seidel_coefficients":"SeidelCoefficients","yni_contributions":"YNIContributions","source_spectrum_viewer":"SourceSpectrumViewer","directivity_plot":"DirectivityPlot","polarization_transmission_fan":"TransmissionFan","seidel_diagram":"SeidelDiagram","grid_distortion":"GridDistortion",
    "geometric_mtf_vs_field":"GeometricMtfvsField", "huygens_mtf_vs_field":"HuygensMtfvsField",
    "fft_mtf_map":"FftMtfMap", "geometric_mtf_map":"GeometricMtfMap",
    "relative_illumination":"RelativeIllumination", "fft_mtf_vs_field":"FftMtfvsField",
    "fft_surface_mtf":"FftSurfaceMtf",
    "huygens_surface_mtf":"HuygensSurfaceMtf",
    "full_field_spot":"FullFieldSpot", "matrix_spot":"MatrixSpot", "configuration_matrix_spot":"ConfigurationMatrixSpot",
    "foucault":"Foucault", "full_field_aberration":"FullFieldAberration",
    "fft_line_edge_spread":"FftPsfLineEdgeSpread", "geometric_line_edge_spread":"GeometricLineEdgeSpread", "extended_source_encircled_energy":"ExtendedSourceEncircledEnergy",
    "image_simulation":"ImageSimulation", "geometric_image":"GeometricImageAnalysis",
    "geometric_bitmap_image":"GeometricBitmapImageAnalysis",
    "extended_diffraction_image":"ExtendedDiffractionImageAnalysis",
    "partially_coherent_image":"PartiallyCoherentImageAnalysis",
    "diff_efficiency_2d":"DiffEfficiency2D", "diff_efficiency_angular":"DiffEfficiencyAngular",
    "diff_efficiency_chromatic":"DiffEfficiencyChromatic",
    "grin_profile":"GrinProfile",
    "dispersion_diagram":"DispersionDiagram",
    "dispersion_vs_wavelength":"DispersionvsWavelength",
    "glass_map":"GlassMap", "athermal_glass_map":"AthermalGlassMap",
    "power_field_map":"PowerFieldMapSettings", "power_pupil_map":"PowerPupilMapSettings",
    "nsc_surface_sag":"NSCSurfaceSag",
    "vignetting":"VignettingDiagramSettings", "footprint":"FootprintSettings",
    "huygens_mtf":"HuygensMtf", "geometric_mtf":"GeometricMtf",
    "fft_through_focus_mtf":"FftThroughFocusMtf", "huygens_through_focus_mtf":"HuygensThroughFocusMtf", "geometric_through_focus_mtf":"GeometricThroughFocusMtf",
    "fft_psf":"FftPsf", "fft_psf_cross":"FftPsfCrossSection", "huygens_psf":"HuygensPsf", "huygens_psf_cross":"HuygensPsfCrossSection",
    "quick_yield":"QuickYield", "tolerance_yield":"ToleranceYield", "tolerance_histogram":"ToleranceHistogram",
    "diffraction_encircled_energy":"DiffractionEncircledEnergy", "geometric_encircled_energy":"GeometricEncircledEnergy",
    "wavefront":"WavefrontMap", "zernike_standard":"ZernikeStandardCoefficients", "zernike_fringe":"ZernikeFringeCoefficients", "zernike_annular":"ZernikeAnnularCoefficients",
    "ray_fan":"RayFan", "opd_fan":"OpticalPathFan", "field_curvature_distortion":"FieldCurvatureAndDistortion",
    "longitudinal_aberration":"LongitudinalAberration", "lateral_color":"LateralColor", "focal_shift":"FocalShiftDiagram",
    "surface_sag":"SurfaceSag", "surface_curvature":"SurfaceCurvature", "surface_phase":"SurfacePhase",
    "surface_sag_cross":"SurfaceSagCross", "surface_curvature_cross":"SurfaceCurvatureCross", "surface_phase_cross":"SurfacePhaseCross",
}

ANALYSES.update({metric+'_vs_'+axis:metric.capitalize()+'vs'+axis.capitalize()for metric in ['reflection','transmission','absorption','diattenuation','phase','retardance']for axis in ['angle','wavelength']})
ANALYSES['coating_listing']='CoatingListing'
ANALYSES['path_analysis']='PathAnalysis'
ANALYSES['nsc_geometric_mtf']='NSCGeometricMtf'
ANALYSES.update(critical_ray_trace='CriticalRayTracer',nsc_single_ray_trace='NSCSingleRayTrace')
ANALYSES['internal_transmission_vs_wavelength']='InternalTransmissionvsWavelength'
ANALYSES.update(SLOPE_ANALYSES)
ANALYSES.update(zernike_coefficients_vs_field='ZernikeCoefficientsVsField',interferogram='Interferogram')
ANALYSES.update(prescription_data='PrescriptionDataSettings',surface_data='SurfaceDataSettings')
ANALYSES.update(star_align_check='STARAlignCheck',star_sys_viewer='STARSysViewer',
                star_2d_def_plot='STAR2DDefPlot',star_perf_change='STARPerfChange',
                star_index_vs_temp='STARIndexVsTemp',star_inspect_fea='STARInspectFEA')

from .coating_models import CoatingAngle,CoatingWavelength,CoatingListing


def tolerance_operand_number(index,count):
    if index>=count:
        raise ZemaxError("INDEX_OUT_OF_RANGE","公差操作数编号越界。",operand=index,count=count)
    return index+1


def parse_zernike(text,expected):
    """2024 R2 Z-index/tab/value/colon polynomial rows, Chinese or English."""
    rows=[]
    for line_number,line in enumerate(text.splitlines(),1):
        match=re.fullmatch(r"\s*Z\s+(\d+)\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\s*(?::\s*(.*))?",line)
        if match:
            value=float(match[2])
            if not math.isfinite(value):return []
            rows.append(dict(term=int(match[1]),value=value,polynomial=match[3],unit="waves",source_line=line_number))
    return rows if [r["term"]for r in rows]==list(range(1,expected+1))else []

def parse_psf_section(text):
    points=[]
    number=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
    for line in text.splitlines():
        match=re.fullmatch(r"\s*(\d+)\s+("+number+r")\s+("+number+r")\s*",line)
        if match:points.append((int(match[1]),float(match[2]),float(match[3])))
    if len(points)<2 or [p[0]for p in points]!=list(range(len(points))):return None
    if any(not math.isfinite(v)for p in points for v in p[1:]):return None
    if any(b[1]<=a[1]for a,b in zip(points,points[1:])):return None
    return dict(series=0,description="native PSF center-row cross section",x_label="position",labels=["relative irradiance"],x=[p[1]for p in points],y=[[p[2]]for p in points],x_unit="micrometers",value_units=["relative irradiance"],source="2024 R2 formatted native text",precision="native displayed digits")


def _parse_native_material_curve(text,title_pattern,value_unit_pattern,value_unit,quantity,positive_values):
    lines=text.splitlines()
    title=next((line.strip() for line in lines if line.strip()),"")
    if not re.search(title_pattern,title,re.I):
        raise ZemaxError("INVALID_RESULT_DATA","原生文本标题与请求的材料曲线不匹配。",title=title)
    header_index=None
    labels=[]
    for index,line in enumerate(lines):
        cells=[cell.strip() for cell in re.split(r"\t+",line.strip()) if cell.strip()]
        if len(cells)>1 and re.fullmatch(r"波长|wavelength",cells[0],re.I):
            header_index=index
            labels=cells[1:]
            break
    if header_index is None or not labels:
        raise ZemaxError("NO_RESULT_DATA","色散报告没有材料列标题。",title=title)
    unit_text=" ".join(lines[:header_index]).replace("μ","µ")
    if not re.search(r"(?:波长\s*[:：]\s*µm|wavelength\s*[:=]\s*(?:µm|um|micrometers?))",unit_text,re.I):
        raise ZemaxError("INVALID_RESULT_DATA","原生色散报告没有可识别的波长单位。",native_unit_lines=lines[:header_index])
    if value_unit_pattern and not re.search(value_unit_pattern,unit_text,re.I):
        raise ZemaxError("INVALID_RESULT_DATA","原生材料曲线没有可识别的纵轴单位。",native_unit_lines=lines[:header_index])
    number=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
    points=[]
    for line_number,line in enumerate(lines[header_index+1:],header_index+2):
        cells=line.split()
        if not cells or not re.fullmatch(number,cells[0]):
            if points:break
            continue
        if len(cells)!=len(labels)+1 or not all(re.fullmatch(number,cell) for cell in cells):
            raise ZemaxError("INVALID_RESULT_DATA","色散表列数与材料标题不匹配，或包含非数值字段。",line=line_number,labels=labels,cells=cells)
        values=[float(cell) for cell in cells]
        if any(not math.isfinite(value) for value in values) or values[0]<=0 or positive_values and any(value<=0 for value in values[1:]):
            raise ZemaxError("INVALID_RESULT_DATA","色散表包含非有限或非正数值。",line=line_number,values=values)
        points.append((line_number,values[0],values[1:]))
    if len(points)<2 or any(b[1]<=a[1] for a,b in zip(points,points[1:])):
        raise ZemaxError("INVALID_RESULT_DATA","色散表采样不足或波长未严格递增。",point_count=len(points))
    temperatures=[]
    pressures=[]
    for line in lines[:header_index]:
        match=re.search(r"(?:温度\s*[:：]?\s*|temperature\s*[:=]?\s*)([-+]?\d+(?:\.\d+)?)\s*(?:摄氏度|°?C)",line,re.I)
        if match:temperatures.append(float(match[1]))
        match=re.search(r"(?:压强|压力|pressure)\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)\s*(?:大气压|atm)",line,re.I)
        if match:pressures.append(float(match[1]))
    series=dict(series=0,description=quantity+" versus wavelength",x_label="Wavelength",
        labels=labels,x=[point[1] for point in points],y=[point[2] for point in points],
        x_unit="micrometers",value_units=[value_unit]*len(labels),y_unit=value_unit,
        invalid_count=0,source="native formatted material analysis text",precision="native displayed digits",
        source_lines=[point[0] for point in points])
    result=dict(series=[series],grids=[],structured_data_available=True,
        computation_method="native_analysis_text_table",material_identity_source="native report column labels",
        environment={"temperature_c":temperatures[0] if temperatures else None,
            "pressure_atm":pressures[0] if pressures else None,
            "source":"native report preamble"},sample_count=len(points),native_title=title)
    return result


def parse_dispersion_diagram(text):
    """Parse native DispersionDiagram refractive-index columns."""
    result=_parse_native_material_curve(text,
        r"折射率\s*(?:vs\.?|对|与)\s*波长|refractive\s+index\s+vs\.?\s*wavelength",
        None,"dimensionless","refractive index",True)
    result["analysis_kind"]="dispersion_diagram"
    return result


def parse_dispersion_vs_wavelength(text):
    """Parse native wavelength-derivative columns and preserve inverse-length units."""
    result=_parse_native_material_curve(text,
        r"色散\s*(?:vs\.?|对|与)\s*波长|dispersion\s+vs\.?\s*wavelength",
        r"(?:色散|dispersion)\s*[:：=]\s*1\s*/\s*(?:µm|um|micrometers?)",
        "1/micrometer","refractive-index dispersion",False)
    result["analysis_kind"]="dispersion_vs_wavelength"
    return result


def parse_glass_map(text):
    """Parse native glass-map Nd/Vd rows into page-able glass records and scatter points."""
    lines=text.splitlines()
    title=next((line.strip() for line in lines if line.strip()),"")
    if not re.search(r"玻璃图数据|glass\s+map\s+data",title,re.I):
        raise ZemaxError("INVALID_RESULT_DATA","原生文本不是玻璃图报告。",title=title)
    header_index=next((i for i,line in enumerate(lines) if all(token in line for token in ("玻璃名称","折射率","阿贝数"))),None)
    if header_index is None:
        raise ZemaxError("NO_RESULT_DATA","玻璃图报告缺少材料、折射率或Abbe数列标题。",title=title)
    number=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
    rows=[]
    for line_number,line in enumerate(lines[header_index+1:],header_index+2):
        cells=line.split()
        if len(cells)==3 and re.fullmatch(number,cells[1]) and re.fullmatch(number,cells[2]):
            index,abbe=float(cells[1]),float(cells[2])
            if not math.isfinite(index) or not math.isfinite(abbe) or index<=0 or abbe<=0:
                raise ZemaxError("INVALID_RESULT_DATA","玻璃图数据包含无效Nd或Abbe数。",line=line_number,cells=cells)
            rows.append(dict(index=len(rows),material=cells[0],refractive_index_nd=index,abbe_vd=abbe,
                source_line=line_number))
        elif rows and ("找到" in line or re.search(r"found\s+\d+\s+glasses",line,re.I)):
            break
        elif rows and not line.strip():
            continue
        elif rows and line.strip():
            break
    if not rows:
        raise ZemaxError("NO_RESULT_DATA","玻璃图报告没有可识别的玻璃数据行。",native_header=lines[header_index])
    series=dict(scatter=0,description="Glass Map",x_label="Abbe number Vd",y_label="Refractive index Nd",
        x_unit="dimensionless",y_unit="dimensionless",x_axis_direction="decreasing_left_to_right",
        coordinate_definition="x=Abbe Vd; y=refractive index Nd at d-line",
        points=[dict(x=row["abbe_vd"],y=row["refractive_index_nd"],label=row["material"]) for row in rows])
    count_match=re.search(r"(?:找到|found\s+)(\d+)\s*(?:玻璃|glasses)"," ".join(lines),re.I)
    return dict(analysis_kind="glass_map",rows=rows,scatter=[series],structured_data_available=True,
        computation_method="native_analysis_text_table",sample_count=len(rows),
        native_report_count=int(count_match[1]) if count_match else None,
        material_identity_source="native report glass-name column",
        coordinate_units=dict(abbe_vd="dimensionless",refractive_index_nd="dimensionless"),
        native_title=title)


def parse_athermal_glass_map(text):
    """Parse the native chromatic/thermal glass-power table and preserve display scaling."""
    lines=text.splitlines()
    title=next((line.strip() for line in lines if line.strip()),"")
    if not re.search(r"无热玻璃图数据|athermal\s+glass\s+map\s+data",title,re.I):
        raise ZemaxError("INVALID_RESULT_DATA","原生文本不是无热玻璃图报告。",title=title)
    header_index=next((i for i,line in enumerate(lines)
        if (("玻璃名称" in line and "有色的" in " ".join(lines[max(0,i-1):i+3]) and "热的" in " ".join(lines[max(0,i-1):i+3]))
        or (re.search(r"glass\s+name",line,re.I) and re.search(r"chromatic", " ".join(lines[max(0,i-1):i+3]),re.I)
            and re.search(r"thermal", " ".join(lines[max(0,i-1):i+3]),re.I)))),None)
    if header_index is None:
        raise ZemaxError("NO_RESULT_DATA","无热玻璃图缺少玻璃、色散或热光焦列标题。",title=title)
    # Display scales come from the native header (光焦 xE-3 / xE-6); never assume them.
    scale_text=" ".join(lines[max(0,header_index-1):header_index+1])
    scale_exponents=re.findall(r"xE([-+]?\d+)",scale_text)
    if len(scale_exponents)!=2:
        # Header contract gap, not a native analysis failure; keep the raw header text.
        raise ZemaxError("INVALID_RESULT_DATA","无热玻璃图报告表头未给出色散/热光焦显示标尺（xE-n），无法确定显示缩放。",
            native_header=lines[header_index],native_scale_source="native report header")
    try:
        chromatic_scale=10.0**int(scale_exponents[0])
        thermal_scale=10.0**int(scale_exponents[1])
    except OverflowError as exc:
        raise ZemaxError("INVALID_RESULT_DATA","无热玻璃图报告表头的显示标尺超出可表示范围（xE-n），无法确定显示缩放。",
            native_header=lines[header_index],native_scale_source="native report header",
            scale_exponents=scale_exponents) from exc
    if not all(math.isfinite(scale) and scale>0 for scale in (chromatic_scale,thermal_scale)):
        raise ZemaxError("INVALID_RESULT_DATA","无热玻璃图报告表头的显示标尺非有限或为零（xE-n），无法确定显示缩放。",
            native_header=lines[header_index],native_scale_source="native report header",
            scale_exponents=scale_exponents)
    display_scales=dict(chromatic_power="1e"+scale_exponents[0].lstrip("+"),
        thermal_power="1e"+scale_exponents[1].lstrip("+"))
    preamble="\n".join(lines[:header_index])
    wavelength={}
    for key,pattern in {"minimum":r"(?:最小波长|minimum\s+wavelength)\s*[:：]\s*(\S+)",
        "center":r"(?:中心波长|center\s+wavelength)\s*[:：]\s*(\S+)",
        "maximum":r"(?:最大波长|maximum\s+wavelength)\s*[:：]\s*(\S+)"}.items():
        match=re.search(pattern,preamble,re.I)
        if match:
            try:value=float(match[1])
            except ValueError as exc:
                raise ZemaxError("INVALID_RESULT_DATA","无热玻璃图报告中的波长无效。",field=key,value=match[1]) from exc
            if not math.isfinite(value) or value<=0:
                raise ZemaxError("INVALID_RESULT_DATA","无热玻璃图报告中的波长无效。",field=key,value=match[1])
            wavelength[key]=value
    number=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
    rows=[]
    for line_number,line in enumerate(lines[header_index+1:],header_index+2):
        cells=line.split()
        if len(cells)==3 and re.fullmatch(number,cells[1]) and re.fullmatch(number,cells[2]):
            chromatic,thermal=map(float,cells[1:])
            if not math.isfinite(chromatic) or not math.isfinite(thermal):
                raise ZemaxError("INVALID_RESULT_DATA","无热玻璃图包含非有限数据。",line=line_number,cells=cells)
            rows.append(dict(index=len(rows),material=cells[0],chromatic_power_reported=chromatic,
                thermal_power_reported=thermal,chromatic_power=chromatic*chromatic_scale,
                thermal_power_per_celsius=thermal*thermal_scale,source_line=line_number))
        elif rows and line.strip():
            break
    if not rows:
        raise ZemaxError("NO_RESULT_DATA","无热玻璃图没有可识别的玻璃数据行。",native_header=lines[header_index])
    series=dict(scatter=0,description="Athermal Glass Map",x_label="Chromatic power",y_label="Thermal power",
        x_unit="dimensionless",y_unit="1/°C",x_axis_display_scale=display_scales["chromatic_power"],
        y_axis_display_scale=display_scales["thermal_power"],
        points=[dict(x=row["chromatic_power"],y=row["thermal_power_per_celsius"],label=row["material"]) for row in rows])
    count_match=re.search(r"(?:找到|found\s+)(\d+)\s*(?:玻璃|glasses)"," ".join(lines),re.I)
    return dict(analysis_kind="athermal_glass_map",rows=rows,scatter=[series],grids=[],
        structured_data_available=True,computation_method="native_analysis_text_table",
        material_identity_source="native report glass-name column",sample_count=len(rows),
        native_report_count=int(count_match[1]) if count_match else None,
        coordinate_units=dict(chromatic_power="dimensionless",thermal_power="1/°C"),
        native_display_scales=display_scales,native_display_scales_source="native report header (光焦 xE-n)",
        native_header=lines[header_index],
        wavelength_conditions=wavelength,native_title=title)


def scalar_settings(settings):
    """Read actual primitive/enum settings; do not traverse native object graphs."""
    settings=unwrap(settings)
    out={}
    for p in settings.GetType().GetProperties():
        if p.GetIndexParameters().Length: continue
        t=p.PropertyType
        if not (t.IsPrimitive or t.IsEnum or str(t.FullName)=="System.String"): continue
        try:value=getattr(settings,str(p.Name))
        except Exception as exc:
            out.setdefault("unavailable_fields",{})[str(p.Name)]=str(exc)
            continue
        out[str(p.Name)]=str(value) if t.IsEnum else value
    for key in ("Field","ReferenceField","Wavelength","Surface","StartSurface","EndSurface"):
        try:obj=getattr(settings,key,None)
        except Exception as exc:
            out.setdefault("unavailable_fields",{})[key]=str(exc)
            continue
        if obj is None: continue
        method="GetWavelengthNumber" if key=="Wavelength" else "GetFieldNumber" if "Field" in key else "GetSurfaceNumber"
        if hasattr(obj,method):out[key]=int(getattr(obj,method)())
    return out

def configure_diff_efficiency(q,setv):
    setv("SampleSize",q.sample_size)
    names={
        "min_wavelength":"MinWavelength", "max_wavelength":"MaxWavelength",
        "min_angle":"MinAngle", "max_angle":"MaxAngle",
        "hologram_object":"HologramObject", "ambient_object":"AmbientObject",
        "detector_object":"DetectorObject", "source_position_x":"srcPositionX",
        "source_position_y":"srcPositionY", "source_position_z":"srcPositionZ",
        "source_unpolarized":"srcUnpolarized", "source_x_tilted":"srcXTitled",
        "source_polarization_jx":"srcPolJx", "source_polarization_jy":"srcPolJy",
        "source_pre_propagation":"srcPrePropagation", "inside_of_object":"InsideOfObject",
    }
    for key,name in names.items():
        value=getattr(q,key,None)
        if value is not None:setv(name,value)


def diff_efficiency_surface(row):
    result=dict(surface_type=str(row.Type),material=str(row.Material))
    if result['surface_type']=='UserDefined':
        result['surface_file']=str(row.CurrentTypeSettings.Filename)
        if result['surface_file'].lower().endswith('us_hologram_kogelnik.dll'):
            result['numeric_limitations']=[dict(polarization='P',status='reference_deviation_observed',
                detail='Installed v242 DLL has an additional external direction-projection-squared factor in controlled off-axis tests; native Hologram1 passes the internal Kogelnik reference.',
                evidence='verification/development/CO-01/acceptance059.json')]
    return result


DIFF_EFFICIENCY_2D_TITLE='Diffraction efficiency versus angle and wavelength'


def label_diff_efficiency(data,kind):
    """Attach physical units and a display title to native diff-efficiency results.

    The native 2D description repeats its own swapped bounds
    ("最大波长 =  0.45，最小波长 = 0.65  (µm)"), which would become the plot title, so the
    displayed title is a neutral topical one while the native string is kept verbatim in
    native_description. Angles, wavelengths, values and units are left untouched.
    """
    for s in data['series']:
        s.setdefault('native_description',s.get('description',''))
        s.update(x_unit='degrees' if kind=='diff_efficiency_angular' else 'micrometers',
                 y_unit='dimensionless',value_quantity='diffraction efficiency')
    for g in data['grids']:
        g['native_axes']={key:g[key] for key in ('x_label','y_label','value_label','min_x','min_y','dx','dy')}
        g['native_description']=g.get('description','')
        g.update(x_label='Angle',y_label='Wavelength',value_label='Diffraction efficiency',
                 x_unit='degrees',y_unit='micrometers',value_unit='dimensionless',
                 description=DIFF_EFFICIENCY_2D_TITLE)

def configure_grin_profile(q,setv):
    setv("ShowIndexVs",q.show_index_vs)
    names={
        "minimum_x":"MinimumX", "maximum_x":"MaximumX", "minimum_y":"MinimumY",
        "maximum_y":"MaximumY", "minimum_z":"MinimumZ", "maximum_z":"MaximumZ",
        "x_value":"X_Value", "y_value":"Y_Value", "z_value":"Z_Value",
        "minimum_index":"MinimumIndex", "maximum_index":"MaximumIndex",
    }
    for key,name in names.items():
        value=getattr(q,key)
        if value is not None:setv(name,value)


def grin_source_context(backend,surface):
    row=backend._row(surface)
    context=dict(surface=surface,surface_type=str(row.Type),material=str(row.Material),
        thickness=float(row.Thickness),semi_diameter=float(row.SemiDiameter),
        configuration=int(backend.system.MCE.CurrentConfiguration),
        source='formal active surface and system-file readback before native analysis')
    if context['surface_type']=='Gradium':
        names=['maximum_step','axial_offset','reference_vertex_index','decenter_x','decenter_y','tilt_x','tilt_y','capping']
        context['gradium']={key:float(backend._cell(row,'parameter_'+str(i)).DoubleValue)for i,key in enumerate(names,1)}
        context['gradium']['profile_file']=str(backend.system.SystemData.Files.GradiumProfile)
        context['gradium']['reference_index_definition']='vertex index at the SGRIN family reference wavelength; separate from the selected system wavelength'
        # Declared GRD/SGRIN metadata only. This is auxiliary provenance: any problem is
        # reported as a status record and never prevents the profile query from running.
        try:
            from .gradium import resource_metadata
            context['gradium']['resource_metadata']=resource_metadata(
                getattr(getattr(backend,'native',None),'application',None),
                context['gradium']['profile_file'],context['material'])
        except Exception as exc:
            context['gradium']['resource_metadata']=dict(status='unavailable',reason=f'metadata unavailable: {exc}')
    return context


def label_grin_profile(data,requested,lens_unit):
    if not data['series']:
        raise ZemaxError('NO_RESULT_DATA','GRIN profile returned no native curve.')
    data['analysis_kind']='grin_profile'
    for curve in data['series']:
        if not curve['x'] or any(len(row)!=1 for row in curve['y']):
            raise ZemaxError('INVALID_RESULT_DATA','GRIN profile must contain one index column.',series=curve['series'])
        curve['native_axes']=dict(x_label=curve['x_label'],labels=curve['labels'])
        curve.update(x_label=requested['show_index_vs'],labels=['Refractive index'],x_unit=lens_unit,
            y_unit='dimensionless',coordinate_frame='selected surface local coordinates',
            wavelength_number=requested.get('wavelength',1),
            index_definition='native profile index at the selected system wavelength')

def configure_contrast_loss(q,setv):
    for name,value in [('SampleSize',q.sampling),('Frequency',q.frequency),('Normalize',q.normalize),('ShowOPD',q.show_opd)]:setv(name,value)


def verify_quick_yield(native,settings,request):
    """Check the final combination after native field selection has completed."""
    from .imaging import check
    from .detectors import check_setting_value
    for name,value in [('Configuration',request.configuration),('NumMonteCarlo',request.monte_carlo_samples),
                       ('PupilSampling',request.pupil_sampling),('Statistic',request.statistic),
                       ('Precision',request.precision),('Compensation',request.compensation),
                       ('CompensatorStrategy',request.compensator_strategy)]:
        check(native,settings,name,value)
    check_setting_value('QYField.IsFieldUser',True,bool(settings.QYField.IsFieldUser))
    check_setting_value('QYField',request.field,int(settings.QYField.GetFieldUser()))
    check_setting_value('Wavelength',request.wavelength,int(settings.Wavelength.GetWavelengthNumber()))


def describe_quick_yield(data,request,system_settings=None):
    if not data.get('series'):
        raise ZemaxError('NO_RESULT_DATA','QuickYield没有返回良率曲线。')
    for curve in data['series']:
        if not curve['x']or len(curve['x'])!=len(curve['y'])or any(v is None or not math.isfinite(v)or v<0 for v in curve['x']):
            raise ZemaxError('INVALID_RESULT_DATA','QuickYield波前轴须为有限非负RMS，且与良率行数一致。',
                series=curve['series'],native_x=curve['x'])
        if len(curve['labels'])!=1 or any(len(row)!=1 or row[0] is None or
                not math.isfinite(row[0]) or not 0<=row[0]<=100 for row in curve['y']):
            raise ZemaxError('INVALID_RESULT_DATA','QuickYield良率列须为有限的百分比。',series=curve['series'])
        curve.update(x_unit='waves',value_units=['percent'],y_unit='percent',
                     value_quantity='cumulative yield',metric='RMS wavefront')
    data.update(analysis_kind='quick_yield',evaluation=dict(metric='RMS wavefront',unit='waves',
        field_selection=request['field'],wavelength_selection=request['wavelength'],
        configuration_selection=request['configuration'],statistic=request['statistic'],
        source='native QuickYield sensitivity fit; requested selectors read back; native text retained',
        reference_equivalence=dict(
            status='controlled empirical equivalence; internal reconstruction is proprietary',
            selected_wavelength_model='Cooke reference agrees after primary-wavelength-dependent solves are evaluated at the selected wavelength',
            tilt='controlled refractor agrees with equal-area OPD RMS after least-squares piston and linear pupil tilt removal',
            precision='Standard high-order approximation errors retained; VeryHigh r6-r12 references passed original tolerance',
            source_model_preservation='native analysis leaves active source settings and solves unchanged',
            evidence='verification/development/TO-01/acceptance574-reference.json')))
    if system_settings:
        wavelengths=system_settings.get('wavelengths',[])
        selected=request['wavelength']
        data['evaluation']['source_wavelengths']=dict(
            primary_number=next((w['number']for w in wavelengths if w.get('primary')),None),
            selected_number=selected,selected_um=next((w['wavelength_um']for w in wavelengths if w['number']==selected),None))


def configure_seidel_diagram(q,setv):
    for name,value in [('IgnoreChromatic',q.ignore_chromatic),('IgnoreDistortion',q.ignore_distortion),
                       ('SuppressFrame',q.suppress_frame),('PlotScale',q.plot_scale)]:
        setv(name,value)


def configure_rms_wavelength(q,setv):
    density = 'RayDens_'+str(q.rings or 3) if q.method=='GaussQuad' else 'RayDens_'+(q.sampling or 'S_64x64').removeprefix('S_')
    for name,value in [('Method',q.method),('RayDensity',density),
                       ('WaveDensity','WaveDens_'+str(q.wavelength_density)),
                       ('Data','StrehlRation' if q.data_type=='StrehlRatio' else q.data_type),
                       ('ReferTo',q.reference),('UseDashes',q.use_dashes),
                       ('ShowDiffractionLimit',q.show_diffraction_limit),
                       ('UsePolarization',q.use_polarization),('PlotScale',q.plot_scale)]:
        setv(name,value)


def map_rms_wavelength_series(data,request):
    if not data.get('series'):
        raise ZemaxError('NO_RESULT_DATA','RMS wavelength analysis returned no native series.')
    metric=request['data_type']
    unit='waves' if metric=='Wavefront' else 'dimensionless' if metric=='StrehlRatio' else 'micrometers'
    data['analysis_kind']='rms_vs_wavelength'
    for item in data['series']:
        item.update(x_unit='micrometers',value_units=[unit]*len(item['labels']),
                    data_type=metric,field_selection=request['field'],
                    actual_point_count=len(item['x']),native_labels=list(item['labels']),
                    wavelength_definition='native continuous wavelength scan; each point monochromatic')


def native_setting(native, settings, name, value):
    p=settings.GetType().GetProperty(name)
    if p is None or not p.CanWrite:
        raise ZemaxError("UNSUPPORTED_SETTING", "本机分析不支持此设置。", setting=name)
    if p.PropertyType.IsEnum: native.set_enum(settings,name,value)
    else:
        kind=str(p.PropertyType.FullName)
        if kind=="System.Boolean" and type(value) is not bool:
            raise ZemaxError("INVALID_ARGUMENT","此设置需要布尔值。",setting=name)
        if kind in {"System.Int32","System.Int64","System.UInt32"}:
            if type(value) not in {int,float} or not math.isfinite(value) or int(value)!=value:
                raise ZemaxError("INVALID_ARGUMENT","此设置需要整数。",setting=name)
            value=int(value)
        setattr(settings,name,value)


class AnalysesMixin:
    def run_analysis(self, req):
        q=req.request
        if q.kind == 'phase_aberration':
            from .phase_copy import uses_copy, run_phase_copy
            if uses_copy(q):
                return run_phase_copy(self, q)
        if q.kind == 'polarization_ray_trace':
            from .polarization_operand import uses_operand, run_polarization_operand
            if uses_operand(q):
                return run_polarization_operand(self, q)
        if q.kind == 'fiber_coupling_settings':
            from .fiber_operand import uses_operand, run_fiber_operand
            if uses_operand(q):
                return run_fiber_operand(self, q)
        if q.kind in {'extended_diffraction_image','partially_coherent_image'}:
            from .scene_images import run_scene_image
            return run_scene_image(self,q)
        if q.kind=="ray_database_viewer":
            from .ray_database import run_viewer
            return run_viewer(self,q)
        if q.kind=="ima_bim_viewer":
            from .ima_viewer import run_viewer
            return run_viewer(self,q)
        if q.kind in {"power_field_map","power_pupil_map"}:
            from .power_maps import run_power_map
            return run_power_map(self,q)
        if q.kind=='test_plate_list':
            from .test_plates import run_test_plates
            return run_test_plates(self,q)
        if q.kind=='biocular_field_of_view':
            from .biocular_fov import run_fov
            return run_fov(self,q)
        if q.kind=='biocular_dipvergence_convergence':
            from .biocular import run_biocular
            return run_biocular(self,q)
        if q.kind=='yybar_diagram':
            from .ray_diagrams import run_yybar
            return run_yybar(self,q)
        if q.kind=='incident_angle_vs_image_height':
            from .ray_diagrams import run_incident_angle
            return run_incident_angle(self,q)
        if q.kind=='sag_table':
            from .sag_table import run_sag_table
            return run_sag_table(self,q)
        if q.kind in {'paraxial_gaussian_beam','skew_gaussian_beam'}:
            from .gaussian_beams import run_gaussian
            return run_gaussian(self,q)
        if q.kind=='seidel_diagram':
            from .seidel_diagram import run_seidel_diagram
            return run_seidel_diagram(self,q)
        if q.kind=="full_field_spot":
            from .spot_topics import run_full_field
            return run_full_field(self,q)
        if q.kind in {'dispersion_diagram','dispersion_vs_wavelength'}:
            from .material_index import uses_index,run_material_index
            if uses_index(q):return run_material_index(self,q)
        if q.kind=="pupil_aberration_fan":
            from .pupil_topics import run_pupil
            return run_pupil(self,q)
        if q.kind in {"system_check","system_data"}:
            from .system_check import run_system_check
            return run_system_check(self,q)
        if q.kind in {"prescription_data","surface_data"}:
            from .native_text_reports import run_text_report
            return run_text_report(self,q)
        if q.kind in {"star_align_check","star_sys_viewer","star_2d_def_plot",
                      "star_perf_change","star_index_vs_temp","star_inspect_fea"}:
            from .star_analyses import run_star_analysis
            return run_star_analysis(self,q)
        if q.kind=="file_comparator":
            from .comparator import run_comparator
            return run_comparator(self,q)
        if q.kind=='polarization_pupil_map':
            from .polarization import run_pupil_map
            return run_pupil_map(self,q)
        if q.kind=='nsc_geometric_mtf':
            from .nsc_mtf import run_nsc_mtf
            return run_nsc_mtf(self,q)
        if q.kind=='nsc_surface_sag':
            from .nsc_analyses import run_nsc_surface_sag
            return run_nsc_surface_sag(self,q)
        if q.kind in {'critical_ray_trace','nsc_single_ray_trace'}:
            from .nsc_analyses import run_nsc_analysis
            return run_nsc_analysis(self,q)
        if q.kind=='path_analysis':
            from .path_analysis import run_path_analysis
            return run_path_analysis(self,q)
        if q.kind=="universal_plot_2d":
            from .universal_grid import run
            return run(self,q)
        if q.kind=="universal_plot_1d":
            from .universal import run
            return run(self,q)
        if q.kind=="internal_transmission_vs_wavelength":
            from .materials import run_internal_transmission
            return run_internal_transmission(self,q)
        if isinstance(q,(CoatingAngle,CoatingWavelength,CoatingListing)):
            from .coatings import run_coating
            return run_coating(self,q)
        if q.kind in {"image_simulation", "geometric_image", "geometric_bitmap_image", "fft_line_edge_spread", "geometric_line_edge_spread", "extended_source_encircled_energy"}:
            from .imaging import run_imaging
            return run_imaging(self,q)
        if q.kind=="through_focus_spot":
            from .rms_analyses import through_focus_spot
            return through_focus_spot(self,q)
        if q.kind=="cardinal_points":
            from .basic_analyses import cardinal_points
            return cardinal_points(self,q)
        if q.kind=='yni_contributions' and q.wavelength is not None:
            from .basic_analyses import yni_operands
            return yni_operands(self,q)
        if q.kind=='polarization_transmission':
            from .transmission_pupil import uses_batch,transmission_pupil
            if uses_batch(q):return transmission_pupil(self,q)
        if q.kind=='polarization_transmission_fan':
            from .transmission_fan import uses_batch,transmission_fan
            if uses_batch(q):return transmission_fan(self,q)
        if q.kind in {"vignetting","footprint"}:
            from .field_analyses import sampled_analysis
            return sampled_analysis(self,q)
        if q.kind=='wavefront'and q.include_pupil_mapping:return self._wavefront_mapping_task(q)
        return self._run_general_analysis(q)

    def _run_general_analysis(self,q):
        if q.kind not in {'source_spectrum_viewer','directivity_plot'}:
            self._require_sequential(focused=q.kind not in {"single_ray_trace","seidel_coefficients","seidel_diagram","grin_profile",*SLOPE_ANALYSES})
        if hasattr(q,"field") and q.field>self.system.SystemData.Fields.NumberOfFields:
            raise ZemaxError("INDEX_OUT_OF_RANGE","视场越界。")
        if getattr(q,"wavelength",None) is not None and q.wavelength>self.system.SystemData.Wavelengths.NumberOfWavelengths:
            raise ZemaxError("INDEX_OUT_OF_RANGE","波长越界。")
        if getattr(q,"surface",None) is not None: self._row(q.surface)
        if q.kind=='interferogram':
            from .wavefront_topics import check_interferogram_configurations
            check_interferogram_configurations(q,int(self.system.MCE.NumberOfConfigurations))
        if q.kind=='foucault' and q.source is not None:
            source=Path(q.source).expanduser().resolve()
            if source.suffix.lower()!='.bmp':
                raise ZemaxError('INVALID_ARGUMENT','Foucault Source 需要 BMP 文件。',source=str(source))
            if not source.is_file():
                raise ZemaxError('FILE_NOT_FOUND','Foucault 参考图像不存在。',source=str(source))
        native_id=self.native.enum(self.native.api.Analysis.AnalysisIDM,ANALYSES[q.kind])
        factory=getattr(self.system.Analyses,'New_Analysis_SettingsFirst',self.system.Analyses.New_Analysis) if q.kind in {'rms_vs_field','rms_field_map','rms_vs_focus','rms_vs_wavelength','through_focus_spot'} else self.system.Analyses.New_Analysis
        tool=factory(native_id)
        try:
            s=unwrap(tool.GetSettings())
            if q.kind=="grid_distortion":s.Reset()
            for key, setter, reader in (("field","SetFieldNumber","GetFieldNumber"),("wavelength","SetWavelengthNumber","GetWavelengthNumber"),("surface","SetSurfaceNumber","GetSurfaceNumber")):
                if hasattr(q,key) and getattr(q,key) is not None and q.kind not in {'polarization_transmission_fan','polarization_transmission','fiber_coupling_settings','polarization_ray_trace','seidel_diagram'} and not (q.kind=="quick_yield" and key=="field"):
                    obj=getattr(s,key.title())
                    getattr(obj,setter)(getattr(q,key))
                    if int(getattr(obj,reader)())!=getattr(q,key):
                        raise ZemaxError("SETTING_REJECTED","原生选择未采用请求值。",setting=key)
            if getattr(q,"surface",None) is None and hasattr(s,"Surface"):
                s.Surface.UseImageSurface()
            def setv(name,value):
                from .detectors import checked_setting
                checked_setting(self.native,s,name,value)
            if q.kind in {"matrix_spot","configuration_matrix_spot"}:
                for name,value in (("Pattern",q.pattern),("ReferTo",q.reference),("ShowScale",q.show_scale),
                                   ("ColorRaysBy",q.color_rays_by),("RayDensity",q.ray_density),
                                   ("DirectionCosines",q.direction_cosines),("UseSymbols",q.use_symbols),
                                   ("UsePolarization",q.use_polarization),("ScatterRays",q.scatter_rays),
                                   ("ShowAiryDisk",q.show_airy_disk),("IgnoreLateralColor",q.ignore_lateral_color)):
                    setv(name,value)
            if q.kind=="foucault":
                setv('Source',str(source) if q.source is not None else '')
                for name,value in (("Type",q.intensity_scale),("ShowAs",q.show_as),("Knife",q.knife),
                                   ("Data",q.data),("RowColumn",q.row_column),("UsePolarization",q.use_polarization),
                                   ("Y_Position",q.y_position),("Decenter_X",q.decenter_x),("Decenter_Y",q.decenter_y),
                                   ("Scale_X",q.scale_x),("Scale_Y",q.scale_y)):
                    setv(name,value)
            if q.kind=="full_field_aberration":
                for name,value in (("FieldShape",q.field_shape),("XFieldWidth",q.x_field_width),
                                   ("YFieldWidth",q.y_field_width),("Decomposition",q.decomposition),
                                   ("MaximumTerm",q.maximum_term),("XFieldSampling",q.x_field_sampling),
                                   ("YFieldSampling",q.y_field_sampling),("PupilSampling",q.pupil_sampling),
                                   ("ShowAs",q.show_as),("Display",q.display)):
                    setv(name,value)
                if q.aberration_type=="SpecifiedTerm":
                    accepted=s.SetAberrationByNumber(q.aberration_number)
                else:
                    enum_type=self.native.api.Analysis.Settings.Aberrations.FFA_AberrationTypes
                    accepted=s.SetAberrationByType(self.native.enum(enum_type,q.aberration_type))
                if not accepted:
                    raise ZemaxError("SETTING_REJECTED","Full Field Aberration 未接受像差选择。",aberration_type=q.aberration_type,aberration_number=q.aberration_number)
                actual_type=str(s.AberrationType)
                actual_number=int(s.AberrationNumber)
                expected_type=q.aberration_type
                if expected_type!="SpecifiedTerm" and actual_type!=expected_type:
                    raise ZemaxError("SETTING_REJECTED","Full Field Aberration 像差类型回读不匹配。",requested=expected_type,actual=actual_type)
                if expected_type=="SpecifiedTerm" and actual_number!=q.aberration_number:
                    raise ZemaxError("SETTING_REJECTED","Full Field Aberration 项编号回读不匹配。",requested=q.aberration_number,actual=actual_number)
            if q.kind=="fft_surface_mtf":
                for name,value in (("Type",q.mtf_type),("Rotation",q.rotation),("SampleSize",q.sampling),
                                   ("ShowAs",q.show_as),("UsePolarization",q.use_polarization),
                                   ("ScaleFactor",q.scale_factor)):
                    setv(name,value)
            if q.kind in {"diff_efficiency_2d","diff_efficiency_angular","diff_efficiency_chromatic"}:
                configure_diff_efficiency(q,setv)
            if q.kind=="grin_profile":
                configure_grin_profile(q,setv)
            if q.kind=="huygens_surface_mtf":
                for name,value in (("ImageSampleSize",q.image_sampling),("PupilSampleSize",q.sampling),
                                   ("Type",q.mtf_type),("ShowAs",q.show_as),
                                   ("UsePolarization",q.use_polarization),("ImageDelta",q.image_delta),
                                   ("Configuration",self.system.MCE.CurrentConfiguration)):
                    setv(name,value)
            if hasattr(q,"sampling") and not q.kind.startswith("rms_vs_") and q.kind not in {*SLOPE_ANALYSES,'rms_field_map','interferogram','zernike_coefficients_vs_field','polarization_transmission_fan','polarization_transmission','fiber_coupling_settings','polarization_ray_trace'}:
                sample=q.sampling
                if q.kind=="fft_psf":
                    setv("SampleSize",sample.replace("S_","PsfS_")); setv("OutputSize",q.image_sampling.replace("S_","PsfS_"))
                elif q.kind.startswith("huygens_") and q.kind!="huygens_mtf_vs_field":
                    setv("PupilSampleSize",sample)
                    setv("ImageSampleSize",getattr(q,"image_sampling",sample))
                else:
                    if q.kind.endswith("_cross") and q.kind.startswith("surface_"):
                        sample=sample.split("x")[0]
                    setv("Sampling" if q.kind in {"wavefront","foucault","surface_sag","surface_curvature","surface_phase","surface_sag_cross","surface_curvature_cross","surface_phase_cross"} else "SampleSize",sample)
            mapping=dict(maximum_frequency="MaximumFrequency",frequency="Frequency",delta_focus="DeltaFocus",number_of_steps="NumberOfSteps",use_polarization="UsePolarization",image_delta="ImageDelta",normalize="Normalize",reference="ReferTo",maximum_radius="RadiusMaximum",remove_tilt="RemoveTilt",use_exit_pupil="UseExitPupil",maximum_terms="MaximumNumberOfTerms",number_of_rays="NumberOfRays",check_apertures="CheckApertures",vignetted_pupil="VignettedPupil",ignore_vignette="IgnoreVignette")
            for key,name in mapping.items():
                if hasattr(q,key):
                    if q.kind in {"fiber_coupling_settings","polarization_ray_trace"}: continue
                    if q.kind=="fiber_coupling_settings": continue
                    if key=="image_delta" and q.kind=="geometric_mtf": continue
                    if key=="image_delta" and q.kind=="fft_psf_cross": continue
                    setv(name,getattr(q,key))
            if q.kind=="quick_yield":
                if q.configuration > int(self.system.MCE.NumberOfConfigurations):
                    raise ZemaxError("INDEX_OUT_OF_RANGE","配置编号越界。",configuration=q.configuration,count=int(self.system.MCE.NumberOfConfigurations))
                for name,value in (("Configuration",q.configuration),("NumMonteCarlo",q.monte_carlo_samples),
                                   ("PupilSampling",q.pupil_sampling),("Statistic",q.statistic),
                                   ("Precision",q.precision),("Compensation",q.compensation),
                                   ("CompensatorStrategy",q.compensator_strategy)):
                    setv(name,value)
                message=s.QYField.SetFieldUser(q.field)
                if message is not None and int(message.ErrorCode)!=0:
                    raise ZemaxError("SETTING_REJECTED","Quick Yield 未接受用户视场。",setting="QYField",field=q.field,code=str(message.ErrorCode),message=str(message.Text))
                actual_field=int(s.QYField.GetFieldUser())
                if actual_field!=q.field:
                    raise ZemaxError("SETTING_REJECTED","Quick Yield 用户视场回读不匹配。",requested=q.field,actual=actual_field)
            if q.kind in {"tolerance_yield","tolerance_histogram"}:
                if q.tolerance_file is None:
                    s.UseSystemTolerances()
                    tolerance_source="system"
                else:
                    available=[str(x) for x in s.GetToleranceFiles()]
                    if q.tolerance_file not in available:
                        raise ZemaxError("INVALID_RESOURCE","原生公差分析未列出所选文件。",requested=q.tolerance_file,available=available)
                    setv("Filename",q.tolerance_file)
                    tolerance_source="file"
                operands=s.GetOperands()
                count=int(operands.NumberOfOperands)
                native_operand=tolerance_operand_number(q.operand,count)
                setv("Operand",native_operand)
                if q.kind=="tolerance_histogram":
                    for name,value in (("MinValue",q.minimum),("MaxValue",q.maximum),("NumBins",q.bins)):
                        setv(name,value)
            if q.kind=="geometric_mtf": setv("MultiplyByDiffractionLimit",q.multiply_by_diffraction_limit)
            if q.kind in {"geometric_through_focus_mtf","geometric_encircled_energy"}:
                # 2024 R2 names the energy multiplication switch ShowDiffractionLimit.
                value=True if q.multiply_by_diffraction_limit is None else q.multiply_by_diffraction_limit
                setv("ShowDiffractionLimit"if q.kind=="geometric_encircled_energy"else"MultiplyByDiffractionLimit",value)
            if q.kind=="huygens_mtf" or q.kind.endswith("through_focus_mtf") and q.kind!="geometric_through_focus_mtf": setv("Type","Modulation")
            if q.kind in {"huygens_mtf","huygens_through_focus_mtf","huygens_psf","huygens_psf_cross","huygens_surface_mtf"}:
                setv("Configuration",self.system.MCE.CurrentConfiguration)
            if q.kind in {"huygens_psf","huygens_psf_cross"}: setv("UseCentroid",False)
            if q.kind=="zernike_annular": setv("Obscuration",q.obscuration)
            if q.kind=="zernike_standard": setv("Epsilon",q.obscuration)
            if q.kind in {'zernike_standard','zernike_fringe','zernike_annular'}:
                setv("ReferenceOBDToVertex",False)
                for name,value in (("Sx",0.),("Sy",0.),("Sr",1.)):setv(name,value)
            if q.kind.startswith("surface_") and q.kind.endswith("_cross") and q.kind not in SLOPE_ANALYSES: setv("Angle",q.angle)
            if q.kind in SLOPE_ANALYSES:
                configure_surface_slope(q,setv)
                desired={};configure_surface_slope(q,desired.__setitem__)
                from .imaging import check
                for name,value in desired.items():check(self.native,s,name,value)
            if q.kind in {'interferogram','zernike_coefficients_vs_field'}:
                from .wavefront_topics import configure_interferogram,configure_zernike_field
                (configure_interferogram if q.kind=='interferogram' else configure_zernike_field)(q,setv)
                if q.kind=='zernike_coefficients_vs_field':
                    from .imaging import check
                    configure_zernike_field(q,lambda name,value:check(self.native,s,name,value))
                    if int(s.Wavelength.GetWavelengthNumber())!=q.wavelength:
                        raise ZemaxError('SETTING_REJECTED','Zernike波长最终回读不匹配。',requested=q.wavelength,actual=int(s.Wavelength.GetWavelengthNumber()))
            if q.kind=="relative_illumination" or q.kind.endswith("_mtf_vs_field"):
                setv("ScanType",q.scan_type)
                setv("FieldDensity",q.field_density)
                setv("RemoveVignettingFactors" if q.kind=="relative_illumination" else "RemoveVignetting",q.remove_vignetting_factors)
                if q.kind=="relative_illumination":
                    setv("RayDensity",q.ray_density)
                    setv("LogScale",q.log_scale)
                else:
                    setv("UseDashes",False)
                    for i in range(6):setv("Freq_"+str(i+1),q.frequencies[i] if i<len(q.frequencies) else 0.)
            if q.kind=="geometric_mtf_vs_field":
                setv("MultiplyByDiffractionLimit",q.multiply_by_diffraction_limit)
                setv("ScatterRays",q.scatter_rays)
            if q.kind.endswith("_mtf_map"):
                if q.reference_field>self.system.SystemData.Fields.NumberOfFields:raise ZemaxError("INDEX_OUT_OF_RANGE","参考视场越界。")
                s.ReferenceField.SetFieldNumber(q.reference_field)
                if s.ReferenceField.GetFieldNumber()!=q.reference_field:raise ZemaxError("SETTING_REJECTED","参考视场未采用。")
                for name,value in (("X_Field_Width",q.x_field_width),("Y_Field_Width",q.y_field_width),("X_Pixels",q.x_pixels),("Y_Pixels",q.y_pixels),("MTF_DataType",q.data_type),("ShowAs","FalseColor"),("RemoveVignetting",q.remove_vignetting_factors)):
                    setv(name,value)
                if q.kind=="geometric_mtf_map":setv("ScatterRays",q.scatter_rays)
            if q.kind=='single_ray_trace':
                s.UseArbitraryRay()
                for name,value in [('Hx',q.hx),('Hy',q.hy),('Px',q.px),('Py',q.py),('UseGlobal',q.use_global),('Type',q.ray_type)]:setv(name,value)
            if q.kind=='grid_distortion':
                if q.reference_field>self.system.SystemData.Fields.NumberOfFields:raise ZemaxError('INDEX_OUT_OF_RANGE','参考视场越界。')
                s.Field.SetFieldNumber(q.reference_field)
                if s.Field.GetFieldNumber()!=q.reference_field:raise ZemaxError('SETTING_REJECTED','参考视场未采用。')
                for name,value in [('FieldWidth',q.field_width),('Aspect',q.aspect),('ScaleFactor',q.scale_factor),('SymmetricMagnification',q.symmetric_magnification)]:setv(name,value)
                if q.grid_number is not None:setv('GridNumber',q.grid_number)
            if q.kind in {'rms_vs_field','rms_vs_focus'}:
                from .rms_analyses import rms_settings
                rms_settings(self.native,s,q)
            if q.kind=='rms_vs_wavelength':
                configure_rms_wavelength(q,setv)
                desired={};configure_rms_wavelength(q,desired.__setitem__)
                from .imaging import check
                from .detectors import check_setting_value
                for name,value in desired.items():check(self.native,s,name,value)
                check_setting_value('Field',q.field,int(s.Field.GetFieldNumber()))
            if q.kind=='rms_field_map':
                from .rms_analyses import rms_map_settings
                rms_map_settings(self.native,s,q)
                from .detectors import check_setting_value
                check_setting_value('Field',q.field,int(s.Field.GetFieldNumber()))
                check_setting_value('Wavelength',q.wavelength,int(s.Wavelength.GetWavelengthNumber()))
                check_setting_value('Surface',q.surface if q.surface is not None else 0,int(s.Surface.GetSurfaceNumber()))
            if q.kind=='contrast_loss':configure_contrast_loss(q,setv)
            if q.kind=='seidel_diagram':configure_seidel_diagram(q,setv)
            if q.kind=='through_focus_spot':
                from .spot_topics import CURRENT_CONFIGURATION_SELECTOR
                for name,value in [('ReferTo',q.reference),('Pattern',q.pattern),('RayDensity',q.ray_density),('DeltaFocus',q.delta_focus_um),('Configuration',CURRENT_CONFIGURATION_SELECTOR),('DirectionCosines',False),('IgnoreLateralColor',False),('ScatterRays',False)]:setv(name,value)
            if q.kind=='quick_yield':verify_quick_yield(self.native,s,q)
            actual={"kind":q.kind,"requested":q.model_dump(exclude_unset=q.kind=='seidel_diagram'),"native":scalar_settings(s)}
            if q.kind=='through_focus_spot':actual['resolved_configuration']=int(self.system.MCE.CurrentConfiguration)
            if q.kind in TOPIC_KINDS:
                actual["settings_type"]=str(s.GetType().FullName)
                actual["settings_note"]="native settings object exposes no topic-specific selector; inputs are read back from the native report header"
            if q.kind=='grin_profile':actual['source_surface']=grin_source_context(self,q.surface)
            if q.kind.startswith('diff_efficiency_') and q.surface is not None:
                actual['evaluation_conditions']=diff_efficiency_surface(self._row(q.surface))
            if q.kind in {"tolerance_yield","tolerance_histogram"}:
                from .imaging import check
                check(self.native,s,'Operand',native_operand)
                if q.tolerance_file is not None:check(self.native,s,'Filename',q.tolerance_file)
                if q.kind=='tolerance_histogram':
                    for name,value in [('MinValue',q.minimum),('MaxValue',q.maximum),('NumBins',q.bins)]:check(self.native,s,name,value)
                actual["tolerance_source"]=tolerance_source
                actual["operand_selection"]=dict(public_index=q.operand,native_index=native_operand,count=count)
        except Exception:
            self._release_owned(tool)
            raise
        return self._start_task("analysis",tool,actual,analysis=True,collector=self._collect_general_analysis)

    def _collect_general_analysis(self,task):
        r=unwrap(task["native"].GetResults())
        if r is None:
            raise ZemaxError("ANALYSIS_FAILED","没有有效原生分析结果。")
        header=[str(x) for x in r.HeaderData.Lines] if r.HeaderData is not None and r.HeaderData.Lines is not None else []
        if not r.IsValid:
            raise ZemaxError("ANALYSIS_FAILED","没有有效原生分析结果。",
                native_messages=[dict(code=str(r.GetMessageAt(i).ErrorCode),text=str(r.GetMessageAt(i).Text)) for i in range(r.NumberOfMessages)],
                native_header=header)
        path=self.directory/(task["task_id"]+"_native.txt")
        if not r.GetTextFile(str(path)):
            if task.get('settings',{}).get('kind')=='through_focus_spot':
                return dict(analysis_kind='through_focus_spot',native_text_exported=False,native_export_error='GetTextFile returned false',
                    native_header=header,native_messages=[dict(code=str(r.GetMessageAt(i).ErrorCode),text=str(r.GetMessageAt(i).Text)) for i in range(r.NumberOfMessages)],artifacts=[],structured_data_available=False)
            raise ZemaxError("EXPORT_FAILED","原生分析文本导出失败。")
        text=path.read_text(encoding="utf-16")
        preamble=[]
        for line in text.splitlines():
            if re.match(r"^\s*[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?\s+[-+]?\d",line)or re.match(r"^\s*Z\s+\d",line):break
            preamble.append(line)
        data={"native_header":header,
              "native_messages":[{"code":str(r.GetMessageAt(i).ErrorCode),"text":str(r.GetMessageAt(i).Text)} for i in range(r.NumberOfMessages)],
              "artifacts":[{"kind":"native_text","path":str(path)}],"series":[],"grids":[],
              "units_source":"原生轴标签、ValueLabel 和 native_header；不得对不同分析统一套用镜头单位。"}
        data["native_preamble"]=preamble
        data["computation_method"]="native_analysis"
        for i in range(r.NumberOfDataSeries):
            s=r.GetDataSeries(i)
            if s is None or s.XData is None or s.YData is None:
                raise ZemaxError('NO_RESULT_DATA','原生分析返回了没有坐标或数值的曲线。',series=i,
                    native_messages=data['native_messages'],native_preamble=preamble,native_text=str(path))
            x=dotnet_array(s.XData.Data); y=dotnet_array(s.YData.Data)
            if len(x)!=len(y) or any(not math.isfinite(v) for v in x):
                raise ZemaxError("INVALID_RESULT_DATA","曲线尺寸不一致或横轴包含非有限值。",series=i,x_count=len(x),y_count=len(y))
            invalid=sum(not math.isfinite(v) for row in y for v in row)
            width=len(y[0]) if y else 0
            labels=[str(label) for label in s.SeriesLabels] if s.SeriesLabels is not None else ['column_'+str(j+1) for j in range(width)]
            if len(labels)!=width or any(len(row)!=width for row in y):
                raise ZemaxError('INVALID_RESULT_DATA','曲线数值列数与原生标签不一致。',series=i,labels=labels,value_columns=width)
            data["series"].append(dict(series=i,description=str(s.Description),x_label=str(s.XLabel),labels=labels,x=x,y=[[v if math.isfinite(v) else None for v in row] for row in y],invalid_count=invalid,
                labels_source='native' if s.SeriesLabels is not None else 'generated column indices; native SeriesLabels is null'))
        for i in range(r.NumberOfDataGrids):
            g=r.GetDataGrid(i)
            array=dotnet_array(g.Values)
            invalid=sum(not math.isfinite(v) for row in array for v in row)
            data["grids"].append(dict(grid=i,description=str(g.Description),x_label=str(g.XLabel),y_label=str(g.YLabel),value_label=str(g.ValueLabel),nx=int(g.Nx),ny=int(g.Ny),dx=float(g.Dx),dy=float(g.Dy),min_x=float(g.MinX),min_y=float(g.MinY),values=[[v if math.isfinite(v) else None for v in row] for row in array],invalid_count=invalid,array_order="native Values dimension 0, dimension 1"))
        data["structured_data_available"]=bool(data["series"] or data["grids"])
        settings=task.get("settings",{})
        kind=settings.get("kind","")
        if kind in TOPIC_KINDS:
            try:
                data.update(parse_topic_text(kind,text,dict(system_settings=task.get("system_settings"),requested_kind=kind,
                    native_settings=settings.get("native"),native_settings_type=settings.get("settings_type","AS_Default"))))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind in {'tolerance_yield','tolerance_histogram'}:
            from .tolerance_distributions import describe_distribution
            describe_distribution(data,kind,text)
        if kind=='quick_yield':describe_quick_yield(data,settings['requested'],task.get('system_settings'))
        if kind=='dispersion_diagram':
            try:data.update(parse_dispersion_diagram(text))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='dispersion_vs_wavelength':
            try:data.update(parse_dispersion_vs_wavelength(text))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='yni_contributions':
            from .basic_analyses import parse_yni_contributions
            try:
                parsed=parse_yni_contributions(text,task.get('context',{}).get('lens_units','unknown'))
                data.update(parsed)
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='source_spectrum_viewer':
            from .basic_analyses import parse_source_spectrum
            try:
                data.update(parse_source_spectrum(text))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='directivity_plot':
            from .basic_analyses import parse_directivity_plot
            try:
                data.update(parse_directivity_plot(text))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='polarization_transmission_fan':
            from .basic_analyses import parse_polarization_transmission_fan
            try:
                data.update(parse_polarization_transmission_fan(text))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='glass_map':
            try:data.update(parse_glass_map(text))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='athermal_glass_map':
            try:data.update(parse_athermal_glass_map(text))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind in {'fft_surface_mtf','huygens_surface_mtf'}:
            from .surface_mtf import describe_surface_mtf
            describe_surface_mtf(data,settings['requested'],task['system_settings']['mtf_units'])
        if kind.startswith('diff_efficiency_') and not data['structured_data_available']:
            raise ZemaxError('NO_RESULT_DATA','衍射效率分析没有返回曲线或网格；请检查体全息模型及原生消息。',
                native_messages=data['native_messages'],native_preamble=preamble,native_text=str(path))
        if kind.startswith('diff_efficiency_'):
            label_diff_efficiency(data,kind)
        if kind in {"fft_psf_cross","huygens_psf_cross"}and not data.get("series"):
            section=parse_psf_section(text)
            if section:data["series"]=[section];data["structured_data_available"]=True
        lens=task.get("system_settings",{}).get("lens_units","see native_preamble")
        if kind=='full_field_aberration':
            from .full_field_aberration import describe_full_field
            describe_full_field(data,settings['requested'],task.get('system_settings',{}))
        if kind=='foucault':
            data['foucault_conditions']=dict(data=settings['requested']['data'],
                knife_position_unit='micrometers',knife_position_reference='image-surface chief ray; X or Y selected by knife',
                reference_decenter_unit='fraction of full reference bitmap width/height',
                reference_scale_unit='reference-to-computed pixel size ratio',
                source=settings.get('native',{}).get('Source'),
                bitmap_export_status='SaveBMP accepted by native settings; no file produced in 2024 R2 probe297')
            for g in data['grids']:
                g['native_axes']={key:g[key] for key in ('x_label','y_label','value_label','min_x','min_y','dx','dy')}
                g.update(x_unit='native normalized display coordinate',y_unit='native normalized display coordinate',
                         x_label='Native display X',y_label='Native display Y',value_label=settings['requested']['data']+' shadowgram',
                         value_unit='dimensionless',value_quantity='native '+settings['requested']['data']+' shadowgram',
                         normalization='native shadowgram normalization; computed Linear reference uses maximum intensity')
        if kind=='grin_profile':label_grin_profile(data,settings['requested'],lens)
        for g in data["grids"]:
            if kind in {"fft_psf","huygens_psf"}:
                g.update(x_unit="micrometers",y_unit="micrometers",value_unit="relative irradiance",reference="native_preamble image-plane reference")
            elif kind=="wavefront":
                g.update(x_unit="normalized pupil",y_unit="normalized pupil",value_unit="waves",reference="chief-ray OPD; tilt removal in actual settings")
                # Circular entrance-pupil coordinates have an independently checked
                # guard-sample mapping. Exit-pupil shape uses its native display axes.
                g["native_axes"]={k:g[k]for k in ("min_x","min_y","dx","dy")}
                cx,cy=g["nx"]//2,g["ny"]//2
                exit_shape=settings.get("native",{}).get("UseExitPupil",True)
                g["pupil_frame"]="apparent exit pupil shape" if exit_shape else "normalized circular entrance pupil"
                if not exit_shape and cx>1 and cy>1:
                    g.update(min_x=-cx/(cx-1),min_y=-cy/(cy-1),dx=1/(cx-1),dy=1/(cy-1),
                             coordinate_definition="pupil=(index-floor(size/2))/(floor(size/2)-1); native guard samples retained",
                             coordinate_validation="entrance-pupil ray OPD reference")
                else:
                    g.update(coordinate_definition="native axes; exit-pupil shape must not be used as normalized entrance-ray inputs",
                             coordinate_validation="native metadata; exit-to-entrance pupil mapping not numerically verified")
                if settings.get("requested",{}).get("include_pupil_mapping",False):
                    g["pupil_mapping"]={"status":"unverified_exit_pupil_mapping"if exit_shape else"verified_entrance_guard_sample_formula",
                        "sample_order":"rows Y, columns X; grid values unchanged",
                        "validity_scope":"coordinate-domain validity only; not a per-ray aperture or propagation check",
                        "coordinate_error":None,"error_status":"no independent per-sample residual available",
                        "points":[[dict(px=None,py=None,valid=False,reason="exit-pupil mapping unverified")if exit_shape else
                            dict(px=(ix-cx)/(cx-1),py=(iy-cy)/(cy-1),valid=((ix-cx)/(cx-1))**2+((iy-cy)/(cy-1))**2<=1,
                                reason=None if ((ix-cx)/(cx-1))**2+((iy-cy)/(cy-1))**2<=1 else"outside circular entrance pupil")
                            for ix in range(g["nx"])]for iy in range(g["ny"])]}

            elif kind.startswith("surface_") and kind not in SLOPE_ANALYSES:
                value_unit=lens if kind=="surface_sag"else "1/"+lens if kind=="surface_curvature"else"cycles (2*pi radians)"
                g.update(x_unit=lens,y_unit=lens,value_unit=value_unit,reference="surface local X/Y")
        if kind=='rms_field_map':
            from .rms_analyses import map_rms_grid
            if not data['grids']:raise ZemaxError('NO_RESULT_DATA','RMS Field Map returned no native grid.',native_text=str(path))
            for grid in data['grids']:map_rms_grid(grid,settings['requested'],task['system_settings'],lens)
        if kind=='contrast_loss':
            from .contrast_loss import describe_contrast_loss
            try:describe_contrast_loss(data,settings['requested'],task.get('system_settings',{}).get('mtf_units'))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='seidel_diagram':
            data['analysis_kind']=kind
            data['result_definition']='native Seidel diagram; native labels, scales and text retained'
        if kind.endswith("_mtf_map"):
            from .mtf_results import map_grid
            if not data['grids']:raise ZemaxError('NO_RESULT_DATA','MTF Map没有原生网格。')
            data['analysis_kind']=kind
            for grid in data['grids']:map_grid(grid,settings['requested'],task['system_settings'])
        if kind=="relative_illumination" or kind.endswith("_mtf_vs_field"):
            if not data["series"]:raise ZemaxError("NO_RESULT_DATA","原生分析没有数值曲线。",native_text=str(path))
            data["analysis_kind"]=kind
            data["frequency_unit"]=task.get("system_settings",{}).get("mtf_units") if kind.endswith("_mtf_vs_field") else None
            data["requested_frequencies"]=settings["requested"].get("frequencies")
        for series_index,s in enumerate(data.get("series",[])):
            if kind.endswith("_mtf_vs_field"):
                from .mtf_results import curve_frequency
                try:s["frequency"]=curve_frequency(s['description'],settings["requested"]["frequencies"])
                except ZemaxError as exc:
                    exc.details['native_text']=str(path)
                    raise
                s["frequency_unit"]=data["frequency_unit"]
            if kind=="relative_illumination" or kind.endswith("_mtf_vs_field"):
                s.update(x_unit="normalized field" if kind.endswith("_mtf_vs_field") else "degrees" if task.get("system_settings",{}).get("field_type")=="Angle" else lens,value_units=["dimensionless"]*len(s["labels"]),axis_definition="native normalized field" if kind.endswith("_mtf_vs_field") else "native physical field coordinate")
            if kind.endswith("through_focus_mtf"):
                s.update(x_unit=lens,value_units=["dimensionless"]*len(s["labels"]),axis_definition="defocus versus tangential/sagittal modulation; native text headers retained")
            elif kind in {"huygens_mtf","geometric_mtf"}:
                s.update(x_unit=task.get("system_settings",{}).get("mtf_units"),value_units=["dimensionless"]*len(s["labels"]))
            elif kind in {"ray_fan","opd_fan","longitudinal_aberration","lateral_color","diffraction_encircled_energy","geometric_encircled_energy","focal_shift"}:
                xunit="micrometers"if"encircled_energy"in kind else"micrometers (wavelength)"if kind=="focal_shift"else"normalized field"if kind=="lateral_color"else"normalized pupil"
                yunit="waves"if kind=="opd_fan"else"micrometers"if kind in {"ray_fan","lateral_color"}else"fraction"if"encircled_energy"in kind else lens
                s.update(x_unit=xunit,value_units=[yunit]*len(s["labels"]))
            elif kind.startswith("surface_")and kind.endswith("_cross") and kind not in SLOPE_ANALYSES:
                value_unit=lens if kind=="surface_sag_cross"else"1/"+lens if kind=="surface_curvature_cross"else"cycles (2*pi radians)"
                s.update(x_unit=lens,value_units=[lens,value_unit],axis_definition="XData=local X; YData columns=local Y, surface value")
        if kind in SLOPE_ANALYSES:describe_surface_slope(data,settings['requested'],lens)
        if kind.endswith('_mtf_vs_field'):
            observed=[s['frequency'] for s in data['series']]
            if len(observed)!=len(set(observed)) or set(observed)!=set(settings['requested']['frequencies']):
                raise ZemaxError('INVALID_RESULT_DATA','频率曲线集合不匹配。',native_text=str(path),observed=observed)
        if kind in {'zernike_standard','zernike_fringe','zernike_annular'}:
            coefficients=parse_zernike(path.read_text(encoding="utf-16"),settings["requested"]["maximum_terms"])
            data["rows"]=coefficients
            data["coefficient_format"]="2024 R2 Z-index/value/polynomial"if coefficients else"unrecognized; use native_text artifact"
            data["coefficient_precision"]="native formatted text; 8 decimal places on this installation"
            data["structured_data_available"]=bool(coefficients)or data["structured_data_available"]
        if kind=='zernike_coefficients_vs_field' and not data['series']:
            from .wavefront_topics import zernike_field_text_series
            parsed=zernike_field_text_series(text,settings['requested']['coefficients'],[int(v)for v in settings['native']['Coefficients'].split(',')])
            if parsed:
                parsed['x_unit']='degrees' if task['system_settings']['field_type']=='Angle' else lens
                data['series']=[parsed];data['structured_data_available']=True
        if kind in {'interferogram','zernike_coefficients_vs_field'}:
            from .wavefront_topics import describe_wavefront_topic
            try:describe_wavefront_topic(data,settings['requested'])
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind=='rms_vs_wavelength':
            try:map_rms_wavelength_series(data,settings['requested'])
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
        if kind in {'rms_vs_field','rms_vs_focus'}:
            if not data.get('series'):raise ZemaxError('NO_RESULT_DATA','RMS分析没有数值曲线。',native_text=str(path))
            data['analysis_kind']=kind
            metric=settings['requested']['data_type']
            unit='waves' if metric=='Wavefront' else 'dimensionless' if metric=='StrehlRatio' else 'micrometers'
            for item in data['series']:item.update(value_units=[unit]*len(item['labels']),x_unit=lens if kind=='rms_vs_focus' else 'degrees' if task['system_settings']['field_type']=='Angle' else lens,data_type=metric,actual_point_count=len(item['x']),wavelength_selection=settings['requested']['wavelength'],native_labels=list(item['labels']))
            for item in data['series']:
                columns=[]
                for label in item['labels']:
                    column=dict(native_label=label)
                    if kind=='rms_vs_field':
                        try:
                            wave=float(label)
                            column['wavelength_numbers']=[w['number'] for w in task['system_settings']['wavelengths'] if abs(w['wavelength_um']-wave)<.000051]
                            column['aggregation']='monochromatic'
                        except ValueError:column['aggregation']='polychromatic' if 'poly' in label.lower() or '多色' in label else 'native_label'
                    else:
                        match=re.search(r'(\d+)\s*$',label)
                        if match:column['field_number']=int(match[1])
                        column['aggregation']='polychromatic' if settings['requested']['wavelength']==0 else 'monochromatic'
                    columns.append(column)
                item['column_metadata']=columns
        if kind in {'single_ray_trace','seidel_coefficients','grid_distortion'}:
            from .basic_analyses import parse_native_tables
            try:data.update(parse_native_tables(text,kind))
            except ZemaxError as exc:
                exc.details['native_text']=str(path)
                raise
            data['position_unit']=lens
            data['native_tail']=text.splitlines()[-24:]
            if kind=='seidel_coefficients':
                supported={'Standard','EvenAspheric','OddAsphere','ExtendedAsphere','ExtendedOddAsphere'}
                unsupported=[];off_axis=[]
                for index in range(1,self.system.LDE.NumberOfSurfaces-1):
                    row=self._row(index)
                    if str(row.Type) not in supported:unsupported.append(dict(surface=index,type=str(row.Type)))
                    tilt=row.TiltDecenterData
                    if any(abs(float(getattr(tilt,prefix+name)))>1e-12 for prefix in ('BeforeSurface','AfterSurface') for name in ('DecenterX','DecenterY','TiltX','TiltY','TiltZ')):off_axis.append(index)
                data['applicability']=dict(unsupported_surfaces=unsupported,off_axis_surfaces=off_axis,within_surface_scope=not unsupported and not off_axis,definition='native paraxial third-order coefficients')
            for row in data['rows']:
                if row.get('unit')=='lens units':row['unit']=lens
            data['analysis_kind']=kind
        if not data["series"]: data.pop("series")
        return data

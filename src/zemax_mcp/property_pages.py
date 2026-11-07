"""Typed local SystemData and LDE property pages."""
from typing import Optional
from pydantic import create_model, model_validator, FiniteFloat
from .schema import Request
from .errors import ZemaxError

class Page(Request):
    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set or any(getattr(self,k) is None for k in self.model_fields_set):
            raise ValueError("设置对象需要非空修改；省略不修改的字段。")
        for k in ('semi_diameter_margin','semi_diameter_margin_pct','apodization_factor','mirror_thickness'):
            value=getattr(self,k,None)
            if value is not None and value<0:raise ValueError(k+'必须非负。')
        for k in ('x_width','y_width'):
            value=getattr(self,k,None)
            if value is not None and value<=0:raise ValueError(k+'必须为正。')
        return self

# Public key, native property, scalar type. Ordering follows native dependencies.
APERTURE_OPTIONS = {
'apodization_type':('ApodizationType',str),'apodization_factor':('ApodizationFactor',FiniteFloat),
'semi_diameter_margin':('SemiDiameterMargin',FiniteFloat),'semi_diameter_margin_pct':('SemiDiameterMarginPct',FiniteFloat),
'telecentric_object_space':('TelecentricObjectSpace',bool),'afocal_image_space':('AFocalImageSpace',bool),
'iterate_solves_when_updating':('IterateSolvesWhenUpdating',bool),'fast_semi_diameters':('FastSemiDiameters',bool),'check_grin_apertures':('CheckGRINApertures',bool)}
ADVANCED = {'reference_opd':('ReferenceOPD',str),'paraxial_rays':('ParaxialRays',str),'f_num_method':('FNumMethod',str),
'dont_print_coordinate_break_data':('DontPrintCoordinateBreakData',bool),'turn_off_threading':('TurnOffThreading',bool),
'opd_modulo_2pi':('OPDModulo2PI',bool),'include_calculated_data_in_session_file':('IncludeCalculatedDataInSessionFile',bool),
'include_tolerance_data_in_session_file':('IncludeToleranceDataInSessionFile',bool),'huygens_integral_method':('HuygensIntegralMethod',str)}
DRAWING = {'hide_rays_to_this_surface':('HideRaysToThisSurface',bool),'skip_rays_to_this_surface':('SkipRaysToThisSurface',bool),
'do_not_draw_this_surface':('DoNotDrawThisSurface',bool),'do_not_draw_edges_from_this_surface':('DoNotDrawEdgesFromThisSurface',bool),
'draw_local_axis':('DrawLocalAxis',bool),'draw_edges_as':('DrawEdgesAs',str),'mirror_substrate':('MirrorSubstrate',str),'mirror_thickness':('MirrorThickness',FiniteFloat)}
TYPE_PROPERTIES = {'surface_color':('SurfaceColor',str),'surface_opacity':('SurfaceOpacity',str),'row_color':('RowColor',str),
'ignore_surface':('IgnoreSurface',bool),'surface_cannot_be_hyperhemispheric':('SurfaceCannotBeHyperhemispheric',bool)}
COMPOSITE = {'is_composite_surface':('IsCompositeSurface',bool)}
PHYSICAL_OPTICS = {
'use_rays_to_propagate_to_next_surface':('UseRaysToPropagateToNextSurface',bool),
'do_not_rescale_beam_size_using_ray_data':('DoNotRescaleBeamSizeUsingRayData',bool),
'use_angular_spectrum_propagator':('UseAngularSpectrumPropagator',bool),'draw_this_lens_on_shaded_model':('DrawThisLensOnShadedModel',bool),
're_compute_pilot_beam_parameters':('ReComputePilotBeamParameters',bool),'use_xaxis_reference':('UseXaxisReference',bool),
'resample_after_refraction':('ResampleAfterRefraction',bool),'auto_resample':('AutoResample',bool),
'x_sampling':('XSampling',str),'y_sampling':('YSampling',str),'x_width':('XWidth',FiniteFloat),'y_width':('YWidth',FiniteFloat),
'output_pilot_radius':('OutputPilotRadius',str),'x_radius':('XRadius',FiniteFloat),'y_radius':('YRadius',FiniteFloat)}

def page(name,mapping):
    return create_model(name,__base__=Page,**{k:(Optional[t],None) for k,(_,t) in mapping.items()})
ApertureOptions=page('ApertureOptions',APERTURE_OPTIONS)
Advanced=page('Advanced',ADVANCED)
Drawing=page('Drawing',DRAWING)
TypeProperties=page('TypeProperties',TYPE_PROPERTIES)
Composite=page('Composite',COMPOSITE)
PhysicalOptics=page('PhysicalOptics',PHYSICAL_OPTICS)
SYSTEM_PAGES={'aperture_options':('Aperture',APERTURE_OPTIONS),'advanced':('Advanced',ADVANCED)}
SURFACE_PAGES={'drawing':('DrawData',DRAWING),'type_properties':('TypeData',TYPE_PROPERTIES),'composite':('CompositeData',COMPOSITE),'physical_optics':('PhysicalOpticsData',PHYSICAL_OPTICS)}

def read_pages(obj,pages):
    result={}
    for key,(attr,mapping) in pages.items():
        target=getattr(obj,attr)
        result[key]={k:str(getattr(target,n)) if t is str else getattr(target,n) for k,(n,t) in mapping.items()}
    return result

def apply_pages(native,obj,req,pages,validate=False):
    from .detectors import checked_setting
    for key,(attr,mapping) in pages.items():
        patch=getattr(req,key,None)
        if patch is None:continue
        target=getattr(obj,attr)
        if key=='physical_optics':
            resample=patch.resample_after_refraction if patch.resample_after_refraction is not None else bool(target.ResampleAfterRefraction)
            auto=patch.auto_resample if patch.auto_resample is not None else bool(target.AutoResample)
            dependent=patch.model_fields_set & {'auto_resample','x_sampling','y_sampling','x_width','y_width'}
            if dependent and not resample:
                raise ZemaxError('UNSUPPORTED_SETTING','重采样参数要求resample_after_refraction=true。',fields=sorted(dependent))
            if auto and patch.model_fields_set & {'x_sampling','y_sampling','x_width','y_width'}:
                raise ZemaxError('UNSUPPORTED_SETTING','手动采样参数要求auto_resample=false。')
        if key=='drawing' and any(k.startswith('mirror_') for k in patch.model_fields_set) and not target.HasMirrorSettings:
            raise ZemaxError('UNSUPPORTED_SETTING','当前曲面无镜面绘图设置。')
        for k,(name,_) in mapping.items():
            if k not in patch.model_fields_set:continue
            value=getattr(patch,k)
            prop=target.GetType().GetProperty(name)
            if prop is None or not prop.CanWrite:raise ZemaxError('UNSUPPORTED_SETTING','属性不可写。',setting=name)
            if prop.PropertyType.IsEnum:native.enum(prop.PropertyType,value)
            if not validate:
                if prop.PropertyType.IsEnum:
                    expected=native.enum(prop.PropertyType,value)
                    setattr(target,name,expected)
                    if not getattr(target,name).Equals(expected):raise ZemaxError('SETTING_REJECTED','枚举设置未采用。',setting=name)
                else:checked_setting(native,target,name,value)

        if not validate:
            from .detectors import check_setting_value
            for k in patch.model_fields_set:
                name=mapping[k][0];actual=getattr(target,name);expected=getattr(patch,k)
                prop=target.GetType().GetProperty(name)
                if prop.PropertyType.IsEnum:
                    if not actual.Equals(native.enum(prop.PropertyType,expected)):raise ZemaxError('SETTING_REJECTED','最终设置组合未采用。',setting=name)
                else:check_setting_value(name,expected,actual)

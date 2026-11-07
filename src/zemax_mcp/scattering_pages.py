"""Native sequential scattering settings and resources."""
from typing import Annotated, Literal
from pydantic import Field, FiniteFloat
from .schema import Request
from .errors import ZemaxError
Fraction=Annotated[FiniteFloat,Field(ge=0,le=1)]
class NoScatter(Request):
    type: Literal['None']
class Lambertian(Request):
    type: Literal['Lambertian']
    scatter_fraction: Fraction
class Gaussian(Request):
    type: Literal['Gaussian']
    scatter_fraction: Fraction
    sigma: Annotated[FiniteFloat,Field(gt=0)]
class ABg(Request):
    type: Literal['ABg']
    abg_name: str
class ABgFile(Request):
    type: Literal['ABgFile']
    file_name: str
class BSDF(Request):
    type: Literal['BSDF']
    file_name: str
    scatter_fraction: Fraction
    angle: FiniteFloat = 0
class User(Request):
    type: Literal['User']
    dll_name: str
    parameters: dict[Annotated[int,Field(strict=True,ge=0)],FiniteFloat] = Field(default_factory=dict)
class Catalog(Request):
    type: Literal['ISScatterCatalog']
    file_name: str
    angle: FiniteFloat = 0
    sample_side: Literal['Front','Back'] = 'Front'
    sampling: Literal['FiveDegrees','TwoDegrees','OneDegree'] = 'FiveDegrees'
Scattering=Annotated[NoScatter|Lambertian|Gaussian|ABg|ABgFile|BSDF|User|Catalog,Field(discriminator='type')]
MAP={'scatter_fraction':'ScatterFraction','sigma':'Sigma','abg_name':'ABgName','file_name':'FileName','dll_name':'DLLName','angle':'Angle','sample_side':'SampleSide','sampling':'Sampling'}
RESOURCES={'ABg':'GetAvailableABgNames','ABgFile':'GetAvailableFileNames','BSDF':'GetAvailableFileNames','User':'GetAvailableDLLNames','ISScatterCatalog':'GetAvailableFiles'}
def resource_names(obj,kind):
    names=[str(x) for x in getattr(obj,RESOURCES[kind])()]
    if kind=='BSDF' and any(x.lower().endswith('.abgf') for x in names):
        raise ZemaxError('UNSUPPORTED_SETTING','本机BSDF资源接口返回ABgFile列表，无法确认BSDF文件采用。',capability='sequential_bsdf_resource_selection',native_filenames=names)
    return names

def settings(native,row,kind):
    data=row.ScatteringData
    try:
        holder=data.CreateScatteringTypeSettings(native.enum(native.api.Editors.LDE.SurfaceScatteringTypes,kind))
    except Exception as exc:
        message=str(exc)
        if kind=='User' and 'UILDEScatterData' in message and ('serializ' in message.lower() or '序列化' in message):
            raise ZemaxError('UNSUPPORTED_SETTING','本机User散射设置创建失败。',capability='sequential_user_scattering',native_error=message,stage='CreateScatteringTypeSettings') from exc
        raise
    return holder,getattr(holder,'_S_'+('Catalog' if kind=='ISScatterCatalog' else kind))
def read_scattering(row):
    data=row.ScatteringData;kind=str(data.CurrentType)
    obj=getattr(data.CurrentTypeSettings,'_S_'+('Catalog' if kind=='ISScatterCatalog' else kind))
    result={'type':kind}
    for key,name in MAP.items():
        if hasattr(obj,name):
            value=getattr(obj,name);result[key]=str(value) if key in {'sample_side','sampling','abg_name','file_name','dll_name'} else value
    if kind=='ISScatterCatalog':result['file_name']=str(obj.GetFile())
    if kind=='User':result['parameters']=[dict(number=i,name=str(obj.GetParameterName(i)),value=float(obj.GetParameterValue(i))) for i in range(obj.NumberOfParameters)]
    return result

def set_scattering(native,row,patch,validate=False):
    from .detectors import checked_setting
    holder,obj=settings(native,row,patch.type)
    vals=patch.model_dump(exclude={'type','parameters'})
    resource=next((k for k in ('abg_name','file_name','dll_name') if k in vals),None)
    if resource and vals[resource] not in resource_names(obj,patch.type):
        raise ZemaxError('INVALID_RESOURCE','散射资源不在可用列表中。',type=patch.type,value=vals[resource])
    for k,v in vals.items():
        if patch.type=='ISScatterCatalog' and k=='file_name':
            status=obj.SetFile(v)
            if str(obj.GetFile())!=v:raise ZemaxError('SETTING_REJECTED','散射目录文件未采用。',status=str(status))
        else:checked_setting(native,obj,MAP[k],v)
    if patch.type=='User':
        for i,v in patch.parameters.items():
            if i>=obj.NumberOfParameters:raise ZemaxError('INDEX_OUT_OF_RANGE','散射DLL参数编号越界。',parameter=i)
            if not obj.SetParameterValue(i,v) or abs(float(obj.GetParameterValue(i))-v)>1e-12:raise ZemaxError('SETTING_REJECTED','散射DLL参数未采用。',parameter=i)
    if not validate:
        if not row.ScatteringData.ChangeScatteringTypeSettings(holder):raise ZemaxError('SETTING_REJECTED','散射类型未采用。')
        actual=read_scattering(row)
        if actual['type']!=patch.type:raise ZemaxError('SETTING_REJECTED','散射类型未采用。',requested=patch.type,actual=actual['type'])
        if patch.type=='User':
            adopted=row.ScatteringData.CurrentTypeSettings._S_User
            for i,v in patch.parameters.items():
                from .detectors import check_setting_value
                check_setting_value('parameters.'+str(i),v,float(adopted.GetParameterValue(i)))
        for k,v in vals.items():
            from .detectors import check_setting_value
            check_setting_value(k,v,actual.get(k))

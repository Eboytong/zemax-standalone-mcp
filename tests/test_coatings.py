"""Coating selectors, typed layer edits, final pickup graph and partial failures."""
from types import SimpleNamespace as NS
from copy import deepcopy
import pytest
from pydantic import ValidationError
from zemax_mcp import coatings as co
from zemax_mcp.coating_models import CoatingLayerRange,CoatingLayerUpdate
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from test_imaging import Selector

@pytest.mark.parametrize('kind',list(co.IDS))
def test_typed_coating_kinds(kind):
    q=RunAnalysis(request=dict(kind=kind,**({}if kind=='coating_listing'else dict(surface=2))))
    assert RunAnalysis.model_validate(q.model_dump())==q

@pytest.mark.parametrize('q',[
    dict(kind='reflection_vs_angle',surface=1,minimum_angle=5,maximum_angle=5),
    dict(kind='phase_vs_angle',surface=0),dict(kind='retardance_vs_angle',surface=1,maximum_angle=91),
    dict(kind='reflection_vs_wavelength',surface=1,wavelength=1),
    dict(kind='absorption_vs_wavelength',surface=1,minimum_wavelength_um=.7,maximum_wavelength_um=.6),
    dict(kind='transmission_vs_angle',surface=1,minimum_y=0),
    dict(kind='transmission_vs_angle',surface=1,minimum_y=1,maximum_y=0),
])
def test_invalid_analysis_requests(q):
    with pytest.raises(ValidationError):RunAnalysis(request=q)


@pytest.mark.parametrize('metric,labels,y_unit',[
    ('phase','S transmission phase|P transmission phase','degrees'),
    ('retardance','Reflection retardance|Transmission retardance','degrees'),
    ('diattenuation','Reflection diattenuation|Transmission diattenuation','dimensionless'),
])
def test_polarization_scan_series_labels_and_units(metric,labels,y_unit):
    from zemax_mcp.coatings import label_polarization_result
    data=dict(series=[dict(series=0,x=[0.,1.],y=[[1.,2.],[3.,4.]],labels=['column_1','column_2'])])
    result=label_polarization_result(data,metric+'_vs_wavelength')
    assert result['series'][0]['labels']==labels.split('|')
    assert result['series'][0]['native_labels']==['column_1','column_2']
    assert result['series'][0]['x_unit']=='micrometers' and result['series'][0]['y_unit']==y_unit


def test_mirror_phase_labels_use_reflected_channels():
    data=dict(series=[dict(series=0,x=[0],y=[[180,0]],labels=['column_1','column_2'])])
    result=co.label_polarization_result(data,'phase_vs_angle','MIRROR')
    assert result['series'][0]['labels']==['S reflection phase','P reflection phase']


def test_reverse_rejected_before_allocating_native_tool(monkeypatch):
    b=NS(_require_sequential=lambda:None,_row=lambda i:NS(Type='Standard'))
    monkeypatch.setattr(co,'new_analysis',lambda *args:pytest.fail('inactive option allocated analysis'))
    q=RunAnalysis(request=dict(kind='phase_vs_angle',surface=1,reverse_direction=True)).request
    with pytest.raises(ZemaxError)as error:co.run_coating(b,q)
    assert error.value.code=='INACTIVE_SETTING'
    assert error.value.details['setting']=='reverse_direction'


def test_primary_refusal_closes_copy_and_preserves_failure():
    class Waves:
        def __init__(self):self.items=[NS(Wavelength=.55,Weight=1.)]
        @property
        def NumberOfWavelengths(self):return len(self.items)
        def GetWavelength(self,i):return self.items[i-1]
        def AddWavelength(self,w,weight):
            def refuse():raise RuntimeError('primary refused')
            row=NS(Wavelength=w,Weight=weight,MakePrimary=refuse)
            self.items.append(row);return row
    closed=[];waves=Waves()
    copy=NS(SystemData=NS(Wavelengths=waves),Close=lambda save:closed.append(save)or False)
    source=NS(SystemData=NS(Wavelengths=NS(NumberOfWavelengths=1,GetWavelength=lambda i:NS(Wavelength=.55,IsPrimary=True))),CopySystem=lambda:copy)
    b=NS(_require_sequential=lambda:None,_row=lambda i:None,system=source,requires_reconnect=False)
    q=RunAnalysis(request=dict(kind='phase_vs_wavelength',surface=1)).request
    with pytest.raises(RuntimeError,match='primary refused'):co.run_coating(b,q)
    assert closed==[False] and b.requires_reconnect


@pytest.mark.parametrize('actual,valid', [([.45,.7],True),([.5445,.5555],False),([.45,.699],False)])
def test_wavelength_scan_checks_returned_axis(actual,valid):
    from types import SimpleNamespace as NS
    from zemax_mcp.coatings import check_wavelength_scan
    q=RunAnalysis(request=dict(kind='phase_vs_wavelength',surface=1,minimum_wavelength_um=.45,maximum_wavelength_um=.7)).request
    data=dict(series=[dict(x=[actual[0],actual[1]],y=[[0.,0.],[0.,0.]])])
    if valid:assert check_wavelength_scan(data,q)==actual
    else:
        with pytest.raises(ZemaxError)as caught:check_wavelength_scan(data,q)
        assert caught.value.code=='SETTING_REJECTED'


def test_wavelength_analysis_closes_tool_and_temporary_copy():
    from zemax_mcp.coatings import CoatingWavelengthAnalysis
    events=[]
    wrapper=CoatingWavelengthAnalysis(NS(Close=lambda:events.append('analysis')or True),NS(Close=lambda _:events.append('copy')or True),1)
    assert wrapper.Close() and wrapper.Close()
    assert events==['analysis','copy']

class Layer:
    def __init__(self,index):
        self.Layer=index
        self.ThicknessMultiplier=1.;self.IndexOffset=0.;self.ExtinctionOffset=0.
        for name in co.STATUS.values():setattr(self,name+'Status','Fixed');setattr(self,name+'PickupFrom',0)
    def __getattr__(self,method):
        for name in co.STATUS.values():
            for mode in ['Fixed','Variable','Pickup']:
                if method=='Set'+name+'Status'+mode:
                    def change(source=None,name=name,mode=mode):
                        setattr(self,name+'Status',mode)
                        if source is not None:setattr(self,name+'PickupFrom',source)
                        return True
                    return change
        raise AttributeError(method)
class Data:
    NumberOfLayers=3;Coating='TEST'
    def __init__(self):
        self.UseLayerMultiplierAndOffsets=True;self.rows={i:Layer(i)for i in range(1,4)};self.fail=None;self.reject_value=False;self.commits=[]
    def GetLayerSettings(self,index):return deepcopy(self.rows[index])
    def SetLayerSettings(self,index,value):
        self.commits.append(index)
        if self.fail==index:raise RuntimeError('commit failed '+str(index))
        self.rows[index]=deepcopy(value)
        if self.reject_value:self.rows[index].ThicknessMultiplier=1
        return True
class B(co.CoatingsMixin):
    def __init__(self,data):
        self.data=data;self.last_checkpoint=None;self.revision=0
        self.native=NS(api=NS(Editors=NS(LDE=NS(CoatingStatusType=None))),enum=lambda enum,name:name)
    def _require_sequential(self):pass
    def _row(self,index):return NS(CoatingData=self.data)
    def _mutate(self,label):self.last_checkpoint='baseline';self.revision+=1


class GatedData(Data):
    def GetLayerSettings(self,index):
        return super().GetLayerSettings(index) if self.UseLayerMultiplierAndOffsets else None
    def __setattr__(self,name,value):
        if name=='UseLayerMultiplierAndOffsets' and value is True and getattr(self,'fail_enable',False):
            raise RuntimeError('enable switch failed')
        if name=='UseLayerMultiplierAndOffsets' and value is False and getattr(self,'fail_restore',False):
            raise RuntimeError('restore switch failed')
        super().__setattr__(name,value)


def test_disabled_layer_read_restores_flag_without_revision():
    b=B(GatedData());b.data.UseLayerMultiplierAndOffsets=False
    result=b.get_coating_layers(CoatingLayerRange(surface=1,count=2))
    assert len(result['rows'])==2 and result['next_start']==3
    assert not result['use_layer_multiplier_and_offsets']
    assert not b.data.UseLayerMultiplierAndOffsets and b.revision==0


def test_zero_layers_does_not_enable_unavailable_switch():
    data=GatedData();data.UseLayerMultiplierAndOffsets=False
    data.NumberOfLayers=0;data.fail_enable=True
    b=B(data)
    result=b.get_coating_layers(CoatingLayerRange(surface=1))
    assert result['rows']==[] and result['total']==0
    assert not data.UseLayerMultiplierAndOffsets and b.revision==0


def test_dispatch_reports_possible_change_when_read_restore_fails(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    backend=Backend(Config(tmp_path,tmp_path),native=NS())
    data=GatedData();data.UseLayerMultiplierAndOffsets=False;data.fail_restore=True
    backend._require_sequential=lambda:None
    backend._row=lambda _:NS(CoatingData=data)
    response=backend.dispatch('get_coating_layers',dict(surface=1))
    assert not response['ok']
    assert response['error']['details']['partial_changes_possible']
    assert response['context']['requires_reconnect']


def test_combined_enable_and_edit_reads_inactive_native_layers():
    b=B(GatedData());b.data.UseLayerMultiplierAndOffsets=False
    result=b.update_coating_layers(CoatingLayerUpdate(surface=1,use_layer_multiplier_and_offsets=True,layers=[dict(layer=1,thickness_multiplier=.9)]))
    assert result['before'][1]['thickness_multiplier']==1
    assert result['after'][0]['thickness_multiplier']==.9
    assert b.data.UseLayerMultiplierAndOffsets and b.revision==1


@pytest.mark.parametrize('restore_failure',[False,True])
def test_layer_read_error_and_restore_error_preserved(restore_failure):
    b=B(GatedData());b.data.UseLayerMultiplierAndOffsets=False
    b.data.fail_restore=restore_failure
    def fail(_):raise RuntimeError('original layer read failure')
    b.data.GetLayerSettings=fail
    with pytest.raises((RuntimeError,ZemaxError)) as caught:
        b.get_coating_layers(CoatingLayerRange(surface=1))
    assert 'original layer read failure' in str(caught.value)
    if restore_failure:
        assert b.requires_reconnect
        assert 'restore switch failed' in str(caught.value.details['restore_error'])
    else:assert not b.data.UseLayerMultiplierAndOffsets

@pytest.mark.parametrize('payload',[
    dict(surface=1),dict(surface=1,layers=[dict(layer=1)]),
    dict(surface=1,layers=[dict(layer=1,index_offset=float('inf'))]),
    dict(surface=1,layers=[dict(layer=1,thickness_multiplier=-1)]),
    dict(surface=1,layers=[dict(layer=1,thickness_status=dict(mode='Pickup',layer=1))]),
    dict(surface=1,layers=[dict(layer=1,index_status=dict(mode='Fixed',layer=2))]),
    dict(surface=1,layers=[dict(layer=1,index_offset=.1),dict(layer=1,index_offset=.2)]),
])
def test_invalid_layer_requests(payload):
    with pytest.raises(ValidationError):CoatingLayerUpdate(**payload)

def test_layer_partial_updates_and_status():
    b=B(Data());b.data.rows[1].ExtinctionOffset=.3
    value=b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[dict(layer=1,thickness_multiplier=.8,thickness_status=dict(mode='Variable'))]))
    row=value['after'][0]
    assert row['thickness_multiplier']==.8 and row['extinction_offset']==.3 and row['thickness_status']['mode']=='Variable'
    assert b.revision==1 and value['checkpoint']=='baseline'
    page=b.get_coating_layers(CoatingLayerRange(surface=1,count=2))
    assert page['total']==3 and page['next_start']==3 and len(page['rows'])==2

@pytest.mark.parametrize('status',['thickness_status','index_status','extinction_status'])
def test_pickup_cycle_rejected_before_mutation(status):
    b=B(Data())
    q=CoatingLayerUpdate(surface=1,layers=[dict(layer=1,**{status:dict(mode='Pickup',layer=2)}),dict(layer=2,**{status:dict(mode='Pickup',layer=1)})])
    with pytest.raises(ZemaxError)as exc:b.update_coating_layers(q)
    assert exc.value.code=='PICKUP_CYCLE' and b.revision==0 and not b.data.commits

def test_pickup_conflict_and_explicit_replacement():
    b=B(Data());b.data.rows[1].ThicknessStatus='Pickup';b.data.rows[1].ThicknessPickupFrom=2
    with pytest.raises(ZemaxError):b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[dict(layer=1,thickness_multiplier=.5)]))
    assert b.revision==0
    result=b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[dict(layer=1,thickness_multiplier=.5,thickness_status=dict(mode='Fixed'))]))
    assert result['after'][0]['thickness_multiplier']==.5 and result['after'][0]['thickness_status']['mode']=='Fixed'

def test_final_graph_detaches_old_edges_before_new_pickup():
    b=B(Data());b.data.rows[2].IndexStatus='Pickup';b.data.rows[2].IndexPickupFrom=1
    q=CoatingLayerUpdate(surface=1,layers=[dict(layer=1,index_status=dict(mode='Pickup',layer=2)),dict(layer=2,index_status=dict(mode='Fixed'))])
    result=b.update_coating_layers(q)
    assert b.data.commits[0]==2 and result['after'][0]['index_status']['pickup_from']==2

@pytest.mark.parametrize('enabled',[False,True])
def test_layer_enabled_dependency(enabled):
    b=B(Data());b.data.UseLayerMultiplierAndOffsets=False
    q=CoatingLayerUpdate(surface=1,use_layer_multiplier_and_offsets=enabled,layers=[dict(layer=1,index_offset=.01)])
    if enabled:assert b.update_coating_layers(q)['after'][0]['index_offset']==.01
    else:
        with pytest.raises(ZemaxError)as exc:b.update_coating_layers(q)
        assert exc.value.code=='INACTIVE_SETTING' and b.revision==0

def test_partial_failure_preserves_completed_layer_and_original_error():
    b=B(Data());b.data.fail=2
    with pytest.raises(ZemaxError)as exc:b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[dict(layer=1,index_offset=.1),dict(layer=2,index_offset=.2)]))
    error=exc.value
    assert error.code=='PARTIAL_UPDATE' and error.details['completed_layers']==[1]
    assert error.details['failed_layer']==2 and 'commit failed 2'in error.details['cause']['message']
    assert b.data.rows[1].IndexOffset==.1

def test_readback_rejects_silent_ignore():
    b=B(Data());b.data.reject_value=True
    with pytest.raises(ZemaxError)as exc:b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[dict(layer=1,thickness_multiplier=.7)]))
    assert exc.value.details['cause']['code']=='SETTING_REJECTED'

def test_out_of_range_layer_and_pickup():
    b=B(Data())
    for layer in [dict(layer=4,index_offset=1),dict(layer=1,index_status=dict(mode='Pickup',layer=4))]:
        with pytest.raises(ZemaxError)as exc:b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[layer]))
        assert exc.value.code=='INDEX_OUT_OF_RANGE' and b.revision==0

@pytest.mark.parametrize('kind',[k for k in co.IDS if k!='coating_listing'])
def test_analysis_settings_written_and_readback(monkeypatch,kind):
    q=RunAnalysis(request=dict(kind=kind,surface=2)).request
    s=NS(Surface=Selector('Surface'),Wavelength=Selector('Wavelength'),ObjectNumber=1,FaceNumber=1)
    monkeypatch.setattr(co,'checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr(co,'check',lambda n,s,k,v:co.check_setting_value(k,v,getattr(s,k)))
    monkeypatch.setattr(co,'scalar_settings',lambda s:dict(vars(s)))
    actual=co.configure(NS(native=None),s,q)
    assert s.Surface.value==2 and s.ObjectNumber==1 and s.FaceNumber==1
    assert actual['requested']['kind']==kind
    if kind.endswith('_angle'):
        assert s.Wavelength.value==q.wavelength-1
        assert actual['native']['wavelength_number']==q.wavelength


@pytest.mark.parametrize('number',[1,2,3])
def test_coating_angle_native_wavelength_is_zero_based(monkeypatch,number):
    q=RunAnalysis(request=dict(kind='phase_vs_angle',surface=1,wavelength=number)).request
    s=NS(Surface=Selector('Surface'),Wavelength=Selector('Wavelength'))
    monkeypatch.setattr(co,'checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr(co,'check',lambda n,s,k,v:co.check_setting_value(k,v,getattr(s,k)))
    monkeypatch.setattr(co,'scalar_settings',lambda s:dict(Wavelength=s.Wavelength.value))
    result=co.configure(NS(native=None),s,q)
    assert result['native']['Wavelength']==number-1
    assert result['native']['wavelength_number']==number

@pytest.mark.parametrize('kind',list(co.IDS))
def test_scan_setup_failure_closes_tool(monkeypatch,kind):
    tool=NS(GetSettings=lambda:None,Close=lambda:True);closed=[]
    class Waves:
        def __init__(self):self.items=[NS(Wavelength=.55,Weight=1.,IsPrimary=True)]
        @property
        def NumberOfWavelengths(self):return len(self.items)
        def RemoveWavelength(self,i):self.items.pop(i-1)
        def GetWavelength(self,i):return self.items[i-1]
        def AddWavelength(self,w,weight):
            row=NS(Wavelength=w,Weight=weight,IsPrimary=False)
            row.MakePrimary=lambda:setattr(row,'IsPrimary',True)
            self.items.append(row);return row
    waves=Waves()
    copy=NS(SystemData=NS(Wavelengths=waves),MCE=NS(CurrentConfiguration=1),SystemID=2,
        LDE=NS(GetSurfaceAt=lambda i:NS(Material='AIR',CoatingData=NS(Coating=''))),Close=lambda _:True)
    system=NS(SystemData=NS(Wavelengths=NS(NumberOfWavelengths=1,GetWavelength=lambda i:NS(Wavelength=.55,IsPrimary=True))),SystemID=1,CopySystem=lambda:copy)
    b=NS(_require_sequential=lambda:None,_row=lambda i:None,system=system,native=NS(),_close_task_native=lambda t:closed.append(t['native'])or t['native'].Close())
    monkeypatch.setattr(co,'new_analysis',lambda b,k:tool)
    monkeypatch.setattr(co,'configure',lambda *args:(_ for _ in ()).throw(RuntimeError('settings failed')))
    with pytest.raises(RuntimeError):co.run_coating(b,RunAnalysis(request=dict(kind=kind,**({}if kind=='coating_listing'else dict(surface=2)))).request)
    assert len(closed)==1 and (closed[0] is tool or closed[0].analysis is tool)

def test_current_layer_read_failure_preserves_original_mutation_error():
    b=B(Data());original=b.data.GetLayerSettings
    def read(index):
        if b.data.fail==index and index in b.data.commits:raise RuntimeError('secondary read failure')
        return original(index)
    b.data.GetLayerSettings=read;b.data.fail=2
    with pytest.raises(ZemaxError)as exc:b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[dict(layer=1,index_offset=.1),dict(layer=2,index_offset=.2)]))
    assert 'commit failed 2'in exc.value.details['cause']['message']
    assert 'secondary read failure'in exc.value.details['failed_layer_state']['read_error']

def test_value_and_pickup_rejected_by_typed_request():
    with pytest.raises(ValidationError):CoatingLayerUpdate(surface=1,layers=[dict(layer=1,index_offset=.1,index_status=dict(mode='Pickup',layer=2))])

def test_final_enabled_flag_is_checked_after_native_layer_commit():
    b=B(Data());commit=b.data.SetLayerSettings
    def drift(index,value):
        result=commit(index,value);b.data.UseLayerMultiplierAndOffsets=False;return result
    b.data.SetLayerSettings=drift
    with pytest.raises(ZemaxError)as exc:b.update_coating_layers(CoatingLayerUpdate(surface=1,layers=[dict(layer=1,index_offset=.1)]))
    assert exc.value.details['cause']['code']=='SETTING_REJECTED'

def test_coating_listing_text_only_result(tmp_path):
    from test_imaging import results,collect
    r=results(GetTextFile=lambda path:True)
    result=collect(tmp_path,r,'coating_listing')
    assert result['structured_data_available']is False and result['artifacts'][0]['kind']=='native_text'

def test_all_native_analysis_ids_exist_in_installed_reflection():
    import json
    from pathlib import Path
    api=json.loads((Path(__file__).parents[1]/'verification/development/BASE-01/probe/api-interfaces.json').read_text(encoding='utf8'))
    ids=api['enums']['ZOSAPI.Analysis.AnalysisIDM']
    assert set(co.IDS.values())<=ids.keys()

def test_analysis_dispatch_uses_coating_adapter(monkeypatch):
    from zemax_mcp.analyses import AnalysesMixin
    monkeypatch.setattr(co,'run_coating',lambda b,q:dict(kind=q.kind))
    value=AnalysesMixin().run_analysis(RunAnalysis(request=dict(kind='reflection_vs_angle',surface=1)))
    assert value['kind']=='reflection_vs_angle'

def test_setting_refusal_keeps_native_error_details(monkeypatch):
    q=RunAnalysis(request=dict(kind='reflection_vs_angle',surface=1)).request
    s=NS(Surface=Selector('Surface'),Wavelength=Selector('Wavelength'))
    def checked(native,s,key,value):
        if key=='MaxAngle':raise ZemaxError('SETTING_REJECTED','original refusal',setting=key)
    monkeypatch.setattr(co,'checked',checked)
    with pytest.raises(ZemaxError)as exc:co.configure(NS(native=None),s,q)
    assert exc.value.details['setting']=='MaxAngle'


@pytest.mark.parametrize('extra',[dict(nsc_object=1),dict(nsc_face=0),dict(nsc_object=0,nsc_face=0),dict(nsc_object=1,nsc_face=-1)])
def test_nsc_coating_selector_pair_and_ranges(extra):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='reflection_vs_angle',surface=2,**extra))


def test_nsc_face_preflight_restores_group_on_rejection():
    editor=NS(ActiveSurface=4,NumberOfObjects=2)
    b=NS(system=NS(NCE=editor),requires_reconnect=False,_select_nsc_group=lambda i:setattr(editor,'ActiveSurface',i))
    editor.GetObjectAt=lambda i:NS(Type='RectangularVolume',Material='N-BK7',CoatScatterData=NS(IsCoatScatterAvailable=True,NumberOfFaces=3,GetFaceData=lambda i:NS(Coating='SPLIT')))
    q=RunAnalysis(request=dict(kind='reflection_vs_angle',surface=2,nsc_object=1,nsc_face=3)).request
    with pytest.raises(ZemaxError)as error:co.nsc_coating_target(b,q)
    assert error.value.code=='INDEX_OUT_OF_RANGE'and editor.ActiveSurface==4


def test_nsc_coating_fields_rejected_on_ordinary_surface(monkeypatch):
    b=NS(_require_sequential=lambda:None,_row=lambda i:NS(Type='Standard'))
    monkeypatch.setattr(co,'new_analysis',lambda *args:pytest.fail('inactive selector created analysis'))
    q=RunAnalysis(request=dict(kind='reflection_vs_angle',surface=1,nsc_object=1,nsc_face=0)).request
    with pytest.raises(ZemaxError)as error:co.run_coating(b,q)
    assert error.value.code=='INACTIVE_SETTING'


def test_copy_closes_even_when_native_analysis_close_raises():
    events=[]
    def failure():events.append('analysis');raise RuntimeError('native close failed')
    wrapped=co.CoatingWavelengthAnalysis(NS(Close=failure),NS(Close=lambda save:events.append('copy')or True),1)
    with pytest.raises(RuntimeError,match='native close failed'):wrapped.Close()
    assert events==['analysis','copy']


@pytest.mark.parametrize('mode,surface',[('Sequential',0),('NonSequential',2)])
def test_nsc_scope_rejects_inconsistent_surface_before_analysis(mode,surface,monkeypatch):
    b=NS(system=NS(Mode=mode),_require_sequential=lambda:None)
    monkeypatch.setattr(co,'new_analysis',lambda *args:pytest.fail('invalid scope allocated analysis'))
    q=RunAnalysis(request=dict(kind='reflection_vs_angle',surface=surface,nsc_object=1,nsc_face=0)).request
    with pytest.raises(ZemaxError)as error:co.run_coating(b,q)
    assert error.value.code=='INVALID_ARGUMENT'


def test_nsc_selector_final_readback_rejects_silent_native_ignore(monkeypatch):
    q=RunAnalysis(request=dict(kind='reflection_vs_angle',surface=2,nsc_object=2,nsc_face=1)).request
    s=NS(Surface=Selector('Surface'),Wavelength=Selector('Wavelength'),ObjectNumber=1,FaceNumber=0)
    monkeypatch.setattr(co,'checked',lambda native,s,key,value:None)
    monkeypatch.setattr(co,'check',lambda native,s,key,value:co.check_setting_value(key,value,getattr(s,key))if key in {'ObjectNumber','FaceNumber'}else None)
    with pytest.raises(ZemaxError)as error:co.configure(NS(native=None),s,q)
    assert error.value.code=='SETTING_REJECTED'

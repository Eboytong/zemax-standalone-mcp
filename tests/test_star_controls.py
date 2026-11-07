from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError

from zemax_mcp.star_models import RunStar, StarRead
from zemax_mcp.star_controls import prepare_control, check_mode
from zemax_mcp.errors import ZemaxError
from zemax_mcp.evaluation import Cancelled
from test_star import Backend as BaseBackend


@pytest.mark.parametrize('payload', [
    dict(kind='rigid_body',surface=1),
    dict(kind='coordinate_transform',surface=1),
    dict(kind='coordinate_transform',surface=1,rotation_matrix=[1]*9),
    dict(kind='coordinate_transform',surface=1,rotation_matrix=[-1,0,0,0,1,0,0,0,1]),
    dict(kind='coordinate_transform',surface=1,reset=True,offset=dict(x=1,y=0)),
    dict(kind='define_component',first_surface=3,last_surface=1),
    dict(kind='remove_component',first_surface=0),
    dict(kind='component_rbm',surface=1,action='configure'),
    dict(kind='thermal_controls',surface=1),
    dict(kind='thermal_controls',surface=1,working_wavelength=0),
    dict(kind='volume_controls',surface=1,data_kind='deformation',grin_step=1),
    dict(kind='volume_controls',surface=1,data_kind='temperature',grin_step=float('inf')),
    dict(kind='update_mode'),dict(kind='update_mode',mode='manual'),
])
def test_star_control_typed_constraints(payload):
    with pytest.raises(ValidationError): RunStar(request=payload)


class Enum:
    def __init__(self,name): self.name=name
    def Equals(self,other): return isinstance(other,Enum) and self.name==other.name
    def __str__(self): return self.name


def transform():
    return N(XOffset=0.,YOffset=0.,ZOffset=0.,R11=1.,R12=0.,R13=0.,R21=0.,R22=1.,R23=0.,R31=0.,R32=0.,R33=1.)


class Component:
    def __init__(self,b):
        self.b=b; self.members=[]
        self.AdjustIndexDataWithComponentRBM=False
        self.ComponentRBMsAreRemoved=False; self.CRBMsAreInCoordinateBreaks=False
        self.Transform=transform()
    @property
    def FirstSurfaceInComponent(self): return self.members[0] if self.members else 0
    @property
    def LastSurfaceInComponent(self): return self.members[-1] if self.members else 0
    @property
    def ListOfSurfacesInComponent(self): return self.members
    @property
    def NumberOfSurfacesInComponent(self): return len(self.members)
    def IsPartOfAComponent(self): return bool(self.members)
    def SetSurfacesInComponent(self,first,last):
        self.b.events.append(('define',first,last)); self.members=list(range(first,last+1))
        for i in self.members: self.b.rows[i].STARData.ComponentRBMs=self
    def RemoveComponent(self,first):
        assert first==self.FirstSurfaceInComponent
        self.b.events.append(('remove',first)); self.members=[]
    def RemoveComponentRBMsFromFEADataSets(self): self.ComponentRBMsAreRemoved=True
    def AddComponentRBMsAsCoordinateBreaks(self):
        self.CRBMsAreInCoordinateBreaks=True
        self.b.system.LDE.NumberOfSurfaces += 2
        for n in (4,5): self.b.rows[n]=N(STARData=N(ComponentRBMs=Component(self.b)))


class Backend(BaseBackend):
    def __init__(self,path):
        super().__init__(path)
        self.native.api=N(STARUpdateMode=object())
        self.native.enum=lambda typ,name:Enum(name)
        self.native.set_enum=lambda obj,name,value:setattr(obj,name,Enum(value))
        self.system.STARSubsystem=N(UpdateMode=Enum('Normal'),DoManualUpdate=self.manual_update)
        self.system.LDE=N(NumberOfSurfaces=5)
        self.system.SystemData.Wavelengths=N(NumberOfWavelengths=3)
        self.rows={i:N(STARData=N(Deformations=self.branch,Temperatures=self.branch,DirectIndex=self.branch)) for i in range(4)}
        for row in self.rows.values(): row.STARData.ComponentRBMs=Component(self)
        rb=self.branch.RBMs
        self.reference=N(X=0.,Y=0.,Z=0.)
        rb.Transform=transform()
        rb.GetReferencePoint=lambda:self.reference
        rb.SetReferencePoint=self.set_reference
        rb.Enable=lambda:setattr(rb,'IsEnabled',True)
        rb.Disable=lambda:setattr(rb,'IsEnabled',False)
        ct=self.branch.CoordinateTransform
        ct.Transform=transform()
        ct.Enable=lambda:setattr(ct,'IsEnabled',True)
        ct.Disable=lambda:setattr(ct,'IsEnabled',False)
        ct.SetDecenter=self.set_offset
        ct.SetRotationMatrix=self.set_rotation
        ct.IsInDefaultFrameOfReference=lambda:self.default_frame
        ct.ResetToDefaultFrameOfReference=self.reset_transform
        self.default_frame=True; self.fit_type=0; self.wave=1
        self.branch.GetThermalFEAFitType=lambda:self.fit_type
        self.branch.SetThermalFEAFitType=lambda n:setattr(self,'fit_type',n)
        self.branch.GetWorkingWavelength=lambda:self.wave
        self.branch.SetWorkingWavelength=self.set_wave
        self.branch.PrimaryWavelengthValue=.55
        self.branch.GRINStep=.1; self.branch.Fits.GRINStep=.1
        self.clobber_thermal=False
    def _row(self,index): return self.rows[index]
    def manual_update(self): self.events.append('manual_update')
    def set_reference(self,x,y,z): self.reference=N(X=x,Y=y,Z=z)
    def set_offset(self,x,y,z):
        self.events.append('offset'); self.default_frame=False
        t=self.branch.CoordinateTransform.Transform
        t.XOffset,t.YOffset,t.ZOffset=x,y,z
    def set_rotation(self,*values):
        self.events.append('rotation'); self.default_frame=False
        from zemax_mcp.star_controls import MATRIX_FIELDS
        for k,v in zip(MATRIX_FIELDS,values): setattr(self.branch.CoordinateTransform.Transform,k,v)
    def reset_transform(self):
        self.default_frame=True; self.branch.CoordinateTransform.Transform=transform()
    def set_wave(self,n):
        self.wave=n
        if self.clobber_thermal: self.fit_type=99


@pytest.fixture
def backend(tmp_path,monkeypatch):
    import zemax_mcp.star_controls as module
    monkeypatch.setattr(module,'checked_setting',lambda native,obj,name,value:setattr(obj,name,value))
    return Backend(tmp_path)


def run(b,payload):
    req=RunStar(request=payload)
    assert RunStar.model_validate(req.model_dump())==req
    b.run_star_operation(req); list(b.flow)
    return b.task['payload']['actual']


def test_rigid_body_reference_enable_and_readback(backend):
    actual=run(backend,dict(kind='rigid_body',surface=1,enabled=True,reference_point=dict(x=1,y=2,z=3)))
    assert actual['enabled'] and actual['reference_point']==[1,2,3]
    assert backend.get_star_data(StarRead(surface=1))['controls']['rigid_body']['reference_point']==[1,2,3]


def test_transform_row_major_order_and_omitted_enable_is_preserved(backend):
    rotation=[0.,-1.,0.,1.,0.,0.,0.,0.,1.]
    actual=run(backend,dict(kind='coordinate_transform',surface=1,offset=dict(x=1,y=2,z=3),rotation_matrix=rotation))
    assert actual['rotation_matrix']==rotation and actual['offset']==[1,2,3]
    assert actual['enabled'] is False
    assert backend.events.index('offset')<backend.events.index('rotation')
    actual=run(backend,dict(kind='coordinate_transform',surface=1,reset=True,enabled=True))
    assert actual['enabled'] and actual['default_frame']


def test_transform_cancel_restores_model_and_subsystem_mode(backend):
    backend.system.STARSubsystem.UpdateMode=Enum('Suspended')
    backend.run_star_operation(RunStar(request=dict(kind='coordinate_transform',surface=1,offset=dict(x=1,y=2))))
    next(backend.flow); backend.task['cancel_requested']=True
    with pytest.raises(Cancelled): next(backend.flow)
    assert backend.events[-1]=='restore'
    check_mode(backend,'Suspended')


def test_component_definition_overlap_and_first_surface_removal(backend):
    actual=run(backend,dict(kind='define_component',first_surface=1,last_surface=2,adjust_index_data_with_rbm=True))
    assert actual['groups']=={1:[1,2]}
    assert actual['component']['adjust_index_data_with_rbm']
    with pytest.raises(ZemaxError) as exc:
        prepare_control(backend,RunStar(request=dict(kind='define_component',first_surface=2,last_surface=3)).request)
    assert exc.value.code=='RELATION_PROTECTED'
    with pytest.raises(ZemaxError) as exc:
        prepare_control(backend,RunStar(request=dict(kind='remove_component',first_surface=2)).request)
    assert exc.value.details['actual']==1
    actual=run(backend,dict(kind='remove_component',first_surface=1))
    assert actual['groups']=={} and ('remove',1) in backend.events


@pytest.mark.parametrize('action',['remove_from_fea','add_coordinate_breaks'])
def test_component_rbm_action_and_repeat_protection(backend,action):
    run(backend,dict(kind='define_component',first_surface=1,last_surface=2))
    actual=run(backend,dict(kind='component_rbm',surface=1,action=action))
    assert actual['component']['rbms_removed' if action=='remove_from_fea' else 'coordinate_breaks']
    if action=='add_coordinate_breaks':
        assert actual['surface_count_after']==actual['surface_count_before']+2
        assert backend._engineering_mapping_valid is False
    with pytest.raises(ZemaxError) as exc:
        prepare_control(backend,RunStar(request=dict(kind='component_rbm',surface=1,action=action)).request)
    assert exc.value.code=='CONDITION_NOT_MET'


def test_thermal_wavelength_preflight_and_final_combination_readback(backend):
    with pytest.raises(ZemaxError) as exc:
        prepare_control(backend,RunStar(request=dict(kind='thermal_controls',surface=1,working_wavelength=4)).request)
    assert exc.value.code=='INDEX_OUT_OF_RANGE' and backend.events==[]
    actual=run(backend,dict(kind='thermal_controls',surface=1,fit_type=1,working_wavelength=2))
    assert actual['fit_type']==1 and actual['working_wavelength']==2
    backend.clobber_thermal=True
    with pytest.raises(ZemaxError) as exc:
        run(backend,dict(kind='thermal_controls',surface=1,fit_type=1,working_wavelength=3))
    assert exc.value.code=='SETTING_REJECTED' and backend.events[-1]=='restore'


@pytest.mark.parametrize('data_kind',['temperature','direct_index'])
def test_volume_controls_patch_one_native_member(backend,data_kind):
    actual=run(backend,dict(kind='volume_controls',surface=1,data_kind=data_kind,grin_step=.2))
    assert actual['grin_step']==.2 and actual['fit_grin_step']==.1


def test_update_mode_manual_update_and_cancel_mode_restore(backend):
    actual=run(backend,dict(kind='update_mode',mode='Suspended',manual_update=True))
    assert actual['update_mode']=='Suspended' and 'manual_update' in backend.events
    backend.run_star_operation(RunStar(request=dict(kind='update_mode',mode='Normal')))
    next(backend.flow); backend.task['cancel_requested']=True
    with pytest.raises(Cancelled): next(backend.flow)
    check_mode(backend,'Suspended')


def test_restore_error_retains_control_error_and_requires_reconnect(backend):
    backend.clobber_thermal=True; backend.restore_fails=True
    with pytest.raises(ZemaxError) as exc:
        run(backend,dict(kind='thermal_controls',surface=1,fit_type=1,working_wavelength=2))
    assert exc.value.code=='STAR_RESTORE_FAILED'
    assert exc.value.details['original_error']['code']=='SETTING_REJECTED'
    assert backend.requires_reconnect and not backend.task['restoration']['restored']

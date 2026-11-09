"""Final NCE combinations and partial-error snapshots after native writes."""
from .errors import ZemaxError
from .data import unwrap
from .analyses import scalar_settings
from .imaging import check
from .detectors import check_setting_value
from .source_spectrum import requested_values


def verify_patch(backend,row,p,fields):
    def verify(obj,name,value,page):
        try:check(backend.native,obj,name,value)
        except ZemaxError as exc:
            exc.details.update(object=p.object,page=page,property=name)
            raise
    if p.object_type:verify(row,'Type',p.object_type,'object')
    for key,name in fields.items():
        if getattr(p,key)is not None:verify(row,name,getattr(p,key),'object')
    for key,name in [('file1','FileName1'),('file2','FileName2')]:
        if getattr(p,key)is not None:verify(row.CurrentTypeSettings,name,getattr(p,key),'files')
    for patch,getter,page in [(p.data,lambda:unwrap(row.ObjectData),'data'),(p.sources,lambda:row.SourcesData,'sources'),(p.type_settings,lambda:row.TypeData,'type_settings'),(p.diffraction,lambda:row.DiffractionData,'diffraction')]:
        if patch:
            obj=getter()
            for name,value in patch.items():verify(obj,name,value,page)
    for index,value in p.parameters.items():
        cell=row.GetObjectCell(backend.native.enum(backend.native.api.Editors.NCE.ObjectColumn,'Par'+str(index)))
        check_setting_value('parameter_'+str(index),value,backend._cell_value(cell))
    for face in p.faces:
        f=row.CoatScatterData.GetFaceData(face.face)
        if face.coating is not None:verify(f,'Coating',face.coating,'face '+str(face.face))
        if face.number_of_rays is not None:verify(f,'NumberOfRays',face.number_of_rays,'face '+str(face.face))
        if face.scatter_model:
            verify(f,'CurrentScatterModel',face.scatter_model,'face '+str(face.face))
            obj=getattr(f.CurrentScatterModelSettings,'_S_'+face.scatter_model)
            for name,value in face.settings.items():verify(obj,name,value,'face '+str(face.face))
    if p.volume:
        verify(row.VolumePhysicsData,'Model',p.volume.model,'volume')
        obj=getattr(row.VolumePhysicsData.ModelSettings,'_S_'+p.volume.model)
        for name,value in p.volume.settings.items():verify(obj,name,value,'volume')
        for index,value in p.volume.parameters.items():check_setting_value('volume_parameter_'+str(index),value,obj.GetParameterValue(index))
    if p.spectrum:
        verify(row.SourcesData,'SourceColor',p.spectrum.mode,'spectrum')
        obj=getattr(row.SourcesData.SourceColorSettings,'_S_'+p.spectrum.mode)
        for name,value in requested_values(p.spectrum).items():verify(obj,name,value,'spectrum')


def failure(backend,exc,index,completed,prepared,stage):
    error=exc if isinstance(exc,ZemaxError)else ZemaxError('NATIVE_ERROR',str(exc),type=type(exc).__name__)
    error.details.update(object=index,checkpoint=backend.last_checkpoint,completed_objects=list(completed),prepared_objects=list(prepared),stage=stage)
    try:
        row=backend._object(index)
        state={}
        for page,reader in [('object',lambda:scalar_settings(row)),('data',lambda:scalar_settings(unwrap(row.ObjectData)))]:
            try:state[page]=reader()
            except Exception as read_error:state[page]=dict(unavailable=str(read_error),type=type(read_error).__name__)
        error.details['failed_object_state']=state
    except Exception as read_error:error.details['failed_object_state_error']=dict(message=str(read_error),type=type(read_error).__name__)
    return error

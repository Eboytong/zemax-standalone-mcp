"""Regular apparent-exit-pupil coordinates from real marginal/chief rays."""
import math
from .errors import ZemaxError


def sine_angle(a,b):
    c=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    return math.sqrt(sum(v*v for v in c))


def real_f_numbers(rows):
    if len(rows)!=5 or any(r.get('error_code')or not r.get('direction')for r in rows):
        raise ZemaxError('PUPIL_REFERENCE_FAILED','主光线或边缘光线无有效方向。')
    chief=rows[0]['direction'];f=[]
    for plus,minus in ((1,2),(3,4)):
        aperture=sine_angle(rows[plus]['direction'],chief)+sine_angle(rows[minus]['direction'],chief)
        if not math.isfinite(aperture)or aperture<=1e-12:raise ZemaxError('PUPIL_REFERENCE_FAILED','边缘光线孔径角退化。')
        f.append(1/aperture)
    return f


def display_inverse(u,v,scales):
    px,py=u*scales[0],v*scales[1]
    residual=math.hypot(px/scales[0]-u,py/scales[1]-v)
    return dict(px=px,py=py,valid=px*px+py*py<=1+1e-12,coordinate_error=residual,
                error_unit='normalized apparent-pupil display coordinates',iterations=1)


def mapping_shell(grid,status,reason):
    return dict(status=status,sample_order='rows Y, columns X; original grid unchanged',
        coordinate_error=None,error_status=reason,validity_scope='regular apparent display-to-entrance-ray mapping, not a physical pupil-surface reconstruction',
        points=[[dict(px=None,py=None,valid=False,reason=reason)for _ in range(grid['nx'])]for _ in range(grid['ny'])])


class PupilMappingMixin:
    def _regular_pupil_reason(self,q):
        system=self.system;data=system.SystemData
        if not q.field or not q.wavelength:return 'explicit single field and wavelength required'
        if data.Aperture.AFocalImageSpace:return 'focused image space required'
        if str(data.Fields.GetFieldType())!='Angle':return 'first-stage reference uses angular fields'
        if str(data.Fields.Normalization)!='Radial':return 'first-stage field reference requires radial normalization'
        field=data.Fields.GetField(q.field)
        if abs(float(field.X))>1e-12:return 'first-stage independent reference is the Y meridian'
        if any(abs(float(getattr(field,n)))>1e-12 for n in ('VDX','VDY','VCX','VCY','VAN')):return 'vignetting transforms are outside the regular reference'
        if not data.Wavelengths.GetWavelength(q.wavelength).IsPrimary:return 'non-primary OPD/display reference has an unresolved recorded difference'
        for i in range(system.LDE.NumberOfSurfaces):
            row=self._row(i)
            if str(row.Type)not in ('Standard','EvenAspheric','OddAsphere','Paraxial'):return 'surface type outside the regular axisymmetric reference: '+str(row.Type)
            aperture=row.ApertureData
            if str(aperture.CurrentType)not in ('None','CircularAperture','FloatingAperture'):return 'unobscured circular apertures required: '+str(aperture.CurrentType)
            if str(aperture.CurrentType)=='CircularAperture'and float(aperture.CurrentTypeSettings._S_CircularAperture.MinimumRadius)>0:return 'annular pupil outside first-stage reference'
            tilt=row.TiltDecenterData
            for prefix in ('BeforeSurface','AfterSurface'):
                for name in ('DecenterX','DecenterY','TiltX','TiltY','TiltZ'):
                    if abs(float(getattr(tilt,prefix+name)))>1e-12:return 'tilt/decenter outside regular reference'
        return None

    def _pupil_ray_job(self,parent,rays,opd=True):
        from .models import BatchRays
        req=BatchRays(rays=rays,opd=opd)
        target=self.system.LDE.NumberOfSurfaces-1
        def launch(_):return self._composite('pupil_reference_rays',dict(ray_count=len(rays),opd=opd),lambda t:self._trace_flow(t,req,target))
        return (yield from self._child_job(parent,launch,None))

    def _wavefront_mapping_task(self,q):
        def flow(task):
            native_q=q.model_copy(update=dict(include_pupil_mapping=False))
            original=yield from self._child_job(task,self._run_general_analysis,native_q)
            if not original.get('grids'):raise ZemaxError('NO_RESULT_DATA','波前没有可用网格。',native_messages=original.get('native_messages'))
            task['settings']=original['task']['settings']
            task['settings']['requested']=q.model_dump()
            task['payload']={k:v for k,v in original.items()if k not in ('task','context','system_settings','rows')}
            if not q.use_exit_pupil:
                # Preserve the existing entrance guard-sample contract.
                for g in original['grids']:
                    cx,cy=g['nx']//2,g['ny']//2
                    g['pupil_mapping']=mapping_shell(g,'verified_entrance_guard_sample_formula',None)
                    g['pupil_mapping']['validity_scope']='coordinate-domain validity only; existing entrance guard formula, not a per-ray aperture or propagation check'
                    for iy,line in enumerate(g['pupil_mapping']['points']):
                        for ix,p in enumerate(line):
                            px,py=(ix-cx)/(cx-1),(iy-cy)/(cy-1)
                            p.update(px=px,py=py,valid=px*px+py*py<=1,reason=None if px*px+py*py<=1 else'outside circular entrance pupil')
                return
            reason=self._regular_pupil_reason(q)
            if reason:
                for g in original['grids']:g['pupil_mapping']=mapping_shell(g,'unsupported_regular_reference',reason)
                return
            fields=self.get_system_settings(None)['fields'];field=fields[q.field-1]
            scale=max(math.hypot(f['x'],f['y'])for f in fields)or 1.
            hx,hy=field['x']/scale,field['y']/scale
            def ray(px,py):return dict(hx=hx,hy=hy,px=px,py=py,wavelength=q.wavelength)
            seed=yield from self._pupil_ray_job(task,[ray(x,y)for x,y in ((0,0),(1,0),(-1,0),(0,1),(0,-1))])
            fs,ft=real_f_numbers(seed['rows']);native=[]
            for name in ('SFNO','TFNO'):
                native.append(float(self.system.MFE.GetOperandValue(self.native.enum(self.native.api.Editors.MFE.MeritOperandType,name),q.field,q.wavelength,0.,0.,0.,0.,0.,0.)))
            if any(abs(a-b)>1e-8+1e-7*abs(b)for a,b in zip((fs,ft),native)):
                raise ZemaxError('PUPIL_REFERENCE_FAILED','实际边缘光线与原生F-number不一致。',ray_f_numbers=[fs,ft],native_f_numbers=native)
            scales=[fs/min(fs,ft),ft/min(fs,ft)]
            raw=original
            if q.remove_tilt:raw=yield from self._child_job(task,self._run_general_analysis,native_q.model_copy(update=dict(remove_tilt=False)))
            for g,raw_grid in zip(original['grids'],raw['grids'],strict=True):
                mapping=mapping_shell(g,'verified_regular_display_mapping',None);g['pupil_mapping']=mapping
                g['coordinate_validation']='native display axes retained; entrance mapping validity and residuals are reported separately in pupil_mapping'
                mapping.update(real_f_numbers=dict(sagittal=fs,tangential=ft),native_f_numbers=native,scales=scales,
                    definition='guard u=(ix-floor(Nx/2))/(floor(Nx/2)-1); v analogous; entrance=(u*Fs/minF,v*Ft/minF)',
                    forward_definition='apparent display=(Px/scale_x,Py/scale_y)',jacobian_determinant=1/(scales[0]*scales[1]),
                    inverse='analytic inverse, one iteration; no OPD coordinate fitting',max_iterations=20,
                    coordinate_error=0.,error_status=None,opd_reference='CurrentAndChief, raw unremoved wavefront')
                cx,cy=g['nx']//2,g['ny']//2;locations=[];rays=[]
                for iy,line in enumerate(mapping['points']):
                    for ix,p in enumerate(line):
                        v=display_inverse((ix-cx)/(cx-1),(iy-cy)/(cy-1),scales)
                        if not v['valid']:
                            p.update(reason='outside entrance pupil or guard sample');continue
                        p.update(v,reason=None);locations.append((ix,iy));rays.append(ray(v['px'],v['py']))
                failures=0
                for start in range(0,len(rays),1024):
                    traced=yield from self._pupil_ray_job(task,rays[start:start+1024])
                    for (ix,iy),r in zip(locations[start:start+1024],traced['rows'],strict=True):
                        p=mapping['points'][iy][ix];expected=raw_grid['values'][iy][ix]
                        valid=not r.get('error_code')and not r.get('vignette_code')and r.get('position')is not None
                        difference=abs(r['opd']-expected)if valid and expected is not None else None
                        p.update(ray_error=r.get('error_code'),vignette_code=r.get('vignette_code'),opd_error_waves=difference)
                        if not valid or difference is None or difference>1e-8+1e-7*abs(expected):
                            failures+=1;p.update(px=None,py=None,valid=False,reason='ray/aperture failure'if not valid else'OPD reference mismatch')
                    task['progress']=min(99,10+int(89*min(start+1024,len(rays))/max(1,len(rays))))
                    yield
                mapping['invalid_reference_points']=failures
                if failures:mapping['status']='partial_regular_reference';mapping['error_status']='some ray/OPD comparisons did not pass'
        return self._composite('analysis',dict(kind='wavefront',requested=q.model_dump()),flow)

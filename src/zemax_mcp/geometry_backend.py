"""Native geometry observation and version-scoped optimization protection."""
import os
import time
import math
import json

from .data import utc_now
from .errors import ZemaxError
from .geometry import ALGORITHM_VERSION, check_radial_pair

UNIT_MM = {'Millimeters': 1, 'Centimeters': 10, 'Meters': 1000, 'Inches': 25.4}


class GeometryMixin:
    def _geometry_process(self,task,payload,budget_seconds):
        import subprocess
        import sys
        from pathlib import Path
        directory=Path(self.directory)
        token=task['task_id']+'_'+str(len(task.get('geometry_computations',[])))
        request_path=directory/(token+'_geometry_input.json')
        result_path=directory/(token+'_geometry_result.json')
        log_path=directory/(token+'_geometry.log')
        request_path.write_text(json.dumps(dict(payload,budget_seconds=max(.001,budget_seconds)),ensure_ascii=False),encoding='utf-8')
        started=time.monotonic()
        with log_path.open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-B','-m','zemax_mcp.geometry_worker',str(request_path),str(result_path)],
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            task['geometry_process']=process
            def partial_failure(code):
                path=result_path.with_suffix('.partial.json')
                try:partial=json.loads(path.read_text(encoding='utf-8'))
                except (OSError,ValueError):partial=dict(rows=[],entities=[],pairs=[],issues=[])
                partial.update(state='unverified',read_complete=False)
                partial.setdefault('issues',[]).append(dict(code=code,log=str(log_path)))
                return partial
            try:
                while process.poll() is None:
                    self._cancel_boundary(task)
                    if time.monotonic()-started>=budget_seconds:
                        process.kill()
                        process.wait(timeout=5)
                        return partial_failure('geometry_budget')
                    yield
                if process.returncode or not result_path.exists():
                    return partial_failure('geometry_process_failed')
                result=json.loads(result_path.read_text(encoding='utf-8'))
                task.setdefault('geometry_computations',[]).append(dict(result.get('compute_telemetry',{}),
                    kind=payload['kind'],wall_seconds=time.monotonic()-started))
                return result
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                task.pop('geometry_process',None)

    def geometry_summary(self):
        fact = getattr(self, '_geometry_fact', None)
        if not fact:
            return dict(state='pending', model_revision=self.revision, session_id=self.session_id)
        value={k:v for k,v in fact.items() if k not in {'rows','issues','engineering_checks','engineering_coverage','configurations','mesh_diagnostics','solid_geometry','entity_map'}}
        if fact.get('engineering_coverage'):
            coverage=fact['engineering_coverage']
            value['coverage_summary']=dict(total=len(coverage),satisfied=sum(r['state']=='satisfied' for r in coverage))
        if fact.get('solid_geometry'):
            solid=fact['solid_geometry']
            value['solid_summary']=dict(state=solid['state'],entity_count=len(solid.get('entities',[])),pair_count=len(solid.get('pairs',[])))
        if fact.get('mesh_diagnostics'):
            mesh=fact['mesh_diagnostics']
            value['mesh_summary']={k:mesh[k] for k in ('state','entity_count','triangle_count','elapsed_seconds') if k in mesh}
        if fact.get('session_id')!=self.session_id or fact.get('model_revision')!=self.revision:value['state']='expired'
        return value | dict(issue_count=len(fact.get('issues',[]))+sum(p.get('state')!='passed' for p in fact.get('rows',[])))

    def _geometry_observation(self, budget_seconds=120, *, read_only=False):
        """Read native surfaces without changing the model or claiming mesh fidelity."""
        started=time.monotonic()
        config=int(self.system.MCE.CurrentConfiguration) if str(self.system.Mode)=='Sequential' else None
        result=dict(state='unverified',session_id=self.session_id,model_revision=self.revision,
                    generation=os.environ.get('ZEMAX_GENERATION'),worker_generation=os.environ.get('ZEMAX_WORKER_GENERATION'),
                    configuration=config,algorithm_version=ALGORITHM_VERSION,unit='mm',
                    source='native_LDE',checked_at=utc_now(),rows=[],issues=[],
                    engineering_state='unregistered',constraint_version=0,scope='system',read_complete=False)
        environment=getattr(self.system.SystemData,'Environment',None)
        result['temperature_c']=float(environment.Temperature) if environment is not None else None
        result['configuration_count']=int(self.system.MCE.NumberOfConfigurations) if str(self.system.Mode)=='Sequential' else 1
        result['checked_configurations']=[config] if config is not None else []
        if str(self.system.Mode)!='Sequential':
            result.update(source='native_NCE',native_unit=str(self.system.SystemData.Units.LensUnits))
            result['issues'].append(dict(code='nsc_entity_export_not_verified'));return result
        units=str(self.system.SystemData.Units.LensUnits);result['native_unit']=units
        scale=UNIT_MM.get(units)
        if scale is None:
            result['issues'].append(dict(code='unknown_length_unit',unit=units));return result
        faces=[]; count=int(self.system.LDE.NumberOfSurfaces)
        for i in range(1,count-1):
            if time.monotonic()-started>budget_seconds:
                result['issues'].append(dict(code='read_budget',surface=i));break
            try:
                row=self._row(i); kind=str(row.Type)
                face=dict(surface=i,radius=float(row.Radius),conic=float(row.Conic),
                          semi_diameter=float(row.SemiDiameter),mechanical_semi_diameter=float(row.MechanicalSemiDiameter),
                          thickness=float(row.Thickness),material=str(row.Material),coefficients=[],surface_type=kind)
                policy=getattr(self,'_engineering_policy',None)
                exterior=next((e for e in policy.mechanical_exteriors if e.surface==i or (
                    e.surface==i-1 and str(self._row(i-1).Material).strip() not in {'','MIRROR','ABSORB'})),None) if policy else None
                if exterior:
                    face['native_mechanical_semi_diameter']=face['mechanical_semi_diameter']
                    face['mechanical_semi_diameter']=exterior.outer_radius_mm/scale
                    face['mechanical_exterior_id']=exterior.id
                    if face['mechanical_semi_diameter']<face['semi_diameter']:
                        raise ValueError('mechanical_exterior_smaller_than_optical_aperture')
                if math.isinf(face['radius']):face['radius']=0.0
                if not all(math.isfinite(face[key]) for key in ('radius','conic','semi_diameter','mechanical_semi_diameter','thickness')):
                    raise ValueError('native_surface_dimensions_not_finite')
                if kind not in {'Standard','EvenAspheric','ExtendedPolynomial'}:
                    raise ValueError('surface_requires_native_entity_export:'+kind)
                if kind=='EvenAspheric':
                    # Read coefficient headers rather than assuming parameter offsets.
                    powers={}
                    for n in range(1,21):
                        cell=self._cell(row,'parameter_'+str(n))
                        if not cell.IsActive:continue
                        header=str(cell.Header).lower().replace(' ','')
                        import re
                        match=re.fullmatch(r'(\d+)(?:(?:th|nd|st|rd)?order(?:term)?|阶项)',header)
                        if match:
                            power=int(match[1]);value=float(self._cell_value(cell))
                            if power==2:face['quadratic']=value
                            elif power>=4 and power%2==0:powers[power]=value
                            elif value:raise ValueError('unsupported_aspheric_term:'+header)
                        else:raise ValueError('aspheric_coefficient_header_unverified:'+header)
                    if not powers:raise ValueError('aspheric_coefficient_contract_unverified')
                    face['coefficients']=[powers.get(n,0) for n in range(4,max(powers)+1,2)]
                    from .geometry import _sag
                    for fraction in (0,.27,.61,.97):
                        r=face['mechanical_semi_diameter']*fraction
                        ok,sag,_=self.system.LDE.GetSag(i,r,0)
                        if not ok or not math.isfinite(sag) or abs((float(sag)-_sag(face,r*r))*scale)>1e-7:
                            raise ValueError('native_sag_contract_mismatch')
                if kind=='ExtendedPolynomial':
                    if face['radius']!=0:raise ValueError('polynomial_base_conic_requires_bounded_adapter')
                    terms=int(self._cell_value(self._cell(row,'parameter_13')))
                    normalization=float(self._cell_value(self._cell(row,'parameter_14')))
                    if not 0<=terms<=230 or normalization<=0:raise ValueError('invalid_polynomial_definition')
                    powers=[(degree-j,j) for degree in range(1,21) for j in range(degree+1)]
                    coefficients=[]
                    for n,(px,py) in enumerate(powers[:terms],15):
                        cell=self._cell(row,'parameter_'+str(n))
                        if not cell.IsActive:raise ValueError('inactive_polynomial_coefficient')
                        value=float(self._cell_value(cell))
                        if not math.isfinite(value):raise ValueError('nonfinite_polynomial_coefficient')
                        if value:coefficients.append([px,py,value])
                    face.update(polynomial=coefficients,normalization=normalization,requires_3d=True)
                    for fx,fy in ((0,0),(.21,.37),(-.43,.19),(.67,-.35)):
                        x=face['mechanical_semi_diameter']*fx;y=face['mechanical_semi_diameter']*fy
                        ok,sag,_=self.system.LDE.GetSag(i,x,y)
                        expected=sum(c*(x/normalization)**px*(y/normalization)**py for px,py,c in coefficients)
                        if not ok or not math.isfinite(sag) or abs((float(sag)-expected)*scale)>1e-7:
                            raise ValueError('native_polynomial_sag_contract_mismatch:'+json.dumps(dict(x=x,y=y,
                                expected=expected,actual=float(sag),success=bool(ok),normalization=normalization)))
                matrix=self.system.LDE.GetGlobalMatrix(i)
                if not matrix[0]:raise ValueError('missing_global_transform')
                rotation=list(matrix[1:10]); translation=list(matrix[10:13])
                face['rotation']=rotation
                face['translation_mm']=[v*scale for v in translation]
                identity=[1,0,0,0,1,0,0,0,1]
                if any(abs(a-b)>1e-10 for a,b in zip(rotation,identity)) or any(abs(v*scale)>1e-9 for v in translation[:2]):
                    face['requires_3d']=True
                aperture=row.ApertureData
                if str(aperture.CurrentType) not in {'None','CircularAperture','FloatingAperture'}:
                    raise ValueError('noncircular_entity_boundary')
                face['z_mm']=translation[2]*scale
                faces.append(face)
            except Exception as exc:
                result['issues'].append(dict(code='surface_unverified',surface=i,reason=str(exc)))
                faces.append(None)
        result['read_complete']=len(faces)==count-2 and all(f is not None for f in faces)
        if read_only:
            return dict(result,surface_data=faces,scale_mm=scale,native_read_seconds=time.monotonic()-started)
        from .geometry import check_radial_model
        result=check_radial_model(result,faces,scale,budget_seconds-(time.monotonic()-started))
        self._evaluate_engineering(result,faces,scale)
        result['elapsed_seconds']=round(time.monotonic()-started,6)
        return result

    def _evaluate_engineering(self,result,faces,scale):
        policy=getattr(self,'_engineering_policy',None)
        if not policy:return
        result['constraint_version']=policy.version
        result['engineering_state']='provisional'
        result['native_constraints_state']='caller_managed'
        result['engineering_checks']=[]
        if not getattr(self,'_engineering_mapping_valid',True):
            result['engineering_state']='unverified'
            result['issues'].append(dict(code='engineering_mapping_required'))
            return
        for rule in policy.constraints:
            face=next((f for f in faces if f and f['surface']==rule.surface),None)
            pair=next((p for p in result['rows'] if p['surfaces'][0]==rule.surface),None)
            row=dict(id=rule.id,kind=rule.kind,surface=rule.surface,object=rule.object,
                     configuration=result.get('configuration'),required=rule.limit,unit=rule.unit,state='unverified')
            if rule.configurations and result.get('configuration') not in rule.configurations:
                result['engineering_checks'].append(dict(row,state='not_applicable',reason='configuration_outside_scope'))
                continue
            bounds=None
            row['coverage']='diagnostic_only'
            if (rule.other_object is not None and rule.kind!='min_gap') or (rule.other_surface is not None and
                    rule.kind!='min_gap'):
                row['reason']='explicit_boundary_pair_adapter_required'
                result['engineering_checks'].append(row)
                continue
            if rule.region and (rule.kind not in {'min_wall_thickness','min_gap'} or
                    (rule.kind=='min_gap' and rule.object is None and set(rule.region)-{'r_min_mm','r_max_mm'}and
                     set(rule.region)!={f'{a}_{end}_mm'for a in 'xy'for end in ['min','max']})):
                row['reason']='engineering_region_adapter_required'
                result['engineering_checks'].append(row)
                continue
            if rule.temperature_c is not None and result.get('temperature_c')!=rule.temperature_c:
                row.update(state='unverified',reason='temperature_not_confirmed')
                result['engineering_checks'].append(row)
                continue
            if rule.material and (not face or face.get('material')!=rule.material):
                row.update(state='unverified',reason='material_scope_mismatch')
                result['engineering_checks'].append(row)
                continue
            if rule.kind=='min_gap' and rule.object is not None and rule.other_object is not None:
                row['deferred']='solid_object_gap'
                result['engineering_checks'].append(row)
                continue
            if face:
                from .geometry import _sag
                radius=face['mechanical_semi_diameter']
                if rule.kind=='min_edge_thickness' and pair and pair['medium']=='glass':
                    back=next((f for f in faces if f and f['surface']==rule.surface+1),None)
                    if back:
                        v=(face['thickness']+_sag(back,radius*radius)-_sag(face,radius*radius))*scale
                        bounds=[v-1e-8,v+1e-8]
                if rule.kind=='min_vertex_radius' and face['radius']:
                    bounds=[abs(face['radius'])*scale]*2
                if rule.kind=='min_clear_aperture':bounds=[2*face['semi_diameter']*scale]*2
                if rule.kind=='min_installation_margin':bounds=[(face['mechanical_semi_diameter']-face['semi_diameter'])*scale]*2
                if rule.kind in {'max_surface_slope','max_aspheric_departure','max_curvature'} and 'polynomial' not in face:
                    from .geometry import surface_metric_bounds
                    bounds=surface_metric_bounds(face,rule.kind,scale)

            if face and rule.kind=='max_mechanical_radius':bounds=[face['mechanical_semi_diameter']*scale]*2
            if pair and rule.kind=='min_center_thickness' and pair['medium']=='glass':bounds=[face['thickness']*scale]*2
            if pair and ((rule.kind=='min_thickness' and pair['medium']=='glass') or (rule.kind=='min_gap' and pair['medium']=='air')):
                bounds=pair.get('minimum_mm')
            if rule.kind=='min_gap' and (rule.other_surface is not None or rule.region):
                other=rule.other_surface if rule.other_surface is not None else rule.surface+1
                back=next((f for f in faces if f and f['surface']==other),None)
                row['boundary_surfaces']=[rule.surface,other]
                if face is None or back is None:
                    row['reason']='selected_boundary_unavailable'
                    bounds=None
                else:
                    from .geometry import selected_radial_gap
                    selected=selected_radial_gap(face,back,scale,rule.region)
                    bounds=selected.pop('bounds',None)
                    row.update(selected)
                    if selected.get('reason')=='selected_boundary_requires_3d_adapter':
                        row.pop('reason',None);row['deferred']='surface_patch_gap'
            if bounds and all(__import__('math').isfinite(v) for v in bounds):
                row['actual_interval']=bounds
                if rule.unit=='mm':row['actual_interval_mm']=bounds
                tolerance=1e-6 if rule.unit=='mm' else 1e-10
                if rule.kind.startswith('min_'):
                    row['state']='satisfied' if bounds[0]>=rule.limit-tolerance else ('violated' if bounds[1]<rule.limit-tolerance else 'unverified')
                else:row['state']='satisfied' if bounds[1]<=rule.limit+tolerance else ('violated' if bounds[0]>rule.limit+tolerance else 'unverified')
            result['engineering_checks'].append(row)
        statuses=[row['state'] for row in result['engineering_checks']]
        if 'violated' in statuses:result['engineering_state']='violated'
        elif 'unverified' in statuses or not any(s!='not_applicable' for s in statuses):result['engineering_state']='unverified'

    def _check_geometry_now(self,budget_seconds=120):
        try:
            result=self._geometry_observation(budget_seconds)
        except Exception as exc:
            result=dict(state='unverified',session_id=self.session_id,model_revision=self.revision,
                        issues=[dict(code='native_geometry_read_failed',reason=str(exc))],rows=[])
        self._geometry_fact=result
        return result

    def start_geometry_check(self,req):
        if req.engineering_policy is not None:
            previous=getattr(self,'_engineering_policy',None)
            if previous and req.engineering_policy.version<previous.version:
                raise ZemaxError('ENGINEERING_VERSION_STALE','工程约束版本已过期。')
            if previous and req.engineering_policy.version==previous.version and req.engineering_policy!=previous:
                raise ZemaxError('ENGINEERING_VERSION_CONFLICT','同一工程版本不能包含不同内容。')
            if not previous or previous.version!=req.engineering_policy.version:
                self._engineering_policy=req.engineering_policy
                self._engineering_mapping_valid=True
                if getattr(self,'_geometry_fact',None):self._geometry_fact={**self._geometry_fact,'state':'expired'}
        sequential=str(self.system.Mode)=='Sequential'
        original=int(self.system.MCE.CurrentConfiguration) if sequential else None
        count=int(self.system.MCE.NumberOfConfigurations) if sequential else 1
        configs=req.configurations or (list(range(1,count+1)) if req.configuration_scope=='required' else [original])
        if sequential and any(not 1<=c<=count for c in configs):raise ZemaxError('INDEX_OUT_OF_RANGE','几何检查组态编号越界。')
        def flow(task):
            started=time.monotonic();facts=[]
            try:
                for config in configs:
                    self._cancel_boundary(task)
                    yield
                    if sequential and int(self.system.MCE.CurrentConfiguration)!=config:
                        self.system.MCE.SetCurrentConfiguration(config)
                        if int(self.system.MCE.CurrentConfiguration)!=config:raise ZemaxError('SETTING_REJECTED','组态切换未采用。')
                    remaining=req.budget_seconds-(time.monotonic()-started)
                    if remaining<=0:break
                    snapshot=self._geometry_observation(remaining,read_only=True)
                    faces=snapshot.pop('surface_data',[])
                    scale=snapshot.pop('scale_mm',1)
                    version=self.revision
                    computed=yield from self._geometry_process(task,dict(kind='radial',fact=snapshot,faces=faces,scale_mm=scale),remaining)
                    computed['check']=req.check
                    if self.revision!=version:
                        computed.update(state='expired',read_complete=False)
                        computed.setdefault('issues',[]).append(dict(code='model_changed_during_check'))
                    self._evaluate_engineering(computed,faces,scale)
                    pending=[]
                    for check in computed.get('engineering_checks',[]):
                        if check.get('deferred')!='surface_patch_gap':continue
                        rule=next(r for r in self._engineering_policy.constraints if r.id==check['id'])
                        first,second=(next(f for f in faces if f and f['surface']==i)for i in check['boundary_surfaces'])
                        pending.append(dict(id=check['id'],front=first,back=second,scale_mm=scale,target_mm=req.representation_tolerance_mm,region=rule.region))
                    if pending:
                        measured=yield from self._geometry_process(task,dict(kind='surface_gaps',requests=pending),max(.001,req.budget_seconds-(time.monotonic()-started)))
                        computed['surface_gap_measurements']=measured.get('measurements',[])
                        returned={m['id']for m in measured.get('measurements',[])}
                        for request in pending:
                            if request['id']not in returned:
                                check=next(c for c in computed['engineering_checks']if c['id']==request['id'])
                                check.update(state='unverified',reason='surface_gap_computation_incomplete',computation_issues=measured.get('issues',[]))
                        for row in measured.get('measurements',[]):
                            check=next(c for c in computed['engineering_checks']if c['id']==row['id'])
                            if row['state']=='measured':
                                low,high=row['interval_mm']
                                check.update(actual_interval_mm=[low,high],actual_interval=[low,high],position_mm=row['position_mm'],measurement_source=row['source'],state='satisfied'if low>=check['required']else'violated'if high<check['required']else'unverified')
                            else:check.update(state='unverified',reason=row.get('reason','surface_patch_unverified'))
                    self._geometry_fact=computed
                    if req.check=='full':
                        yield from self._geometry_solids(task,computed,faces,scale,req,started)
                    facts.append(computed)
                    task['progress']=int(len(facts)*100/len(configs))
            finally:
                if sequential and int(self.system.MCE.CurrentConfiguration)!=original:
                    self.system.MCE.SetCurrentConfiguration(original)
                    if int(self.system.MCE.CurrentConfiguration)!=original:
                        self._geometry_fact=None
                        raise ZemaxError('CONFIGURATION_RESTORE_FAILED','检查后原组态恢复未确认。')
                if facts:
                    fact=dict(facts[0]);fact['configurations']=facts
                    fact['configuration']=original;fact['checked_configurations']=[f['configuration'] for f in facts]
                    fact['state']='failed' if any(f['state']=='failed' for f in facts) else ('passed' if len(facts)==len(configs) and all(f['state']=='passed' for f in facts) else 'unverified')
                    fact['engineering_state']=next((s for s in ('violated','unverified','unregistered','provisional') if any(f.get('engineering_state')==s for f in facts)),'unregistered')
                    fact['rows']=[dict(row,configuration=f['configuration']) for f in facts for row in f.get('rows',[])]
                    fact['issues']=[dict(issue,configuration=f['configuration']) for f in facts for issue in f.get('issues',[])]
                    fact['engineering_checks']=[dict(row,configuration=f['configuration']) for f in facts for row in f.get('engineering_checks',[])]
                    policy=getattr(self,'_engineering_policy',None)
                    if policy:
                        required_configs=list(range(1,count+1)) if sequential else [None]
                        coverage=[]
                        for rule in policy.constraints:
                            for config in rule.configurations or required_configs:
                                actual=next((r for r in fact['engineering_checks'] if r['id']==rule.id and r['configuration']==config),None)
                                coverage.append(dict(id=rule.id,configuration=config,state=actual['state'] if actual else 'unverified'))
                        states=[r['state'] for r in coverage]
                        fact['engineering_coverage']=coverage
                        fact['engineering_state']='violated' if 'violated' in states else ('unverified' if not states or any(s!='satisfied' for s in states) else 'provisional')
                    if len(facts)!=len(configs):fact['issues']=[*fact.get('issues',[]),dict(code='configuration_budget',requested=configs)]
                    self._geometry_fact=fact
                    task['payload']={'geometry':fact};task['rows']=fact['rows'];task['summary']=self.geometry_summary()
        return self._composite('geometry_check',req.model_dump(),flow,require_sequential=False)

    def _geometry_solids(self,task,fact,faces,scale,req,started):
        from .export_models import CadExport
        sequential=str(self.system.Mode)=='Sequential'
        entities=[];relations=[];complete=True
        if sequential:
            count=int(self.system.LDE.NumberOfSurfaces)
            for i in range(1,count-1):
                if str(self._row(i).Material).strip().upper() in {'MIRROR','ABSORB'}:
                    complete=False
                    fact.setdefault('issues',[]).append(dict(code='physical_entity_adapter_required',surface=i,
                        reason='reflective_or_absorbing_substrate_and_edge_required'))
            indexed={f['surface']:f for f in faces if f}
            for i in range(1,count-2):
                material=str(self._row(i).Material).strip()
                if not material or material.upper() in {'MIRROR','ABSORB'}:continue
                a,b=indexed.get(i),indexed.get(i+1)
                entity=dict(id=f'S{i}-S{i+1}',surfaces=[i,i+1],material=material,source='native_STEP',representation_error_mm=None)
                if a and b and a['surface_type']==b['surface_type']=='Standard' and a['conic']==b['conic']==0:
                    expected=[a['translation_mm'][k]+a['rotation'][3*k+2]*a['thickness']*scale for k in range(3)]
                    equal_axes=all(abs(x-y)<1e-9 for x,y in zip(a['rotation'],b['rotation']))
                    equal_edges=abs(a['mechanical_semi_diameter']-b['mechanical_semi_diameter'])*scale<1e-8
                    if equal_axes and equal_edges and all(abs(x-y)<1e-7 for x,y in zip(expected,b['translation_mm'])):
                        entity.update(source='native_LDE_analytic_solid',representation_error_mm=0,native_definition=dict(
                            radii_mm=[a['radius']*scale,b['radius']*scale],thickness_mm=a['thickness']*scale,
                            mechanical_radius_mm=a['mechanical_semi_diameter']*scale,rotation=a['rotation'],translation_mm=a['translation_mm']))
                if a and b and {a['surface_type'],b['surface_type']}<={'Standard','ExtendedPolynomial'} and a['radius']==b['radius']==0:
                    expected=[a['translation_mm'][k]+a['rotation'][3*k+2]*a['thickness']*scale for k in range(3)]
                    equal_axes=all(abs(x-y)<1e-9 for x,y in zip(a['rotation'],b['rotation']))
                    equal_edges=abs(a['mechanical_semi_diameter']-b['mechanical_semi_diameter'])*scale<1e-8
                    if equal_axes and equal_edges and all(abs(x-y)<1e-7 for x,y in zip(expected,b['translation_mm'])):
                        # Each cap is expressed in the same physical mm basis.
                        polynomials=[[[px,py,c*scale/(f.get('normalization',1)*scale)**(px+py)]
                                      for px,py,c in f.get('polynomial',[])] for f in (a,b)]
                        entity.update(source='native_LDE_polynomial_solid',native_definition=dict(kind='polynomial',
                            polynomials=polynomials,normalization_mm=1,thickness_mm=a['thickness']*scale,
                            mechanical_radius_mm=a['mechanical_semi_diameter']*scale,rotation=a['rotation'],translation_mm=a['translation_mm']))
                if 'native_definition' not in entity and a and b and {a['surface_type'],b['surface_type']}<={'Standard','EvenAspheric'}:
                    expected=[a['translation_mm'][k]+a['rotation'][3*k+2]*a['thickness']*scale for k in range(3)]
                    if all(abs(x-y)<1e-9 for x,y in zip(a['rotation'],b['rotation'])) and abs(a['mechanical_semi_diameter']-b['mechanical_semi_diameter'])*scale<1e-8 and all(abs(x-y)<1e-7 for x,y in zip(expected,b['translation_mm'])):
                        profiles=[dict(radius_mm=f['radius']*scale,conic=f['conic'],terms=[
                            [2,f.get('quadratic',0)/scale],*[[2*n+4,c/scale**(2*n+3)] for n,c in enumerate(f['coefficients'])]]) for f in (a,b)]
                        entity.update(source='native_LDE_bounded_radial_solid',native_definition=dict(kind='radial',
                            profiles=profiles,target_error_mm=req.representation_tolerance_mm,thickness_mm=a['thickness']*scale,mechanical_radius_mm=a['mechanical_semi_diameter']*scale,
                            rotation=a['rotation'],translation_mm=a['translation_mm']))
                if 'native_definition' not in entity:
                    path=self.directory/(task['task_id']+f'_c{fact.get("configuration")}_S{i}.step')
                    try:
                        yield from self._child_job(task,self.run_cad_export,CadExport(path=str(path),format='STEP',start=i,end=i+1,tolerance='N_TenEMinus7'))
                        entity['path']=str(path)
                    except ZemaxError as exc:
                        complete=False
                        fact.setdefault('issues',[]).append(dict(code='entity_export_failed',entity=entity['id'],reason=str(exc)))
                        continue
                entities.append(entity)
            for a,b in zip(entities,entities[1:]):
                if a['surfaces'][1]==b['surfaces'][0]:
                    relations.append(dict(kind='cemented',entities=[a['id'],b['id']],native_verified=True))
        else:
            for i in range(1,int(self.system.NCE.NumberOfObjects)+1):
                row=self._object(i)
                if str(row.Type).startswith(('Source','Detector','Null')):continue
                entity=dict(id=f'O{i}',object=i,inside_of=f'O{int(row.InsideOf)}' if int(row.InsideOf)>0 else None,material=str(row.Material),source='native_STEP',representation_error_mm=None)
                unit=str(self.system.SystemData.Units.LensUnits);native_scale=UNIT_MM.get(unit)
                if str(row.Type)=='RectangularVolume' and native_scale is not None:
                    from .data import unwrap
                    data=unwrap(row.ObjectData)
                    dims=[float(getattr(data,k))for k in ['X1HalfWidth','Y1HalfWidth','X2HalfWidth','Y2HalfWidth','ZLength']]
                    if all(math.isfinite(v)and v>0 for v in dims)and dims[:2]==dims[2:4]:
                        transform=self._nsc_transform(i)
                        entity.update(source='native_NCE_analytic_box',representation_error_mm=0,native_definition=dict(
                            kind='box',half_x_mm=dims[0]*native_scale,half_y_mm=dims[1]*native_scale,length_mm=dims[4]*native_scale,
                            rotation=[v for r in transform['rotation']for v in r],translation_mm=[v*native_scale for v in transform['translation']]))
                if 'native_definition'not in entity:
                    path=self.directory/(task['task_id']+f'_object_{i}.step')
                    yield from self._child_job(task,self.run_cad_export,CadExport(path=str(path),format='STEP',start=i,end=i,tolerance='N_TenEMinus7'))
                    entity['path']=str(path)
                entities.append(entity)
        policy=getattr(self,'_engineering_policy',None)
        for entity in entities:
            entity['wall_requests']=[dict(id=r.id,faces=r.faces,region=r.region) for r in policy.constraints
                if r.kind=='min_wall_thickness' and (entity['id']==f'O{r.object}' or r.surface in entity.get('surfaces',[]))] if policy else []
        declared_relations=[]
        for relation in policy.relations if policy else []:
            if relation.configurations and fact.get('configuration') not in relation.configurations:continue
            r=relation.model_dump();r['native_verified']=False
            if not sequential and relation.kind in {'nested','intentional_overlap'}:
                try:
                    first,second=(int(e.removeprefix('O')) for e in relation.entities)
                    if relation.kind=='nested':
                        from .geometry import native_containment_path
                        parents={e['id']:e.get('inside_of')for e in entities}
                        path=native_containment_path(parents,f'O{first}',f'O{second}')or native_containment_path(parents,f'O{second}',f'O{first}')
                        r['native_verified']=path is not None
                        if path:r.update(native_child=path[0],native_verification_path=path)
                    else:r['native_verified']=int(self._object(first).InsideOf)==second or int(self._object(second).InsideOf)==first
                except (ValueError,AttributeError):pass
            declared_relations.append(r)
        from .geometry import merge_native_relations
        relations=merge_native_relations(relations,declared_relations)
        remaining=req.budget_seconds-(time.monotonic()-started)
        if remaining<=0:
            fact.setdefault('issues',[]).append(dict(code='solid_check_budget'))
            fact['state']='unverified' if fact['state']!='failed' else 'failed'
            return
        gap_requests=[dict(id=check['id'],entities=[f'O{rule.object}',f'O{rule.other_object}'],region=rule.region)
            for check in fact.get('engineering_checks',[]) for rule in policy.constraints
            if check['id']==rule.id and check.get('deferred')=='solid_object_gap']if policy else []
        solid=yield from self._geometry_process(task,dict(kind='step',entities=entities,relations=relations,gap_requests=gap_requests),remaining)
        fact['solid_geometry']=solid
        fact['entity_map']=[{k:v for k,v in e.items() if k not in {'native_definition','path'}} for e in entities]
        if policy:
            measurements={m['id']:m for e in solid.get('entities',[]) for m in e.get('wall_measurements',[])}
            measurements.update({m['id']:m for m in solid.get('gap_measurements',[])})
            for check in fact.get('engineering_checks',[]):
                rule=next(r for r in policy.constraints if r.id==check['id'])
                measured=measurements.get(rule.id)
                if measured and measured['state']!='measured'and not check.get('reason'):
                    check['reason']=measured.get('reason','solid_measurement_unverified')
                if measured and measured['state']=='measured' and not check.get('reason'):
                    low,high=measured['interval_mm']
                    check.update(actual_interval=[low,high],actual_interval_mm=[low,high],state='satisfied' if low>=rule.limit else 'violated' if high<rule.limit else 'unverified',position_mm=measured.get('position_mm'),measurement_source=measured.get('source'))
            states=[r['state'] for r in fact.get('engineering_checks',[])]
            fact['engineering_state']='violated' if 'violated' in states else 'unverified' if 'unverified' in states else 'provisional'
        if solid['state']=='failed':fact['state']='failed'
        elif solid['state']=='passed' and complete and fact['state']!='failed':
            covered={surface for entity in entities for surface in entity.get('surfaces',[])}
            fact['issues']=[issue for issue in fact.get('issues',[]) if not (
                (issue.get('code') in {'transformed_entity_requires_3d','surface_unverified'} and issue.get('surface') in covered) or
                (not sequential and issue.get('code')=='nsc_entity_export_not_verified'))]
            fact.update(state='unverified' if fact['issues'] else 'passed',read_complete=not fact['issues'])
        elif fact['state']=='passed':fact['state']='unverified'
        fact['read_complete']=fact.get('read_complete',False) and complete

    def _geometry_mesh_diagnostics(self,task,req,started):
        from pathlib import Path
        from .export_models import CadExport
        from .geometry_export import visualization_mesh
        from .geometry import check_meshes
        fact=self._geometry_fact
        if fact.get('model_revision')!=self.revision:return
        meshes=[];artifacts=[]
        try:
            if str(self.system.Mode)=='Sequential':
                groups=[]
                for i in range(1,int(self.system.LDE.NumberOfSurfaces)-2):
                    material=str(self._row(i).Material).strip().upper()
                    if material and material not in {'MIRROR','ABSORB'}:groups.append((i,i+1))
                if not groups:raise ValueError('no_identified_solid_intervals')
                export=self.directory/(task['task_id']+'_geometry.json')
                native=yield from self._child_job(task,self.run_cad_export,CadExport(path=str(export),format='VisualizationJSON'))
                data=json.loads(export.read_text(encoding='utf-8'))
                meshes=[visualization_mesh(data,surfaces=list(g)) for g in groups]
                artifacts.extend(native.get('artifacts',[]))
            else:
                for i in range(1,int(self.system.NCE.NumberOfObjects)+1):
                    if time.monotonic()-started>req.budget_seconds:raise TimeoutError('export_budget')
                    row=self._object(i);kind=str(row.Type)
                    if kind.startswith(('Source','Detector','Null')):continue
                    export=self.directory/(task['task_id']+f'_object_{i}.json')
                    native=yield from self._child_job(task,self.run_cad_export,CadExport(path=str(export),format='VisualizationJSON',start=i,end=i))
                    data=json.loads(export.read_text(encoding='utf-8'))
                    meshes.append(visualization_mesh(data,object_id=i));artifacts.extend(native.get('artifacts',[]))
            remaining=req.budget_seconds-(time.monotonic()-started)
            if remaining<=0:raise TimeoutError('mesh_budget')
            fact['mesh_diagnostics']=check_meshes(meshes,budget_seconds=remaining)
            fact['mesh_diagnostics']['entity_count']=len(meshes)
            fact['mesh_diagnostics']['triangle_count']=sum(len(m['triangles']) for m in meshes)
            # Native visualization has no verified maximum chord-error contract.
            # Keep the exact issue visible even when its diagnostic mesh is closed.
            fact.setdefault('issues',[]).append(dict(code='native_export_precision_unverified'))
        except (ValueError,KeyError,OSError,TimeoutError,ZemaxError) as exc:
            fact.setdefault('issues',[]).append(dict(code='mesh_diagnostics_unverified',reason=str(exc)))
        task['payload']={'geometry':fact,'artifacts':artifacts};task['summary']=self.geometry_summary()




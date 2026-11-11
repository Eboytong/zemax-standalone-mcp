"""Real stdio, native optimizer and independent multi-film transfer matrices."""
import asyncio
import cmath
import math
from pathlib import Path
from uuid import uuid4

import pytest

from tests.support.native import execute
from tests.support.thin_film import bk7_index


def stack_rta(wave,angle,direction,layers,polarization):
    n0,ns=(1.,bk7_index(wave)) if direction=='inward' else (bk7_index(wave),1.)
    if direction=='outward':layers=list(reversed(layers))
    transverse=n0*math.sin(math.radians(angle))
    def admittance(n):
        c=cmath.sqrt(1-(transverse/n)**2)
        return (n*c if polarization=='s' else n/c),c
    q0,_=admittance(n0);qs,_=admittance(ns)
    a,b,c,d=1.,0.,0.,1.
    for n,thickness in layers:
        q,cosine=admittance(n);delta=2*math.pi*n*thickness*cosine/wave
        u,v,w,z=cmath.cos(delta),1j*cmath.sin(delta)/q,1j*q*cmath.sin(delta),cmath.cos(delta)
        a,b,c,d=a*u+b*w,a*v+b*z,c*u+d*w,c*v+d*z
    denominator=q0*a+q0*qs*b+c+qs*d
    r=(q0*a+q0*qs*b-c-qs*d)/denominator;t=2*q0/denominator
    reflection=abs(r)**2;transmission=abs(t)**2*qs.real/q0.real
    return dict(reflection=reflection,transmission=transmission,absorption=1-reflection-transmission)


@pytest.mark.zemax
def test_fixed_stack_native_optimizer_stdio():
    name='D6'+uuid4().hex[:6].upper()
    text=(f'MATE {name}_L\n0.4 1.38 0\n0.8 1.38 0\n'
          f'MATE {name}_H\n0.4 2.1 0\n0.8 2.1 0\n'
          f'COAT {name}_ONE\n{name}_L .1 1 0\n'
          f'COAT {name}_REL\n{name}_L .25 0 0\n'
          f'COAT {name}_TWO\n{name}_L .1 1 0\n{name}_H .08 1 0\n')
    resource=Path.home()/'Documents/Zemax/Coatings'/(name+'.DAT');resource.write_text(text,encoding='ascii')
    async def work(e):
        (e.folder/resource.name).write_text(text,encoding='ascii')
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],files=dict(coating_file=resource.name))))
        for suffix,film in [('ONE',[(1.38,.1)]),('REL',[(1.38,.25*.55/1.38)]),('TWO',[(1.38,.1),(2.1,.08)])]:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',coating=name+'_'+suffix,replace_solves=True)]))
            await e.call('update_coating_layers',dict(request=dict(surface=1,use_layer_multiplier_and_offsets=True,
                layers=[dict(layer=i,thickness_multiplier=.6 if i==1 else 1) for i in range(1,len(film)+1)])))
            before=await e.call('get_surfaces',dict(start=0,count=3))
            layers=await e.call('get_coating_layers',dict(request=dict(surface=1)))
            status=await e.call('get_status');settings=await e.call('get_system_settings')
            wave=.65 if suffix=='REL' else .55
            objectives=[dict(wavelength_um=wave,polarization='s',target=0)] if len(film)==1 else [
                dict(wavelength_um=wave,angle_deg=angle,direction=direction,polarization=pol,metric=metric,target=target)
                for wave,angle,direction,pol,metric,target in [(.5,0,'inward','s','reflection',0),
                    (.65,30,'outward','p','transmission',1),(.55,25,'inward','p','reflection',0),
                    (.55,20,'outward','s','absorption',0)]]
            q=dict(kind='coating_optimization',surface=1,objectives=objectives,
                   variables=[dict(layer=i,minimum=.2,maximum=1.8) for i in range(1,len(film)+1)])
            if suffix=='REL':q.update(algorithm='OrthogonalDescent',cycles='Fixed_50_Cycles')
            r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
            assert r['summary']['native_terminal']['succeeded']
            assert r['summary']['constraints_satisfied'] and r['summary']['selected']=='optimized'
            assert r['summary']['optimized']['weighted_mean_squared_error']<=r['summary']['initial']['weighted_mean_squared_error']
            assert r['resources']['bench_closed'] and r['resources']['candidate_closed']
            assert r['restoration']['restored']
            for phase,states in [('before',layers['rows']),('after',r['layers_after'])]:
                stack=[(n,d*state['thickness_multiplier']) for (n,d),state in zip(film,states)]
                for sample in r[phase]['samples']:
                    for pol in ('s','p'):
                        ref=stack_rta(sample['wavelength_um'],sample['angle_deg'],sample['direction'],stack,pol)
                        for metric,wanted in ref.items():e.check(f'{suffix} {phase} {sample["index"]} {pol} {metric}',sample[metric][pol],wanted,atol=1e-8,rtol=1e-6)
            if len(film)==1:
                e.check('quarter wave multiplier '+suffix,r['layers_after'][0]['thickness_multiplier'],wave/(4*film[0][0]*film[0][1]),atol=1e-5,rtol=1e-5)
            page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=0,count=1))
            assert len(page['rows'])==1
            await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/(suffix+'.png')))))
            assert await e.call('get_surfaces',dict(start=0,count=3))==before
            assert await e.call('get_coating_layers',dict(request=dict(surface=1)))==layers
            assert await e.call('get_system_settings')==settings
            assert (await e.call('get_status'))['model_revision']==status['model_revision']
            await e.call('open_lens',dict(path=r['summary']['best_model']))
            replay=await e.call('get_coating_rta',dict(request=dict(surface=1,conditions=[{k:v for k,v in o.items() if k in ('wavelength_um','angle_deg','direction')} for o in objectives])))
            for a,c in zip(replay['samples'],r['direct_after']['samples']):
                for metric in ('reflection','transmission','absorption'):
                    for pol in ('s','p'):e.check('reload '+metric+pol,a[metric][pol],c[metric][pol])
            if suffix=='REL':
                assert r['direct_comparison_before']['state']=='native_reference_difference'
                assert r['native_mapping']['primary_wavelength_um']==.55
                rerun=await e.finish(await e.call('run_analysis',dict(request=q|dict(cycles='Fixed_1_Cycle',save_best=False))))
                for a,c in zip(rerun['before']['samples'],r['after']['samples']):
                    for metric in ('reflection','transmission','absorption'):
                        for pol in ('s','p'):e.check('physical reload '+metric+pol,a[metric][pol],c[metric][pol])
        # Preflight failure preserves the last loaded candidate and allows reuse.
        current=await e.call('get_surfaces',dict(start=0,count=3))
        current_layers=await e.call('get_coating_layers',dict(request=dict(surface=1)))
        current_settings=await e.call('get_system_settings')
        invalid=dict(q);invalid['objectives']=[dict(wavelength=99)]
        rejected=await e.call('run_analysis',dict(request=invalid),okay=False)
        assert rejected['error']['code']=='INDEX_OUT_OF_RANGE'
        assert await e.call('get_surfaces',dict(start=0,count=3))==current
        # A genuine cooperative cancellation, followed by a valid direct query.
        q['cycles']='Fixed_50_Cycles';q['save_best']=False
        t=await e.call('run_analysis',dict(request=q))
        await e.call('cancel_task',dict(task_id=t['task_id']))
        for _ in range(200):
            t=await e.call('get_task_status',dict(task_id=t['task_id']))
            if t['state'] in ('cancelled','failed','succeeded'):break
            await asyncio.sleep(.02)
        assert t['state']=='cancelled',t
        cancelled=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert cancelled['restoration']['restored']
        assert not cancelled['resources']['cleanup_errors']
        assert await e.call('get_surfaces',dict(start=0,count=3))==current
        assert await e.call('get_coating_layers',dict(request=dict(surface=1)))==current_layers
        assert await e.call('get_system_settings')==current_settings
        await e.call('get_coating_rta',dict(request=dict(surface=1)))
    try:
        asyncio.run(execute('coating_optimization_native',work))
    finally:resource.unlink(missing_ok=True)

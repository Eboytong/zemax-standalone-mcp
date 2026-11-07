"""The finite bandwidth and local Jones component matrices from the plan."""
import asyncio
import json
import math
import pytest
from support.native import execute
from support.nsc import setup,update,detector
from support.finite_reference import phasor_power_moments


@pytest.mark.zemax
@pytest.mark.parametrize('length',[.005,.01,.02])
def test_finite_bandwidth_matrix_native(length):
    async def work(e):
        import numpy as np
        n=10000;wave=.00055;band=wave*wave/length;records=[]
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=n,Power=1,ZCosine=1),
            sources=dict(RandomPolarization=False,Jx=1,Jy=0,CoherenceLength=length,InitialPhaseDeg=0)),
            dict(object=2,object_type='DetectorRectangle',material='ABSORB',z=.001,
                 data=dict(NumberXPixels=1,NumberYPixels=1,XHalfWidth=1,YHalfWidth=1,Polarization=0),
                 type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        for ratio in (0,.25,.5,1,1.5,2):
            distance=ratio*length;refs=[]
            for count in (32768,65536):
                wavelength=wave-band/2+(np.arange(count)+.5)*band/count
                phase=-2*np.pi*distance/wavelength
                refs.append((complex(np.exp(1j*phase).mean()),complex(np.exp(2j*phase).mean())))
            expected,variance=phasor_power_moments(*refs[-1],n)
            tolerance=6*math.sqrt(variance)+10*sum(abs(a-b)for a,b in zip(*refs))+1e-8
            await update(e,[dict(object=2,z=distance)])
            await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(use_polarization=True,random_seed=42,
                save_zrd=str(e.folder/f'ratio_{ratio}.zrd')))))
            data=await detector(e,2,kind='coherent',coherent_type='Power',width=1,height=1)
            actual=data['values'][0][0]
            records.append(dict(ratio=ratio,distance_mm=distance,expected=expected,actual=actual,atol=tolerance,
                                applicability='coincident source/detector: no finite propagation'if ratio==0 else'finite path',
                                passed=None if ratio==0 else actual is not None and abs(actual-expected)<=tolerance))
        await e.call('save_lens_as',dict(path=str(e.folder/'model.zos')))
        (e.folder/'bandwidth-reference.json').write_text(json.dumps(dict(coherence_length_mm=length,seed=42,rays=n,
            criterion='six finite-N standard errors plus quadrature refinement',rows=records),indent=2),encoding='utf-8')
        assert all(r['passed']for r in records if r['ratio']>0),records
    asyncio.run(execute('finite_bandwidth_'+str(length),work))


@pytest.mark.zemax
@pytest.mark.parametrize('angle',[0,45,90])
@pytest.mark.parametrize('tilt',[0,2])
def test_finite_jones_component_matrix_native(angle,tilt):
    async def work(e):
        await setup(e,3);a=math.radians(angle);t=math.radians(tilt)
        await update(e,[dict(object=i,object_type='SourceRay',x=-10*math.tan(t),
            data=dict(NumberOfAnalysisRays=1,Power=power,XCosine=math.sin(t),ZCosine=math.cos(t)),
            sources=dict(RandomPolarization=False,Jx=1 if i==1 else math.cos(a),Jy=0 if i==1 else math.sin(a),
                         CoherenceLength=0,InitialPhaseDeg=0))for i,power in ((1,.25),(2,.75))]+
            [dict(object=3,object_type='DetectorRectangle',z=10,material='ABSORB',
                data=dict(NumberXPixels=1,NumberYPixels=1,XHalfWidth=1,YHalfWidth=1),
                type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        records=[]
        vectors=[(math.cos(t),0,-math.sin(t)),(math.cos(a)*math.cos(t),math.sin(a),-math.cos(a)*math.sin(t))]
        for flag in (0,1,2,3):
            await update(e,[dict(object=3,data=dict(Polarization=flag))])
            amplitudes=[math.sqrt(p)*(1 if flag==0 else vectors[i][flag-1])for i,p in enumerate((.25,.75))]
            # Manual L14156/L14177: S_amp sums amplitudes of ALL incident
            # rays. The polarization flag selects the numerator's complex
            # component and incoherent power, not S_amp's incident-ray sum.
            incident_amplitude=sum(math.sqrt(p)for p in (.25,.75))
            denominator=incident_amplitude**2;power=sum(v*v for v in amplitudes)
            for phase in range(0,361,30):
                await update(e,[dict(object=2,sources=dict(InitialPhaseDeg=phase))])
                await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(use_polarization=True,random_seed=42))))
                actual=(await detector(e,3,kind='coherent',coherent_type='Power',width=1,height=1))['values'][0][0]
                if phase==0:
                    native_amplitude=(await detector(e,3,kind='coherent',coherent_type='Amplitude',width=1,height=1))['values'][0][0]
                    native_flux=(await detector(e,3,kind='flux',width=1,height=1))['values'][0][0]
                    # DetectorDataType.Amplitude is a native displayed result;
                    # it is not the unnormalized S_amp in manual L14177.
                    assert native_amplitude is not None and math.isfinite(native_amplitude) and native_amplitude>=0
                    e.check('selected component incoherent power W',native_flux,power)
                q=complex(math.cos(math.radians(phase)),-math.sin(math.radians(phase)))
                expected=power*abs(amplitudes[0]+amplitudes[1]*q)**2/denominator if denominator>1e-28 else 0.
                records.append(dict(flag=flag,phase_deg=phase,actual=actual,expected=expected,
                    native_amplitude=native_amplitude if phase==0 else None,
                    selected_incoherent_power_W=native_flux if phase==0 else None,
                    incident_ray_amplitude_sum=incident_amplitude,
                    passed=actual is not None and abs(actual-expected)<=1e-8+1e-7*abs(expected)))
        await e.call('save_lens_as',dict(path=str(e.folder/'model.zos')))
        (e.folder/'jones-components-reference.json').write_text(json.dumps(dict(polarization_angle_deg=angle,
            incidence_tilt_deg=tilt,local_vectors=vectors,pixels=[1,1],normalize_coherent_power=False,
            definition='manual L14156-14181: selected component field and incoherent power divided by ALL-incident ray amplitude sum squared',
            manual_lines=[14156,14177,14181,14233,14235],
            rows=records),indent=2),encoding='utf-8')
        assert all(r['passed']for r in records),[r for r in records if not r['passed']]
    asyncio.run(execute(f'finite_jones_A{angle}_T{tilt}',work))

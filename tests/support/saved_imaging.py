"""Numerical cross checks of acquired PSF/MTF/energy, with explicit method labels."""
import json
from pathlib import Path


def fft_frequency_projection(chief, field, wavelength):
    """Image-plane to chief-normal FFT frequency for a centered Y-field fixture.

    The actual primary wavelength is used for a polychromatic FFT PSF.
    General decentered/tilted planes require a two-dimensional mapping.
    """
    import math
    if chief.get('field')!=field or chief.get('wavelength')!=wavelength:
        raise ValueError('Chief ray selection differs from saved analysis')
    data=chief['result'];row=data['rows'][0];settings=data['system_settings']
    expected=wavelength or next(w['number']for w in settings['wavelengths']if w['primary'])
    if row['input']['wavelength']!=expected:
        raise ValueError('FFT projection requires the actual selected/primary wavelength')
    if row['error_code'] or row['vignette_code']:
        raise ValueError('Invalid chief ray for frequency projection')
    l,m,n=row['direction'];normal=row['surface_normal']
    if not all(math.isfinite(v)for v in (l,m,n)) or abs(l)>1e-10 or abs(abs(normal[2])-1)>1e-10:
        raise ValueError('Projection limited to the centered Y-field, flat untilted image fixture')
    if abs(l*l+m*m+n*n-1)>1e-10 or n<=0:
        raise ValueError('Invalid chief direction')
    return dict(tangential=1/n,sagittal=1.,chief_cosine=n,
                definition='f_beam_t = f_image_t / cos(chief,image_normal)',
                wavelength_number=expected,source=chief.get('source_file'))


def validate_folder(folder, additional_folders=()):
    import numpy as np
    from .finite_reference import normalized_otf
    analyses={};sources=[]
    paths = [p for base in (folder, *additional_folders) for p in Path(base).rglob('*.json')]
    for path in paths:
        if path.name in ('calls.json','checks.json','imaging-reference.json','saved-cross-reference.json'):continue
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict)or not data.get('task'):continue
        task=data['task'];settings=task.get('settings',{})
        if task.get('state')!='succeeded':continue
        kind=settings.get('kind',task.get('kind'));q=settings.get('requested',settings)
        if kind not in ('huygens_psf','huygens_mtf','fft_psf','fft_mtf','diffraction_encircled_energy'):continue
        key=(kind,q.get('sampling'));analyses[key]=data;sources.append(str(path))
    selections={(d['task']['settings'].get('requested',d['task']['settings']).get('field'),
                 d['task']['settings'].get('requested',d['task']['settings']).get('wavelength'))for d in analyses.values()}
    if len(selections)>1:raise ValueError('Saved results use different fields or wavelengths')
    records=[];missing=[];projection=None;chief=None
    for base in (folder,*additional_folders):
        path=Path(base)/'chief-reference.json'
        if path.is_file():
            chief=json.loads(path.read_text(encoding='utf-8'));chief['source_file']=str(path)
    if chief is not None:projection=fft_frequency_projection(chief,*next(iter(selections)))
    def record(check,actual,expected,tolerance,**context):
        records.append(dict(check=check,actual=float(actual),expected=float(expected),atol=tolerance,
            passed=bool(np.isfinite(actual)and np.isfinite(expected)and abs(actual-expected)<=tolerance),**context))
    for family in ('fft','huygens'):
        levels=[];window=None
        for n in (256,512,1024):
            sampling=f'S_{n}x{n}';psf=analyses.get((family+'_psf',sampling));mtf=analyses.get((family+'_mtf',sampling))
            if psf is None or mtf is None:
                if n<=512:missing.append(dict(family=family,sampling=n))
                continue
            g=psf['grids'][0];values=np.asarray(g['values'],dtype=float)
            current_window=(g['nx'],g['ny'],g['dx'],g['dy'])
            if window is not None and current_window!=window:
                missing.append(dict(family=family,sampling=n,reason='PSF output sampling/window differs across pupil refinement',
                                    reference_window=window,actual_window=current_window))
            window=current_window
            if not np.isfinite(values).all()or values.sum()<=0:raise ValueError('Invalid PSF samples')
            fx,fy,otf=normalized_otf(values,g['dx']/1000,g['dy']/1000)
            level={};cy,cx=values.shape[0]//2,values.shape[1]//2
            for series in mtf['series']:
                for j,label in enumerate(series['labels']):
                    if label not in ('Tangential','Sagittal','子午','弧矢'):raise ValueError('Unknown MTF label: '+label)
                    tangential=label in ('Tangential','子午');axis=fy if tangential else fx
                    line=abs(otf[:,cx])if tangential else abs(otf[cy,:])
                    for frequency in (10,25,50):
                        if not series['x'][0]<=frequency<=series['x'][-1]:raise ValueError('MTF frequency outside data')
                        actual=float(np.interp(frequency,series['x'],[v[j]for v in series['y']]))
                        reference_frequency=frequency*(projection['tangential']if tangential else projection['sagittal'])if family=='fft'and projection else frequency
                        expected=float(np.interp(reference_frequency,axis,line))
                        record('PSF Fourier MTF',actual,expected,.02,family=family,sampling=n,label=label,frequency=frequency,
                               reference_frequency=reference_frequency)
                        level[(label,frequency)]=(actual,expected)
            if family=='fft':
                ee=analyses.get(('diffraction_encircled_energy',sampling))
                if ee is None:missing.append(dict(kind='FFT energy',sampling=n))
                else:
                    if ee['task']['settings']['native']['UseHuygensPSF']is not False:raise ValueError('Energy method is not FFT')
                    x=g['min_x']+np.arange(g['nx'])*g['dx'];y=g['min_y']+np.arange(g['ny'])*g['dy']
                    actual_series=[s for s in ee['series']if s['description'].strip().casefold()not in('衍射极限','diffraction limit')]
                    if len(actual_series)!=1:raise ValueError('Exactly one actual-field energy series required')
                    series=actual_series[0]
                    for radius in (10,20):
                        expected=float(values[x[None,:]**2+y[:,None]**2<=radius*radius].sum()/values.sum())
                        actual=float(np.interp(radius,series['x'],[v[0]for v in series['y']]))
                        record('FFT PSF disk energy',actual,expected,.025,family=family,sampling=n,radius_um=radius,
                            normalization='finite PSF window; absolute Parseval reference separate')
                        level[('energy',radius)]=(actual,expected)
            levels.append((n,level))
        if len(levels)>=2:
            (coarse,a),(fine,b)=levels[-2:]
            for key in a.keys()&b.keys():
                for j,quantity in enumerate(('native','reference')):
                    record('sampling refinement',b[key][j],a[key][j],.005,family=family,sampling=fine,quantity=quantity,key=str(key))
        else:missing.append(dict(family=family,reason='two complete sampling levels required'))
    finest={f:max((r['sampling']for r in records if r.get('family')==f),default=0)for f in ('fft','huygens')}
    deciding=[r for r in records if r['sampling']==finest[r['family']]]
    status='incomplete'if missing else'numeric_pass'if deciding and all(r['passed']for r in deciding)else'numeric_failure'
    return dict(status=status,scope='method-matched transforms of acquired data; independent lens model not implied',
        sources=sources,missing=missing,projection=projection,finest_sampling=finest,checks=records,
        failed_deciding_checks=[r for r in deciding if not r['passed']])

"""Units, source conditions and native cumulative-bin coordinates."""
import math

from .errors import ZemaxError


def describe_extended_source(data,request,system_settings):
    kind=request['data_type']
    distribution=kind in {'X_Distrib','Y_Distrib'}
    if not data.get('series'):
        raise ZemaxError('NO_RESULT_DATA','Extended source energy returned no native curves.')
    for series in data['series']:
        if len(series['x'])!=len(series['y']) or any(len(row)!=1 for row in series['y']):
            raise ZemaxError('INVALID_RESULT_DATA','Extended source energy requires one value per native position.')
        axis_label=dict(Encircled='Native reported radial distance',X_Only='Native reported X half-width',
                        Y_Only='Native reported Y half-width',Ensquared='Native reported square half-width',
                        X_Distrib='Image X',Y_Distrib='Image Y')[kind]
        series.update(native_labels=list(series['labels']),native_x_label=series.get('x_label'),
                      labels=[kind],x_label=axis_label,
                      x_unit='micrometers',value_units=['relative distribution' if distribution else 'fraction'],
                      value_quantity='energy distribution' if distribution else 'enclosed energy fraction',
                      labels_source='adopted native Type and original native description',
                      reference=request['reference'],native_x=list(series['x']),
                      normalization='native peak-normalized distribution; not per-bin probability' if distribution else 'fraction of native traced energy')
        if not distribution and len(series['x'])==396:
            x=series['x'];step=x[1]-x[0]
            if step>0 and all(math.isclose(b-a,step,rel_tol=1e-9,abs_tol=1e-12) for a,b in zip(x,x[1:])):
                width=4*step
                series['native_binning']=dict(base_sample_count=100,display_subdivisions=4,
                    interval_um=width,
                    coordinate_definition='native reported distance retained; cumulative bin upper edge trails reported position by one base interval',
                    enclosure_radius_um=[max(0,v-width) for v in x],
                    enclosure_radius_source='calculated sampling interpretation validated with controlled 2024 R2 reference models',
                    evidence='uniform ObjectHeight square at 16/20/40um maxima, point limit and circular-pupil diffraction; numerical reference uses native bin edges')
    data['extended_source_conditions']=dict(
        field_size=request['field_size'],field_size_definition='full square input-file width',
        field_size_unit='degrees' if system_settings.get('field_type')=='Angle' else system_settings.get('lens_units'),
        maximum_distance_unit='micrometers',rotation_unit='degrees',
        requested_rays_x1000=request['rays_x1000'],actual_ray_count=None,
        ray_count_definition='approximate request; native distributes rays across image pixels and wavelength weights',
        multiply_by_diffraction_limit=request['multiply_by_diffraction_limit'],
        diffraction_approximation='native unobscured circular-pupil approximation',
        input_resource=request['image_name'])
    return data

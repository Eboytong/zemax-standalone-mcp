"""Explicit condition mapping for the installed ISTARMaterials query methods."""
import math
from .errors import ZemaxError


def evaluate_material(backend, catalog, material, samples):
    try: owner = backend.system.STARSubsystem.Materials
    except Exception as exc:
        raise ZemaxError('STAR_MATERIAL_ERROR',str(exc),native_method='STARSubsystem.Materials',
                         catalog=catalog,material=material,native_type=type(exc).__name__) from exc
    rows = []
    for number, sample in enumerate(samples):
        values = (sample.wavelength_um, sample.environment_pressure_atm, sample.environment_temperature_c,
                  sample.material_pressure_atm, sample.material_temperature_c)
        row = dict(sample=number, **sample.model_dump())
        for method, key, args in [('GetRefractiveIndex','refractive_index', values),
                                  ('GetDNDT','dn_dt', (*values,sample.delta_temperature_c))]:
            try: value = float(getattr(owner, method)(catalog,material,*args))
            except Exception as exc:
                raise ZemaxError('STAR_MATERIAL_ERROR',str(exc),native_method=method,
                                 sample=number,catalog=catalog,material=material,
                                 conditions=sample.model_dump(),native_type=type(exc).__name__) from exc
            if not math.isfinite(value) or (key == 'refractive_index' and value <= 0):
                raise ZemaxError('INVALID_RESULT_DATA','STAR material query returned an invalid value.',
                                 native_method=method,sample=number,value=str(value),conditions=sample.model_dump())
            row[key] = value
        rows.append(row)
    return dict(rows=rows,source='ISTARMaterials.GetRefractiveIndex/GetDNDT',
                units=dict(wavelength='micrometers',pressure='atmospheres',temperature='Celsius',
                           delta_temperature='Celsius interval',refractive_index='dimensionless',dn_dt='per Celsius interval'),
                reference_definition='Native environment/material pressure and temperature conditions retained; absolute/relative index reference and dn/dT numeric acceptance pending')

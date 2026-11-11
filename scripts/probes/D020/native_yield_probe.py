"""Read formal merit column identities, wizard-generated grouping and TDE methods."""
import json
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

b=Backend(Config.from_env());out=Path('.local/evidence/development/D020');out.mkdir(parents=True,exist_ok=True)
def call(name,args=None):
    r=b.dispatch(name,args or {});assert r['ok'],r
    return r['data']
try:
    call('connect');call('new_system')
    call('update_system_settings',dict(aperture_value=5,wavelengths=[dict(wavelength_um=.55)]))
    call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',parameters={1:50},thickness=50,semi_diameter=5,replace_solves=True)]))
    wizard=unwrap(b.system.MFE.SEQOptimizationWizard2)
    wizard.CommonSettings.ResetSettings();wizard.Criterion=b.native.enum(wizard.GetType().GetProperty('Criterion').PropertyType,'Wavefront')
    wizard.OptimizeForBestNominalPerformance=False;wizard.OptimizeForManufacturingYield=True;wizard.ManufacturingYieldWeight=1;wizard.UseGaussianQuadrature=True;wizard.Rings=2;wizard.AssumeAxialSymmetry=False;wizard.CommonSettings.Apply()
    mfe=b.system.MFE;rows=[]
    for i in range(1,int(mfe.NumberOfOperands)+1):
        row=mfe.GetOperandAt(i)
        rows.append(dict(index=i,type=str(row.Type),target=float(row.Target),weight=float(row.Weight),cells=[dict(column=j,header=str(row.GetCellAt(j).Header),active=bool(row.GetCellAt(j).IsActive),value=b._cell_value(row.GetCellAt(j))) for j in range(2,10)]))
    data=dict(context=b.context(),rows=rows,tde_methods=[str(x) for x in b.system.TDE.GetType().GetMethods() if any(k in str(x) for k in ['Save','Load'])],yield_available=bool(wizard.IsHighManufacturingYieldAvailable))
    for code in ['OPDC','OPDM','OPDX']:
        row=mfe.AddOperand();row.ChangeType(b.native.enum(b.native.api.Editors.MFE.MeritOperandType,code))
        data[code]=[dict(column=j,header=str(row.GetCellAt(j).Header),active=bool(row.GetCellAt(j).IsActive)) for j in range(2,10)]
    (out/'native-yield-columns.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False))
finally:
    print(call('disconnect'))

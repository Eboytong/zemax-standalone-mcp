"""Prepare native FEA inputs before opening a separate MCP session."""
import json
from itertools import product
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from tests.support.paths import fixture_dir


def prepared_star_lens(data_kind=None, fitted=False):
    folder=fixture_dir('2026r1_star_preloaded_'+(data_kind or 'combined'))
    backend=Backend(Config(Config.from_env().install_dir,folder))
    record=dict(preparation='Native API import; MCP import is tested independently',branches={})
    def call(name,arguments=None):
        result=backend.dispatch(name,arguments or {})
        assert result['ok'],result
        return result['data']
    try:
        call('connect');call('new_system');call('insert_surfaces',dict(at=1))
        call('update_system_settings',dict(aperture_value=2,
            material_catalogs=['SCHOTT'],wavelengths=[dict(wavelength_um=.55)]))
        call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',thickness=20,
            semi_diameter=1,replace_solves=True)]))
        for kind in ([data_kind] if data_kind else ['deformation','temperature','direct_index']):
            if kind=='deformation':
                values=[[x,y,0.,0.,0.,.01] for x,y in product([-1.,0.,1.],repeat=2)]
                branch=backend.system.LDE.GetSurfaceAt(1).STARData.Deformations
                method='ImportDeformations'
            else:
                values=[[x,y,z,21. if kind=='temperature' else 1.5]
                    for x,y,z in product([-1.,0.,1.],[-1.,0.,1.],[0.,10.,20.])]
                branch=getattr(backend.system.LDE.GetSurfaceAt(1).STARData,
                    'Temperatures' if kind=='temperature' else 'DirectIndex')
                method='ImportTemperatures' if kind=='temperature' else 'ImportDirectIndex'
            source=folder/(kind+'.txt')
            source.write_text('\n'.join(' '.join(map(str,row)) for row in values)+'\n',encoding='utf-8')
            branch.SetDataIsLocal();getattr(branch.FEAData,method)(str(source))
            assert int(branch.FEAData.NumberOfDataPoints)==len(values)
            record['branches'][kind]=dict(points=int(branch.FEAData.NumberOfDataPoints),
                filename=str(branch.FEAData.Filename),fitted=fitted)
            if fitted:
                branch.Fits.Refit()
                getattr(branch.Fits,{'deformation':'ApplyDeformations',
                    'temperature':'ApplyTemperatures','direct_index':'ApplyIndex'}[kind])()
        lens=folder/'preloaded.zos'
        call('save_lens_as',dict(path=str(lens)))
        return lens
    finally:
        result=backend.dispatch('disconnect',{})
        record['disconnect']=result['ok']
        (folder/'preparation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


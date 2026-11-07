from pathlib import Path
import pytest
from zemax_mcp.config import PROJECT_ROOT
@pytest.mark.zemax
@pytest.mark.parametrize('fmt',['ASCII','Binary','CompressedBinary'])
def test_point_cloud_live(fmt):
    import asyncio
    from tests.support.native import execute
    async def work(e):
        await e.model()
        before=await e.call('get_surfaces')
        r=await e.call('export_point_cloud',{'request':dict(surface=1,path=str(e.folder/'surface.pcd'),
                       x_sampling=7,y_sampling=5,format=fmt)})
        assert r['copy_closed'] and Path(r['path']).is_file()
        assert r['header']['points']>0
        if fmt=='ASCII':
            lines=Path(r['path']).read_text(encoding='ascii').splitlines()
            start=next(i for i,line in enumerate(lines) if line.strip().startswith('DATA '))+1
            fields=r['header']['fields']
            points=[dict(zip(fields,map(float,line.split()))) for line in lines[start:] if line.strip()]
            assert len(points)==r['header']['points']
            for point in points:
                import math
                if point['x']**2+point['y']**2>25:
                    assert math.isnan(point['z']);continue
                for name in ['z','normal_x','normal_y']:
                    e.check('plane '+name,point[name],0,atol=1e-8,rtol=1e-7)
                e.check('plane normal magnitude',abs(point['normal_z']),1,atol=1e-8,rtol=1e-7)
        assert await e.call('get_surfaces')==before
    asyncio.run(execute('point_cloud_'+fmt,work))


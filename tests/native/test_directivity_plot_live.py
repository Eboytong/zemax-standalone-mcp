import asyncio
import json
import math
from pathlib import Path

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_directivity_plot_stdio():
    async def work(e):
        await e.call("open_lens", dict(path=str(Path.home() / "Documents/Zemax/Samples/Non-sequential/Colorimetry/Example 1  Two-color mixing gives white.zos")))
        baseline=await e.call('get_system_settings')
        objects=await e.call('get_nsc_objects',dict(request={}))
        result = await e.finish(await e.call("run_analysis", dict(request=dict(kind="directivity_plot"))))
        assert result["computation_method"] == "native_DirectivityPlot_text"
        assert result["ies_file"].lower() == "sample.ies"
        assert result["peak_intensity_candela"] == pytest.approx(18)
        assert result["total_luminous_flux_lumens"] == pytest.approx(112.81, abs=0.001)
        assert len(result["series"]) == 1
        curve = result["series"][0]
        assert len(curve["x"]) == 37
        for angle, value in [(-180, 0), (-90, .5), (0, 1), (90, .5), (180, 0)]:
            index = curve["x"].index(angle)
            e.check("native directivity value", curve["y"][index][0], value, atol=1e-12, rtol=0)
        assert any(a["kind"] == "native_text" for a in result["artifacts"])
        source=Path.home()/'Documents/Zemax/Objects/Sources/IESNA/sample.ies'
        data=list(map(float,source.read_text().split('TILT=NONE',1)[1].replace(',',' ').split()))
        nv,nh=int(data[3]),int(data[4])
        assert (nv,nh,int(data[5]))==(19,19,1)
        vertical=data[13:13+nv]
        intensities=data[13+nv+nh:]
        assert len(intensities)==nv*nh
        scans=[intensities[i*nv:(i+1)*nv] for i in range(nh)]
        assert all(scan==scans[0] for scan in scans)
        values=[v*data[2] for v in scans[0]]
        for angle,y in zip(curve['x'],curve['y']):
            expected=values[vertical.index(abs(angle))]/max(values)
            e.check('IES native normalized angle '+str(angle),y[0],expected,atol=5.1e-5,rtol=0)
        discrete_flux=2*math.pi*sum((values[i-1]*math.sin(math.radians(vertical[i-1]))+
            values[i]*math.sin(math.radians(vertical[i])))/2*math.radians(vertical[i]-vertical[i-1])
            for i in range(1,nv))
        e.check('IES discrete angular flux',result['total_luminous_flux_lumens'],discrete_flux,atol=.0051,rtol=0)
        (e.folder/'ies-reference.json').write_text(json.dumps(dict(source=str(source),
            vertical=vertical,intensity_cd=values,native_flux=result['total_luminous_flux_lumens'],
            trapezoidal_flux=discrete_flux,linear_triangle_exact_flux=36*math.pi),indent=2),encoding='utf-8')
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=3,count=2))
        assert page['total']==37 and len(page['rows'])==2
        status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
        assert status['state']=='succeeded' and status['close_attempted']
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_nsc_objects',dict(request={}))==objects
        image=e.folder/'directivity.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(image))))
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    asyncio.run(execute("directivity_plot", work))

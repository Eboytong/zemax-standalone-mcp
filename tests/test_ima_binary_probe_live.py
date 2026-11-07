"""Binary IMA plane and BIM source-display identity experiments."""
import asyncio,json,struct,uuid
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
def test_binary_source_planes():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        resource=await e.call('get_system_resources',dict(request=dict(kind='image_simulation_files')))
        root=Path(resource['directory']);token=uuid.uuid4().hex
        planes=[]
        for j in range(3):
            plane=bytearray(49);plane[8+j*8]=[255,128,64][j];plane[15+j*8]=[64,32,16][j];planes.append(bytes(plane))
        ima=root/('ima451_'+token+'.IMA');bim=root/('bim451_'+token+'.BIM')
        ima.write_bytes(struct.pack('<hhh',0,7,3)+b''.join(planes))
        pixels=[0.]*49;pixels[8]=1.;pixels[16]=.5;pixels[33]=.25
        bim.write_bytes(struct.pack('<ii',7,7)+struct.pack('<49d',*pixels))
        try:
            for path,wave in [(ima,'RGB'),(bim,1)]:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='image_simulation',input_file=path.name,wavelength=wave,
                    show_as='SourceBitmap',oversampling='None',guard_band='None',aberrations='None',psf_x_points=3,psf_y_points=3))))
                (e.folder/(path.suffix[1:]+str(wave)+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                assert result['task']['settings']['native']['InputFile']==path.name
                print(path.suffix,wave,[(g['channel'],[(iy,ix,v) for iy,row in enumerate(g['values']) for ix,v in enumerate(row) if v]) for g in result['grids']],flush=True)
        finally:
            ima.unlink(missing_ok=True);bim.unlink(missing_ok=True)
    asyncio.run(execute('ima452_normalization',work))

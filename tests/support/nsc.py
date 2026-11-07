"""Controlled nonsequential setup, trace and detector calls."""

async def setup(e, count):
    await e.call("new_system", dict(mode="NonSequential"))
    if count > 1:
        await e.call("insert_nsc_objects", dict(request=dict(at=1,count=count-1)))
    catalogs = (await e.call("get_system_settings"))["material_catalogs"]
    if "SCHOTT" not in catalogs:catalogs.append("SCHOTT")
    await e.call("update_system_settings", dict(settings=dict(
        material_catalogs=catalogs, wavelengths=[dict(wavelength_um=.55)])))


async def update(e, changes):
    return await e.call("update_nsc_objects", dict(request=dict(changes=[dict(c,replace_solves=True)for c in changes])))


async def trace(e, name="rays", max_segments=10000, **options):
    zrd=e.folder/(name+".zrd")
    r=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),random_seed=42,**options))))
    data=await e.finish(await e.call("read_zrd",dict(request=dict(path=str(zrd),max_segments=max_segments))))
    return r,data["rows"]


async def detector(e, index, **args):
    return await e.call("get_detector_data",dict(request=dict(detector=index,**args)))


"""Hologram2 public state guards and enabled Variable persistence, real stdio."""
import asyncio
from pathlib import Path

import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize("entry", ["update_surfaces", "set_variables"])
@pytest.mark.parametrize("extension", ["zos", "zmx"])
def test_hologram2_public_persistence_native(entry, extension):
    async def work(e):
        source = Path.home()/"Documents/Zemax/Samples/Sequential/Diffractive components/Reflection hologram.zmx"
        await e.call("open_lens", dict(path=str(source)))
        async def surface():
            return (await e.call("get_surfaces", dict(start=1, count=1)))["surfaces"][0]
        async def mode(variable, cell="parameter_13", okay=True):
            args = dict(variables=[dict(surface=1, cell=cell, variable=variable)]) if entry=="set_variables" else dict(changes=[
                dict(surface=1, solves={cell:dict(mode="variable" if variable else "fixed")})])
            return await e.call(entry, args, okay=okay)
        async def reload(label):
            path = e.folder/f"{label}.{extension}"
            await e.call("save_lens_as", dict(path=str(path)))
            await e.call("open_lens", dict(path=str(path)))
            return await surface()
        for value in (0, 1):
            await e.call("update_surfaces", dict(changes=[dict(surface=1, parameters={13:value},
                solves={"parameter_13":dict(mode="fixed")}, replace_solves=True)]))
            await mode(False)
            state = await reload(f"fixed_{value}")
            e.check(f"fixed value {value}", state["cells"]["parameter_13"]["value"], value)
            assert state["cells"]["parameter_13"]["solve"]["type"]=="Fixed"
            info = state["cells"]["parameter_13"]
            assert "Variable" in info["available_solves"]
            assert info["solve_persistence"]["variable_persists"] == (value==1)
            before = e.calls[-1]["response"]["context"]
            result = await mode(True, okay=value==1)
            if value==0:
                assert result["error"]["code"]=="UNSUPPORTED_SOLVE",result
                assert result["context"]["model_revision"]==before["model_revision"]
                assert result["context"]["checkpoint"]==before["checkpoint"]
                assert not result["error"]["details"]["partial_changes_possible"]
            else:
                state = await reload("enabled_variable")
                assert state["cells"]["parameter_13"]["solve"]["type"]=="Variable"
                e.check("enabled value reload", state["cells"]["parameter_13"]["value"], 1)
                before = e.calls[-1]["response"]["context"]
                result = await e.call("update_surfaces", dict(changes=[dict(surface=1,parameters={13:0})]), okay=False)
                assert result["error"]["code"]=="UNSUPPORTED_SOLVE"
                assert result["context"]["model_revision"]==before["model_revision"]
                assert (await surface())["cells"]["parameter_13"]["value"]==1
        await e.call("update_surfaces",dict(changes=[dict(surface=1,parameters={13:0},solves={"parameter_13":dict(mode="fixed")})]))
        state = await reload("disabled_fixed")
        assert state["cells"]["parameter_13"]["solve"]["type"]=="Fixed"
        e.check("disabled value reload", state["cells"]["parameter_13"]["value"],0)
        await mode(True, "parameter_1")
        state = await reload("continuous_variable")
        assert state["cells"]["parameter_1"]["solve"]["type"]=="Variable"
        # Verify neither public batch modifies an earlier valid item on rejection.
        initial_comment = state["comment"]
        args = dict(variables=[dict(surface=1,cell="parameter_1",variable=False),dict(surface=1,cell="parameter_13")]) if entry=="set_variables" else dict(changes=[
            dict(surface=0,comment="must not write"),dict(surface=1,solves={"parameter_13":dict(mode="variable")})])
        before = e.calls[-1]["response"]["context"]
        result = await e.call(entry,args,okay=False)
        assert result["error"]["code"]=="UNSUPPORTED_SOLVE"
        assert result["context"]["model_revision"]==before["model_revision"]
        assert (await surface())["cells"]["parameter_1"]["solve"]["type"]=="Variable"
        # A rejected request leaves the model usable for an independent valid write.
        await e.call("update_surfaces",dict(changes=[dict(surface=1,comment=initial_comment+" verified")]))
    asyncio.run(execute(f"hologram2_{entry}_{extension}",work))


@pytest.mark.zemax
def test_hologram2_type_change_native():
    async def work(e):
        await e.model()
        bad = dict(surface=1,surface_type="Hologram2",replace_solves=True,solves={"parameter_13":dict(mode="variable")})
        before = e.calls[-1]["response"]["context"]
        result = await e.call("update_surfaces",dict(changes=[bad]),okay=False)
        assert result["error"]["code"]=="UNSUPPORTED_SOLVE"
        assert result["context"]["model_revision"]==before["model_revision"]
        state = (await e.call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]
        assert state["surface_type"]=="Standard"
        await e.call("update_surfaces",dict(changes=[dict(**bad,parameters={13:1})]))
        path=e.folder/"type_enabled.zos"
        await e.call("save_lens_as",dict(path=str(path)))
        await e.call("open_lens",dict(path=str(path)))
        state=(await e.call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]
        assert state["surface_type"]=="Hologram2"
        assert state["cells"]["parameter_13"]["solve"]["type"]=="Variable"
        e.check("type change value",state["cells"]["parameter_13"]["value"],1)
    asyncio.run(execute("hologram2_type_change",work))

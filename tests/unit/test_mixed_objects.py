from types import SimpleNamespace as N
import pytest
from zemax_mcp.nonsequential import NonSequentialMixin,object_scope
from zemax_mcp.errors import ZemaxError
from zemax_mcp.nsc_models import ObjectRange


class Editor:
    ActiveSurface=2
    def SetActiveSurface(self,index):self.ActiveSurface=index;return True


class Fixture(NonSequentialMixin):
    def __init__(self):
        self.system=N(Mode='Sequential',NCE=Editor(),LDE=N(NumberOfSurfaces=6))
        self.requires_reconnect=False;self.last_checkpoint='checkpoint.zos';self.revision=0
    def _row(self,index):return N(Type='NonSequential'if index in (2,4)else'Standard')
    @object_scope
    def operation(self,req):
        self._require_nsc();self.revision+=1
        if req.start==99:raise ZemaxError('SETTING_REJECTED','rejected')
        return dict(selected=self.system.NCE.ActiveSurface)


def test_mixed_group_scope_and_restoration():
    b=Fixture();r=b.operation(ObjectRange(nsc_surface=4))
    assert r==dict(selected=4,nsc_surface=4)and b.system.NCE.ActiveSurface==2
    assert b._active_nsc_surface is None
    with pytest.raises(ZemaxError,match='纯非序列'):b._require_nsc()


@pytest.mark.parametrize('surface,code',[(None,'UNSUPPORTED_MODE'),(3,'INVALID_NSC_GROUP')])
def test_invalid_group_before_mutation(surface,code):
    b=Fixture()
    with pytest.raises(ZemaxError)as err:b.operation(ObjectRange(nsc_surface=surface))
    assert err.value.code==code and b.revision==0 and b.system.NCE.ActiveSurface==2


def test_failure_restores_group_and_preserves_error():
    b=Fixture()
    with pytest.raises(ZemaxError)as err:b.operation(ObjectRange(nsc_surface=4,start=99))
    assert err.value.code=='SETTING_REJECTED'and b.system.NCE.ActiveSurface==2


def test_group_restoration_failure_requires_reconnect():
    b=Fixture()
    def select(index):
        if index==2:return False
        b.system.NCE.ActiveSurface=index;return True
    b.system.NCE.SetActiveSurface=select
    with pytest.raises(ZemaxError)as err:b.operation(ObjectRange(nsc_surface=4))
    assert err.value.code=='RESTORE_FAILED'and b.requires_reconnect and b._active_nsc_surface is None


def test_group_selection_rejection_does_not_modify_model():
    b=Fixture();b.system.NCE.SetActiveSurface=lambda _:False
    with pytest.raises(ZemaxError)as err:b.operation(ObjectRange(nsc_surface=4))
    assert err.value.code=='NSC_GROUP_SELECTION_FAILED'and b.revision==0


@pytest.mark.parametrize('status,adopted',[(False,True),(True,False)])
def test_explicit_group_selector_checks_return_and_actual(status,adopted):
    b=Fixture()
    def select(index):
        if adopted:b.system.NCE.ActiveSurface=index
        return status
    b.system.NCE.SetActiveSurface=select
    with pytest.raises(ZemaxError):b.operation(ObjectRange(nsc_surface=4))
    assert b.revision==0


def test_pure_nsc_selector_rejected():
    b=Fixture();b.system.Mode='NonSequential'
    with pytest.raises(ZemaxError)as err:b.operation(ObjectRange(nsc_surface=2))
    assert err.value.code=='INVALID_ARGUMENT'and b.revision==0

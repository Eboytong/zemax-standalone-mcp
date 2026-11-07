"""Primitive reflection must read the implementation exposed by pythonnet."""
from types import SimpleNamespace as N
from zemax_mcp.analyses import scalar_settings


def properties(*names):
    return N(GetProperties=lambda:[N(Name=n,GetIndexParameters=lambda:N(Length=0),PropertyType=N(IsPrimitive=True,IsEnum=False)) for n in names])


def test_interface_projection_reads_implementation_properties():
    implementation=N(GetType=lambda:properties('IsCancelling'),IsCancelling=False)
    interface=N(__implementation__=implementation)
    assert scalar_settings(interface)=={'IsCancelling':False}


def test_unavailable_implementation_property_remains_reported():
    implementation=N(GetType=lambda:properties('MissingSetting'))
    result=scalar_settings(N(__implementation__=implementation))
    assert 'MissingSetting' in result['unavailable_fields']

"""Sequential (LDE) scatter capabilities derived from the native reflection dump.

Every fact here is copied from
``verification/development/BASE-01/probe/api-interfaces.json`` and is re-checked by
``tests/unit/test_scatter_capabilities.py`` so a version change cannot silently drift
away from the adapter. No capability is invented: a member that the dump does not
show is reported as absent rather than assumed.

Notable findings encoded below:

* ``ISurfaceScatteringBSDF``/``Gaussian``/``Lambertian`` expose ``ScatterFraction``;
  ``ABg``/``ABgFile``/``User``/``ISScatterCatalog`` do not.
* ``ISurfaceApertureFloating`` has no properties and no methods in the dump, so the
  floating aperture is **not** a scatter host in this build; the reflection only shows
  an empty interface.
* Several analyses expose a ``ScatterRays``/``ScatterNSCRays`` toggle, which is an
  analysis-host option and not a scatter model definition.
"""
from .errors import ZemaxError

DUMP_PATH = 'verification/development/BASE-01/probe/api-interfaces.json'

# ZOSAPI.Editors.LDE.SurfaceScatteringTypes
LDE_TYPES = ('None', 'Lambertian', 'Gaussian', 'ABg', 'ABgFile', 'BSDF', 'User', 'ISScatterCatalog')

TYPE_INTERFACE = {
    'None': 'ZOSAPI.Editors.LDE.ISurfaceScatteringNone',
    'Lambertian': 'ZOSAPI.Editors.LDE.ISurfaceScatteringLambertian',
    'Gaussian': 'ZOSAPI.Editors.LDE.ISurfaceScatteringGaussian',
    'ABg': 'ZOSAPI.Editors.LDE.ISurfaceScatteringABg',
    'ABgFile': 'ZOSAPI.Editors.LDE.ISurfaceScatteringABgFile',
    'BSDF': 'ZOSAPI.Editors.LDE.ISurfaceScatteringBSDF',
    'User': 'ZOSAPI.Editors.LDE.ISurfaceScatteringUser',
    'ISScatterCatalog': 'ZOSAPI.Editors.LDE.ISurfaceScatteringCatalog',
}

# Enumeration method per type; 'None' has no resource list.
RESOURCE_QUERY = {
    'ABg': 'GetAvailableABgNames',
    'ABgFile': 'GetAvailableFileNames',
    'BSDF': 'GetAvailableFileNames',
    'User': 'GetAvailableDLLNames',
    'ISScatterCatalog': 'GetAvailableFiles',
}

# Types whose settings object carries ScatterFraction (dump: properties list).
SCATTER_FRACTION_HOSTS = ('Lambertian', 'Gaussian', 'BSDF')
SCATTER_FRACTION_ABSENT = ('None', 'ABg', 'ABgFile', 'User', 'ISScatterCatalog')

# Placeholder values a native resource selector has actually been observed to return.
# Kept deliberately narrow, because rejecting a name that is legally a resource would
# break valid ABg/catalog selections:
#   ''     - empty string from a selector with no entry
#   '无'    - observed literal in development/evidence/ED-01/bsdf-resource-selector-probe20261108.md
#   'none' - .NET null stringified by the adapter (str(None))
# Nothing else is treated as a placeholder without native or documented evidence.
PLACEHOLDERS = frozenset({'', '无', 'none'})

# Consumers of this module: src/zemax_mcp/scattering_pages.py (resource_names and
# set_scattering) and the reflection-sync tests. Functions here exist to serve those call
# sites; a helper without a caller is removed rather than kept as a mirror of the dump.

# Analysis-side toggles that merely enable scattered rays in an existing analysis.
ANALYSIS_SCATTER_TOGGLES = {
    'ZOSAPI.Analysis.Settings.Spot.IAS_Spot': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.Mtf.IAS_GeometricMtf': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.Mtf.IAS_GeometricMtfMap': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.Mtf.IAS_GeometricMtfvsField': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.Mtf.IAS_GeometricThroughFocusMtf': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.EncircledEnergy.IAS_DiffractionEncircledEnergy': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.EncircledEnergy.IAS_GeometricEncircledEnergy': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.ExtendedScene.IAS_GeometricImageAnalysis': 'ScatterRays',
    'ZOSAPI.Analysis.Settings.RayTracing.IAS_NSCSingleRayTrace': 'ScatterNSCRays',
}

# Floating aperture: reflected as an empty interface in this build.
FLOATING_APERTURE = {
    'interface': 'ZOSAPI.Editors.LDE.ISurfaceApertureFloating',
    'property_count': 0,
    'method_count': 0,
    'hosts_scatter': False,
    'note': ('reflection exposes no properties or methods, so neither a scatter model nor a '
             'scatter fraction can be set through the floating aperture in this build'),
}


def is_placeholder(name):
    """True when a native resource name is one of the observed placeholder values."""
    return str(name).strip().casefold() in PLACEHOLDERS


def valid_names(names):
    """Drop placeholder entries and keep the original order."""
    return [name for name in names if not is_placeholder(name)]


def require_capability(kind, field):
    """Reject a field the reflected settings interface for ``kind`` does not provide."""
    if kind not in TYPE_INTERFACE:
        raise ZemaxError('INVALID_ARGUMENT', '未知的散射类型。', type=kind, known=list(TYPE_INTERFACE))
    if field == 'scatter_fraction' and kind not in SCATTER_FRACTION_HOSTS:
        raise ZemaxError('UNSUPPORTED_SETTING', '该散射类型的设置对象没有散射比例属性。',
                         type=kind, field=field,
                         settings_interface=TYPE_INTERFACE[kind],
                         scatter_fraction_hosts=list(SCATTER_FRACTION_HOSTS))


def require_resource(kind, value, names):
    """Validate a requested resource against the native list, ignoring placeholders."""
    available = valid_names(names)
    placeholders = [name for name in names if is_placeholder(name)]
    if not available:
        raise ZemaxError('UNSUPPORTED_SETTING', '本机该散射类型的资源接口没有返回可用资源。',
                         type=kind, resource_query=RESOURCE_QUERY.get(kind),
                         placeholder_values=placeholders, native_names=list(names))
    folded = {name.casefold(): name for name in available}
    match = folded.get(str(value).casefold())
    if match is None:
        raise ZemaxError('INVALID_RESOURCE', '散射资源不在可用列表中。',
                         type=kind, requested=value, available=available)
    return match


def catalog_diagnostics(value, names):
    """Diagnostics for an ISScatterCatalog selection without inventing new hard rules."""
    available = valid_names(names)
    suffix = str(value).rsplit('.', 1)[-1].lower() if '.' in str(value) else ''
    matched_name = next((name for name in available
                         if str(value).casefold() == name.casefold()), None)
    return dict(requested=value, available=available, matched=matched_name is not None,
                matched_name=matched_name, suffix=suffix, suffix_is_isx=(suffix == 'isx'))

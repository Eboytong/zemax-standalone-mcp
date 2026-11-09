"""Declared GRADIUM resource metadata from the installed GRD/SGRIN files.

This module reports only what the selected resource files declare: the profile
block (name, glass family, maximum z / boule thickness and the twelve stored
coefficients) and the glass-family block (wavelength range and reference
wavelength). It never evaluates the profile polynomial, never predicts a ray or
capping outcome, and never changes a native coordinate, setting or request.

The profile file actually selected by the system is used: a relative name is
resolved against the ``Glasscat`` resource directory, an absolute name is read
directly, so a task-owned GRD is never attributed to the stock ``PROFILE.GRD``.

Everything here is best effort: a missing, unreadable, unsupported or non-finite
resource yields a status record instead of an exception, so auxiliary provenance
can never turn a previously working profile query into a failure, and no NaN/Inf
value can reach the result JSON.
"""
from __future__ import annotations

import math
from pathlib import Path

GRD_COEFFICIENT_COUNT = 12
GRD_NAME_LIMIT = 20
METADATA_SCOPE = ('declared GRD/SGRIN metadata only; no profile evaluation, no ray or boundary '
                  'prediction, no native setting change')


def glasscat_directory(application):
    """Return ``(directory, reason)``; ``reason`` is None when the path is usable."""
    if application is None:
        return None, 'no connected native application'
    try:
        root = Path(str(application.ZemaxDataDir))
    except Exception as exc:  # pragma: no cover - depends on the installed API object
        return None, f'ZemaxDataDir unavailable: {exc}'
    if not str(root) or not root.is_absolute():
        return None, f'ZemaxDataDir is not an absolute path: {root}'
    return root / 'Glasscat', None


def read_declared_text(path):
    """Read a declared resource file; ASCII layout, tolerant fallback."""
    return Path(path).read_text(encoding='utf-8', errors='replace')


def _finite(value, field, owner):
    if not math.isfinite(value):
        raise ValueError(f'non-finite {field} for {owner}: {value!r}')
    return value


def parse_profile_blocks(text):
    """Parse documented GRD blocks into ``{name: block}``; raise ``ValueError`` when unsupported."""
    lines = text.splitlines()
    blocks = {}
    index = 0
    while index < len(lines):
        header = lines[index].strip()
        index += 1
        if not header or header.startswith('!'):
            continue
        parts = header.split()
        if len(parts) < 3:
            raise ValueError(f'profile header needs name, glass family and maximum z: {header!r}')
        name, family = parts[0], parts[1]
        if len(name) > GRD_NAME_LIMIT:
            raise ValueError(f'profile name longer than {GRD_NAME_LIMIT} characters: {name!r}')
        maximum_z = _finite(float(parts[2]), 'maximum z', f'profile {name!r}')
        if maximum_z <= 0:
            raise ValueError(f'maximum z must be positive: {header!r}')
        coefficients = []
        while len(coefficients) < GRD_COEFFICIENT_COUNT and index < len(lines):
            candidate = lines[index].strip()
            index += 1
            if not candidate or candidate.startswith('!'):
                continue
            coefficients.append(_finite(float(candidate.split()[0]), 'coefficient', f'profile {name!r}'))
        if len(coefficients) != GRD_COEFFICIENT_COUNT:
            raise ValueError(f'profile {name!r} has {len(coefficients)} coefficients')
        if name in blocks:
            raise ValueError(f'duplicate profile name {name!r}')
        blocks[name] = dict(name=name, family=family, maximum_z=maximum_z,
                            coefficients=coefficients, extra_tokens=parts[3:])
    return blocks


def parse_family_blocks(text):
    """Parse documented ``SGRIN.DAT`` family headers into ``{family: block}``.

    Only the header fields are read (wavelength range, reference wavelength, term
    counts). The coefficient rows that follow are skipped by shape - a family name
    is a non-numeric single token, while coefficient rows start with a number - so
    the row layout is never interpreted.
    """
    lines = [line.strip() for line in text.splitlines()]
    families = {}
    index = 0
    while index < len(lines):
        if not lines[index] or lines[index].startswith('!'):
            index += 1
            continue
        name = lines[index]
        header = lines[index + 1:index + 4]
        if len(header) != 3:
            raise ValueError(f'family {name!r} header is truncated')
        bounds = header[0].split()
        if len(bounds) != 2:
            raise ValueError(f'family {name!r} wavelength range is invalid: {header[0]!r}')
        minimum = _finite(float(bounds[0]), 'minimum wavelength', f'family {name!r}')
        maximum = _finite(float(bounds[1]), 'maximum wavelength', f'family {name!r}')
        if not 0 < minimum < maximum:
            raise ValueError(f'family {name!r} wavelength range is not increasing: {header[0]!r}')
        reference = _finite(float(header[1].split()[0]), 'reference wavelength', f'family {name!r}')
        if reference <= 0:
            raise ValueError(f'family {name!r} reference wavelength is not positive: {header[1]!r}')
        terms = header[2].split()
        if len(terms) != 2:
            raise ValueError(f'family {name!r} term counts are invalid: {header[2]!r}')
        families[name] = dict(name=name, minimum_wavelength_um=minimum, maximum_wavelength_um=maximum,
                              reference_wavelength_um=reference,
                              index_terms=int(terms[0]), dispersion_terms=int(terms[1]))
        index += 4
        while index < len(lines) and lines[index] and not lines[index].startswith('!'):
            try:
                float(lines[index].split()[0])
            except ValueError:
                break
            index += 1
    return families


def resolve_profile_path(application, profile_file):
    """Resolve the selected profile file to ``(path, resource_root, reason, origin)``.

    A relative name keeps its own relative identity under the ``Glasscat`` resource
    root (sub-directories are preserved, never truncated to the bare file name); an
    absolute name is used as given while the ``Glasscat`` root is still reported as
    the native resource root. ``reason`` is None only when a path results.
    """
    directory, reason = glasscat_directory(application)
    if profile_file and str(profile_file).strip():
        candidate = Path(str(profile_file))
        if candidate.is_absolute():
            return candidate, directory, None, 'absolute'
        if directory is None:
            return None, None, reason, 'relative'
        return directory / candidate, directory, None, 'relative'
    if directory is None:
        return None, None, reason, 'default'
    return directory / 'PROFILE.GRD', directory, None, 'default'


def profile_metadata(path, name, resource_root=None, origin=None):
    """Declared block for one profile name in the selected file; status record on any problem."""
    result = dict(status='unavailable', profile_name=name,
                  directory=str(resource_root) if resource_root else None,
                  native_resource_root=str(resource_root) if resource_root else None,
                  source=str(path) if path else None, path_origin=origin)
    if path is None:
        result['reason'] = 'profile file could not be resolved'
        return result
    path = Path(path)
    if not path.is_file():
        result['reason'] = f'profile file {path} is not present'
        return result
    try:
        blocks = parse_profile_blocks(read_declared_text(path))
    except (OSError, ValueError) as exc:
        result.update(status='unsupported', reason=str(exc))
        return result
    block = blocks.get(name)
    if block is None:
        result.update(reason=f'profile {name!r} is not declared in {path.name}',
                      available=sorted(blocks))
        return result
    result.update(status='declared', family=block['family'], maximum_z=block['maximum_z'],
                  coefficient_count=len(block['coefficients']), coefficients=block['coefficients'],
                  extra_tokens=block['extra_tokens'])
    return result


def family_metadata(family, resource_root=None):
    """Declared ``SGRIN.DAT`` header for one glass family; status record on any problem.

    The family header is read from the native resource root (``Glasscat``), which is
    the only location the installed resource layout documents. A ``SGRIN.DAT`` that
    happens to sit next to a task-owned profile file is **not** treated as the active
    family file: nothing in the available readback binds it to the analysis. The
    declaration is therefore reported as a candidate with ``native_binding``
    unconfirmed rather than as an adopted native value.
    """
    result = dict(status='unavailable', family=family,
                  directory=str(resource_root) if resource_root else None,
                  native_resource_root=str(resource_root) if resource_root else None,
                  declaration='candidate', native_binding='unconfirmed',
                  binding_basis='family header read from the Glasscat resource root; no native readback '
                                'confirms which family file the analysis used')
    if family is None:
        result['reason'] = 'no glass family declared by the profile block'
        return result
    if resource_root is None:
        result['reason'] = 'native resource root (Glasscat) is unavailable'
        return result
    path = Path(resource_root) / 'SGRIN.DAT'
    result['source'] = str(path)
    if not path.is_file():
        result['reason'] = f'{path} is not present'
        return result
    try:
        families = parse_family_blocks(read_declared_text(path))
    except (OSError, ValueError) as exc:
        result.update(status='unsupported', reason=str(exc))
        return result
    block = families.get(family)
    if block is None:
        result.update(reason=f'family {family!r} is not declared in {path.name}')
        return result
    result.update(status='declared',
                  reference_wavelength_um=block['reference_wavelength_um'],
                  wavelength_range_um=[block['minimum_wavelength_um'], block['maximum_wavelength_um']])
    return result


def resource_metadata(application, profile_file, material):
    """Declared GRD/SGRIN metadata for a GRADIUM surface; never raises."""
    try:
        path, root, reason, origin = resolve_profile_path(application, profile_file)
        result = dict(status='unavailable', profile_file=profile_file, material=material,
                      scope=METADATA_SCOPE, path_origin=origin,
                      directory=str(root) if root else None,
                      native_resource_root=str(root) if root else None)
        if reason is not None:
            result['reason'] = reason
            return result
        profile = profile_metadata(path, material, root, origin)
        result['profile'] = profile
        result['family'] = family_metadata(profile.get('family'), root)
        result['status'] = profile['status']
        if profile['status'] != 'declared':
            result['reason'] = profile.get('reason')
        if origin == 'absolute':
            result['path_note'] = ('profile file is outside the native resource root; the Glasscat root is '
                                   'still reported as the native resource root')
        return result
    except Exception as exc:  # auxiliary provenance must never break a working query
        return dict(status='unavailable', reason=f'unexpected metadata error: {exc}',
                    profile_file=profile_file, material=material, scope=METADATA_SCOPE)

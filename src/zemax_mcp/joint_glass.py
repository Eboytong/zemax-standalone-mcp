"""Joint assignment planning; native evaluation is shared with single-group trials."""
import itertools
import math

from .errors import ZemaxError
from .detectors import check_setting_value


def identity_key(identity):
    return identity['catalog'].casefold().removesuffix('.agf'), identity['material'].casefold()


def assignment_key(assignments):
    return tuple((a['group'], *identity_key(a['identity'])) for a in assignments)


def combination(assignments):
    return dict(assignments=assignments, catalog='joint',
                material=' | '.join(a['identity']['material'] for a in assignments))


def enumerate_assignments(pools, strategy, limit):
    """Always include the unchanged control; each slot pool starts with its original."""
    baseline = [dict(group=group, identity=pool[0]) for group, pool in pools]
    output, seen = [], set()
    def add(values):
        key = assignment_key(values)
        if key not in seen and len(output) < limit:
            output.append(combination(values)); seen.add(key)
    add(baseline)
    if strategy == 'cartesian':
        for choices in itertools.islice(itertools.product(*(pool for _, pool in pools)), limit):
            add([dict(group=group, identity=identity) for (group, _), identity in zip(pools, choices)])
    else:
        selected = pools[:1] if strategy == 'beam' else pools
        for group, pool in selected:
            for identity in pool:
                add([dict(a, identity=identity) if a['group'] == group else a.copy() for a in baseline])
    return output


def read_identity(tool, catalog, material):
    from .materials import choose_catalog
    selected_catalog = choose_catalog(tool.GetAllCatalogs(), catalog)
    tool.SelectedCatalog = selected_catalog
    check_setting_value('SelectedCatalog', selected_catalog, str(tool.SelectedCatalog))
    available = [str(v) for v in tool.GetAllMaterials()]
    matches = [name for name in available if name.casefold() == material.casefold()]
    if len(matches) != 1:
        raise ZemaxError('INVALID_RESOURCE', '槽位材料不在指定目录中。', catalog=catalog, material=material)
    tool.SelectedMaterial = matches[0]
    check_setting_value('SelectedMaterial', matches[0], str(tool.SelectedMaterial))
    raw = str(tool.RelCost)
    try:
        cost = float(raw)
    except ValueError:
        cost = None
    if cost is not None and not math.isfinite(cost):cost = None
    return dict(catalog=str(tool.SelectedCatalog), material=str(tool.SelectedMaterial), nd=float(tool.Nd), vd=float(tool.Vd),
                minimum_wavelength_um=float(tool.MinimumWavelength), maximum_wavelength_um=float(tool.MaximumWavelength),
                relative_cost=cost, relative_cost_raw=raw, exclude_substitution=bool(tool.ExcludeSubstitution), status=str(tool.MaterialStatus))


def discover_joint_steps(b, q, groups):
    from .glass_trials import discover_steps, catalog_filter
    from .materials import owned_catalog
    pools, records = [], []
    waves = [float(b.system.SystemData.Wavelengths.GetWavelength(i).Wavelength)
             for i in range(1, int(b.system.SystemData.Wavelengths.NumberOfWavelengths) + 1)]
    for slot in q.joint_slots:
        baseline_name = groups[slot.group]['material']
        if slot.materials:
            catalogs = b.system.SystemData.MaterialCatalogs
            loaded = list(dict.fromkeys(str(c) for c in catalogs.GetCatalogsInUse() if str(c).strip()))
            providers = [c for c in loaded if baseline_name in [str(m) for m in catalogs.GetMaterialsInCatalog(c)]]
            if len(providers) != 1:
                raise ZemaxError('AMBIGUOUS_MATERIAL', '原材料目录身份不唯一。', material=baseline_name, catalogs=providers)
            with owned_catalog(b) as tool:
                baseline = read_identity(tool, providers[0], baseline_name)
            scan = None
        else:
            scan = yield from discover_steps(b, q.model_copy(update={'max_candidates': max(1, slot.pool_size - 1)}), baseline_name)
            baseline = scan['baseline']
        pool = [baseline]; rejected = []
        if slot.materials:
            with owned_catalog(b) as tool:
                for choice in slot.materials:
                    candidate = read_identity(tool, choice.catalog, choice.material)
                    if identity_key(candidate) == identity_key(baseline):continue
                    reasons, distance = catalog_filter(candidate, baseline, q, waves)
                    candidate['distance'] = distance
                    if reasons:rejected.append(dict(identity=candidate, reasons=reasons))
                    else:pool.append(candidate)
                    yield
        else:
            pool.extend(scan['selected'][:slot.pool_size - 1])
        pools.append((slot.group, pool))
        records.append(dict(group=slot.group, baseline=baseline, selected=pool, rejected=rejected,
                            discovery=scan if not slot.materials else None))
    candidates = enumerate_assignments(pools, q.search_strategy, q.max_evaluations)
    return candidates, pools, dict(slots=records, combination_count=math.prod(len(pool) for _, pool in pools),
                                  strategy=q.search_strategy, maximum_evaluations=q.max_evaluations)


def available_slots(b):
    b._require_sequential()
    system = b.system; end = int(system.LDE.NumberOfSurfaces) - 1
    catalogs = system.SystemData.MaterialCatalogs
    loaded = [str(x) for x in catalogs.GetCatalogsInUse() if str(x).strip()]
    slots, skipped = [], []
    i = 1
    while i < end:
        row = system.LDE.GetSurfaceAt(i); material = str(row.Material)
        if not material or material == 'MIRROR':
            i += 1;continue
        last = i + 1
        while last < end and str(system.LDE.GetSurfaceAt(last).Material) == material:last += 1
        providers = [c for c in loaded if material in [str(v) for v in catalogs.GetMaterialsInCatalog(c)]]
        reasons = []
        if len(providers) != 1:reasons.append('catalog_identity_not_unique')
        if any(str(system.LDE.GetSurfaceAt(j).MaterialCell.Solve) != 'Fixed' for j in range(i, last)):
            reasons.append('material_solve_protected')
        contribution_conditions = []
        if any(str(system.LDE.GetSurfaceAt(j).Type) != 'Standard' for j in range(i, last + 1)):
            contribution_conditions.append('contribution_requires_standard_surfaces')
        record = dict(first_surface=i, last_surface=last, material=material, catalogs=providers, skip_reasons=reasons,
            contribution_conditions=contribution_conditions)
        (skipped if reasons else slots).append(record);i = last
    return dict(slots=slots, skipped=skipped, units='current lens units', source='native LDE and catalogs')

"""Select existing JSON Schema branches and retain their reachable definitions."""
from copy import deepcopy

from .errors import ZemaxError


def reachable(schema):
    definitions = schema.get('$defs', {})
    body = {k: deepcopy(v) for k, v in schema.items() if k != '$defs'}
    used, pending = {}, [body]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str) and value.startswith('#/$defs/'):
            name = value[len('#/$defs/'):].replace('~1', '/').replace('~0', '~')
            if name not in used:
                if name not in definitions:
                    raise ZemaxError('INVALID_SCHEMA_REFERENCE', '请求定义缺少引用。', reference=value)
                used[name] = deepcopy(definitions[name]); pending.append(used[name])
    return body | ({'$defs': dict(sorted(used.items()))} if used else {})


def select_branch(schema, field, value):
    result = deepcopy(schema)
    request = result.get('properties', {}).get('request', {})
    mapping = request.get('discriminator', {}).get('mapping', {})
    if request.get('discriminator', {}).get('propertyName') != field or value not in mapping:
        raise ZemaxError('UNKNOWN_CAPABILITY_BRANCH', '该工具没有此请求分支。', field=field, value=value)
    result['properties']['request'] = {'$ref': mapping[value]}
    return reachable(result)


def restrict_analyses(schema, kinds):
    result = deepcopy(schema)
    allowed = set(kinds)
    found = set()
    def visit(value):
        if isinstance(value, dict):
            discriminator = value.get('discriminator', {})
            mapping = discriminator.get('mapping', {})
            if discriminator.get('propertyName') == 'kind' and 'wavefront' in mapping:
                selected = {k: v for k, v in mapping.items() if k in allowed}
                found.update(selected)
                discriminator['mapping'] = selected
                value['oneOf'] = [{'$ref': ref} for ref in selected.values()]
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(result)
    if found != allowed:
        raise ZemaxError('UNKNOWN_ANALYSIS_SELECTION', '分析选择不属于本工具合同。', kinds=sorted(allowed - found))
    return reachable(result)

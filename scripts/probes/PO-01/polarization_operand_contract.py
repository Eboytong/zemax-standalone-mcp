"""Inspect the documented CODA polarization-ray operand and query controls."""
import json
import os
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT / 'src'))


def run(destination):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    result = dict(columns=[], queries=[])

    def call(name, args=None):
        reply = backend.dispatch(name, args or {})
        if not reply.get('ok'):
            raise RuntimeError(dict(tool=name, reply=reply))
        return reply['data']

    def save():
        (folder / 'probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    try:
        result['connect'] = call('connect')
        sample = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        call('open_lens', dict(path=str(sample)))
        before = dict(settings=call('get_system_settings'), surfaces=call('get_surfaces', dict(start=0, count=100)), merit=call('get_merit_function'))
        result['baseline'] = before
        mfe = backend.system.MFE
        code = backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType, 'CODA')
        count = int(mfe.NumberOfOperands)
        row = mfe.AddOperand()
        try:
            row.ChangeType(code)
            cells = []
            for number in range(1, 9):
                cell = row.GetOperandCell(backend.native.enum(backend.native.api.Editors.MFE.MeritColumn, f'Param{number}'))
                cells.append(cell)
                result['columns'].append(dict(number=number, header=str(cell.Header), type=str(cell.DataType), active=bool(cell.IsActive)))
            save()
            for label, values in [('default', [0, 2, 1, 0., 1., 101]), ('field2', [0, 2, 2, 0., 1., 101]),
                                  ('pupilcenter', [0, 2, 1, 0., 0., 101]), ('phase', [0, 2, 1, 0., 1., 111]),
                                  ('intensity', [0, 2, 1, 0., 1., 0]), ('surface1', [1, 2, 1, 0., 1., 101])]:
                for component in (101, 102, 103, 104, 105, 106, 110, 111, 112, 113):
                    args = [values[0], values[1], values[2], component, values[3], values[4], 0., 0.]
                    query = dict(case=label, data=component, arguments=args)
                    result['queries'].append(query)
                    try:
                        query['value'] = float(mfe.GetOperandValue(code, *args))
                    except Exception as exc:
                        query['error'] = dict(type=type(exc).__name__, message=str(exc))
                    save()
        finally:
            mfe.RemoveOperandAt(count + 1)
            result['temporary_row_removed'] = int(mfe.NumberOfOperands) == count
        result['after'] = dict(settings=call('get_system_settings'), surfaces=call('get_surfaces', dict(start=0, count=100)), merit=call('get_merit_function'))
        result['preserved'] = result['after'] == before
    except BaseException as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        result['disconnect'] = backend.dispatch('disconnect', {})
        receipt = folder / 'state/close_receipt.json'
        result['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        save()
    print(json.dumps(dict(columns=result['columns'], query_count=len(result['queries']), errors=[q for q in result['queries'] if 'error' in q], preserved=result.get('preserved'), close=result.get('close_receipt')), ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1])

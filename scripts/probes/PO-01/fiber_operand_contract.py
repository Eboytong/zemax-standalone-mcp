"""Inspect documented FICL columns and compare selectable native queries."""
import json
import os
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT / 'src')]
from probe_common import adapter, paged_result, poll_task


def run(destination):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    record = dict(calls=[], queries=[], manual='2024 R2 pp.1116-1117')
    call = adapter(backend, record['calls'])

    def save():
        (folder / 'probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    try:
        record['connection'] = call('connect')
        call('open_lens', dict(path=str(Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline = call('get_system_settings')
        surfaces = call('get_surfaces', dict(start=0, count=100))
        merit = call('get_merit_function')
        record.update(baseline=baseline, surfaces=surfaces, merit_before=merit)
        task = poll_task(call, call('run_analysis', dict(request=dict(kind='fiber_coupling_settings'))), record)
        record['topic_task'] = task
        if task['state'] != 'succeeded':
            raise RuntimeError(task)
        record['topic'] = paged_result(call, task['task_id'], record)
        mfe = backend.system.MFE
        code = backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType, 'FICL')
        record['signatures'] = [str(m) for m in mfe.GetType().GetMethods() if m.Name == 'GetOperandValue']
        count = int(mfe.NumberOfOperands)
        row = mfe.AddOperand()
        try:
            row.ChangeType(code)
            record['columns'] = []
            cells = []
            for number in range(1, 9):
                cell = row.GetOperandCell(backend.native.enum(backend.native.api.Editors.MFE.MeritColumn, f'Param{number}'))
                cells.append(cell)
                record['columns'].append(dict(number=number, header=str(cell.Header), data_type=str(cell.DataType), active=bool(cell.IsActive)))
            save()
            for label, sampling, wave, field, ignore, sna, rna, pol in [
                ('base', 2, 1, 1, 1, .1, .1, 0),
                ('receiver_na', 2, 1, 1, 1, .1, .05, 0),
                ('field', 2, 1, 2, 1, .1, .1, 0),
                ('wave', 2, 2, 1, 1, .1, .1, 0),
                ('source', 2, 1, 1, 0, .05, .1, 0),
                ('polarized', 2, 1, 1, 1, .1, .1, 1),
            ]:
                for data in range(6):
                    args = [sampling, wave, float(field), float(ignore), sna, rna, float(data), float(pol)]
                    query = dict(case=label, arguments=args)
                    record['queries'].append(query)
                    try:
                        query['direct'] = float(mfe.GetOperandValue(code, *args))
                        for cell, value in zip(cells, args):
                            if str(cell.DataType).lower() == 'integer':
                                cell.IntegerValue = int(value)
                            else:
                                cell.DoubleValue = float(value)
                        query['readback'] = [int(c.IntegerValue) if str(c.DataType).lower() == 'integer' else float(c.DoubleValue) for c in cells]
                        mfe.CalculateMeritFunction()
                        query['row_value'] = float(row.Value)
                    except Exception as exc:
                        query['error'] = dict(type=type(exc).__name__, message=str(exc))
                    save()
        finally:
            mfe.RemoveOperandAt(count + 1)
            record['temporary_row_removed'] = int(mfe.NumberOfOperands) == count
        record['settings_preserved'] = call('get_system_settings') == baseline
        record['surfaces_preserved'] = call('get_surfaces', dict(start=0, count=100)) == surfaces
        record['merit_after'] = call('get_merit_function')
        record['merit_preserved'] = record['merit_after'] == merit
    except BaseException as exc:
        record['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        save()
    print(json.dumps(dict(columns=record.get('columns'), queries=record['queries'], close=record['close_receipt']), ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1])

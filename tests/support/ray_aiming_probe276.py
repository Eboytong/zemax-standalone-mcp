"""Bounded formal native wait/cancel probe for Ray Aiming Wizard."""
import json
import time
from pathlib import Path

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean
from zemax_mcp.design_tools import RAY_FIELDS, ENUMS


def run():
    folder = Path('verification/development/ED-04/ray-aiming276').resolve()
    folder.mkdir(exist_ok=False)
    b = Backend(Config(Config.from_env().install_dir, folder/'native'))
    record = dict(calls=[], cases=[], wait_seconds=10,
                  formal_methods=['RunAndWaitWithTimeout', 'WaitWithTimeout', 'Cancel', 'Close'])

    def save():
        (folder/'probe.json').write_text(json.dumps(clean(record), ensure_ascii=False, indent=2), encoding='utf-8')

    def call(name, args=None):
        result = b.dispatch(name, args or {})
        record['calls'].append(dict(tool=name, arguments=args, response=result))
        save()
        assert result['ok'], result
        return result['data']

    def state(tool):
        return {name: getattr(tool, name) for name in
                ['IsAsynchronous', 'IsFiniteDuration', 'IsRunning', 'CanCancel', 'Succeeded', 'Progress', 'Status', 'ErrorMessage']}

    def ray_settings():
        current = b.system.SystemData.RayAiming
        return {name: str(getattr(current, name)) if name in ENUMS else getattr(current, name)
                for name in RAY_FIELDS}

    try:
        call('connect')
        for baseline in ['controlled', 'cooke']:
            if baseline == 'controlled':
                call('new_system')
                call('insert_surfaces', dict(at=1, count=2))
                call('update_system_settings', dict(aperture_value=2, wavelengths=[dict(wavelength_um=.55)]))
                call('update_surfaces', dict(changes=[
                    dict(surface=1, radius=50, thickness=5, material='N-BK7', semi_diameter=2, replace_solves=True),
                    dict(surface=2, radius=-50, thickness=47, semi_diameter=2, replace_solves=True)]))
            else:
                call('open_lens', dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
            before = dict(surfaces=call('get_surfaces'), settings=call('get_system_settings'),
                          merit=call('get_merit_function'), ray_aiming=ray_settings())
            tool = b.system.Tools.OpenRayAimingWizard()
            holder = dict(native=tool)
            item = dict(baseline=baseline, before=state(tool), ray_before=before['ray_aiming'])
            record['cases'].append(item)
            save()
            try:
                print('Native bounded wizard run:', baseline, flush=True)
                start = time.monotonic()
                item['run_status'] = str(tool.RunAndWaitWithTimeout(10.0))
                item['run_elapsed_seconds'] = time.monotonic()-start
                item['after_wait'] = state(tool)
                save()
                print('Wait returned:', item['run_status'], flush=True)
                if tool.IsRunning:
                    if tool.CanCancel:
                        item['cancel_accepted'] = bool(tool.Cancel())
                        item['cancel_wait_status'] = str(tool.WaitWithTimeout(10.0))
                    item['after_cancel'] = state(tool)
                elif tool.Succeeded:
                    recommended = tool.GetRecommendedSettings()
                    item['recommended'] = {name: str(getattr(recommended, name)) if name in ENUMS else getattr(recommended, name)
                                           for name in RAY_FIELDS} if recommended is not None else None
                item['ray_after'] = ray_settings()
            finally:
                item['close_confirmed'] = b._close_task_native(holder)
                item['close_details'] = {k: v for k, v in holder.items() if k != 'native'}
                save()
            if not item['close_confirmed']:
                break
            item['source_preserved'] = (before['surfaces'] == call('get_surfaces') and
                                        before['settings'] == call('get_system_settings') and
                                        before['merit'] == call('get_merit_function') and
                                        before['ray_aiming'] == ray_settings())
            save()
        record['disconnect'] = b.dispatch('disconnect', {})
    finally:
        b.shutdown()
        save()
    print(json.dumps(clean(dict(cases=record['cases'], disconnect=record.get('disconnect'))), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    run()

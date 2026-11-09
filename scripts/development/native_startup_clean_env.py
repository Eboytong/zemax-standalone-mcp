"""Prepare a project-external Python runtime and run one Standalone check."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.development import native_startup_check as check


def run(runtime_root, evidence_root):
    runtime_root = Path(runtime_root).resolve()
    evidence_root = Path(evidence_root).resolve()
    if runtime_root.is_relative_to(ROOT):
        raise ValueError('The diagnostic environment must be outside the project directory.')
    if sys.version_info[:2] != (3, 14) or struct.calcsize('P') != 8:
        raise ValueError('The base interpreter must be Python 3.14 x64.')
    evidence_root.mkdir(parents=True, exist_ok=False)
    record = dict(runtime_root=str(runtime_root), base_python=sys.executable,
                  repository=str(ROOT), native_requested=False, stages=[])
    print('Evidence: ' + str(evidence_root), flush=True)
    stage = 'base_context'
    try:
        code = check.run(evidence_root / 'base-context', context_only=True)
        record['stages'].append(dict(stage=stage, exit_code=code))
        if code:
            record['state'] = 'blocked_base_context'
            return code

        python = runtime_root / 'Scripts/python.exe'
        commands = []
        if not python.is_file():
            commands.append(('create_environment', [sys.executable, '-B', '-m', 'venv', str(runtime_root)]))
        commands += [
            ('runtime_version', [str(python), '-B', '-c',
             "import sys,struct; assert sys.version_info[:2] == (3,14) and struct.calcsize('P') == 8, 'Python 3.14 x64 required'"]),
            ('install_dependencies', [str(python), '-B', '-m', 'pip', '--log', str(evidence_root / 'pip.log'),
             'install', '--constraint', str(ROOT / 'requirements/all.lock.txt'),
             '--editable', str(ROOT) + '[reports,test]']),
            ('native_check', [str(python), '-B', '-X', 'utf8',
             str(ROOT / 'scripts/development/native_startup_check.py'),
             '--output-dir', str(evidence_root / 'native')]),
        ]
        for stage, command in commands:
            print('Stage: ' + stage, flush=True)
            if stage == 'native_check':
                record['native_requested'] = True
            completed = subprocess.run(command, cwd=ROOT, check=False)
            code = completed.returncode
            record['stages'].append(dict(stage=stage, command=command, exit_code=code))
            if code:
                record.update(state='failed', failed_stage=stage)
                return code
        record['state'] = 'passed'
        return 0
    except Exception as exc:
        record.update(state='failed', failed_stage=stage,
                      error=dict(type=type(exc).__name__, message=str(exc)))
        raise
    finally:
        (evidence_root / 'bootstrap.json').write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Evidence: ' + str(evidence_root), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, default=Path.home() / 'Zemax_MCP_Runtime/.venv')
    label = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    parser.add_argument('--output-dir', type=Path, default=ROOT /
                        '.local/evidence/development/BASE-04' / ('external-runtime-' + label))
    args = parser.parse_args()
    return run(args.runtime_root, args.output_dir)


if __name__ == '__main__':
    sys.exit(main())

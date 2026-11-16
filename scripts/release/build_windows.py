"""Build the Windows wheel and ZIP from a temporary source snapshot."""
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[2]
# 2026-11-16 00:00:00 UTC; override to reproduce another release timestamp.
DEFAULT_EPOCH = 1794787200


def run(*args, cwd, env):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main():
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 14) or struct.calcsize('P') != 8:
        raise SystemExit('Python 3.14 x64 on Windows is required.')
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    version = project['version']
    release = ROOT / 'releases' / version
    wheel_name = f'zemax_standalone_mcp-{version}-py3-none-any.whl'
    bundle_name = f'zemax-standalone-mcp-{version}-windows-x64'
    wheel_target = release / wheel_name
    zip_target = release / f'{bundle_name}.zip'
    if wheel_target.exists() or zip_target.exists():
        raise SystemExit('Release artifacts already exist. Move them before rebuilding.')
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', str(DEFAULT_EPOCH)))
    timestamp = datetime.fromtimestamp(epoch, timezone.utc)
    if not 1980 <= timestamp.year <= 2107:
        raise SystemExit('SOURCE_DATE_EPOCH must be within the ZIP timestamp range (1980–2107).')
    environment = os.environ.copy()
    environment.update(SOURCE_DATE_EPOCH=str(epoch), PYTHONHASHSEED='0',
                       PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    environment.pop('PYTHONPATH', None)
    environment.pop('PYTHONHOME', None)
    with tempfile.TemporaryDirectory(prefix='zemax-release-') as temporary:
        work = Path(temporary)
        source = work / 'source'
        source.mkdir()
        for name in ('pyproject.toml', 'README.md', 'LICENSE'):
            shutil.copyfile(ROOT / name, source / name)
        shutil.copytree(ROOT / 'src', source / 'src',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
        build_env = work / 'build-env'
        venv.EnvBuilder(with_pip=True).create(build_env)
        python = str(build_env / 'Scripts' / 'python.exe')
        run(python, '-I', '-B', '-m', 'pip', 'install', '--disable-pip-version-check',
            '-r', str(ROOT / 'requirements' / 'build.lock.txt'), cwd=work, env=environment)
        wheel_dir = work / 'wheels'
        wheel_dir.mkdir()
        run(python, '-I', '-B', '-c',
            'from setuptools.build_meta import build_wheel; build_wheel(' + repr(str(wheel_dir)) + ')',
            cwd=source, env=environment)
        wheel = wheel_dir / wheel_name
        files = {f'releases/{version}/{wheel_name}': wheel}
        for name in ('install.ps1', 'start.ps1', 'start-2026r1.ps1', 'README.md', 'LICENSE',
                     'requirements/core.lock.txt', 'requirements/all.lock.txt',
                     'requirements/build.lock.txt', 'examples/config/mcp.config.example.json',
                     'docs/guides/windows-distribution.md'):
            files[name] = ROOT / name
        archive = work / f'{bundle_name}.zip'
        # Stable ordering, timestamps and attributes; stored entries avoid compressor variation.
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as bundle:
            for name, path in sorted(files.items()):
                entry = zipfile.ZipInfo(f'{bundle_name}/{name}', timestamp.timetuple()[:6])
                entry.create_system = 0
                entry.external_attr = 0x20
                bundle.writestr(entry, path.read_bytes())
        release.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(wheel, wheel_target)
        shutil.copyfile(archive, zip_target)
    print(f'Wheel: {wheel_target}\nWindows ZIP: {zip_target}')


if __name__ == '__main__':
    main()

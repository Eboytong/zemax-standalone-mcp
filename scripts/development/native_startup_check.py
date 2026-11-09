"""Run the bounded Standalone check from a normal Windows user terminal."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from tests.support import connection_probe019 as probe


def file_label(path):
    import win32security
    record = dict(path=str(path))
    try:
        descriptor = win32security.GetFileSecurity(str(path), 0x10)
        record['label_sddl'] = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(
            descriptor, 1, 0x10)
    except OSError as exc:
        record['error'] = str(exc)
    return record


def token_context(process):
    import win32con
    import win32security
    token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
    try:
        integrity = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)
        sid = integrity[0] if isinstance(integrity, tuple) else integrity
        sid_text = win32security.ConvertSidToStringSid(sid)
        return dict(integrity_sid=sid_text,
                    integrity_rid=int(sid_text.rsplit('-', 1)[1]),
                    elevated=bool(win32security.GetTokenInformation(token, win32security.TokenElevation)),
                    session_id=win32security.GetTokenInformation(token, win32security.TokenSessionId))
    finally:
        token.Close()


def process_context():
    import win32api
    context = dict(pid=os.getpid(), **token_context(win32api.GetCurrentProcess()),
                   python=sys.executable, repository=str(ROOT))
    parent_pid = os.getppid()
    parent = dict(pid=parent_pid)
    try:
        process = win32api.OpenProcess(0x1000, False, parent_pid)
        try:
            parent.update(token_context(process))
        finally:
            process.Close()
    except OSError as exc:
        parent['error'] = str(exc)
    context['parent'] = parent
    context['file_labels'] = [file_label(path) for path in dict.fromkeys(
        [ROOT, Path(sys.executable), Path(getattr(sys, '_base_executable', sys.executable))])]
    return context


def run(folder, *, context_only=False):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    context = process_context()
    context.update(checked_at=datetime.now(timezone.utc).isoformat(), mode='Standalone')
    (folder/'process-context.json').write_text(
        json.dumps(context, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(context=context, evidence=str(folder)), ensure_ascii=False), flush=True)
    if context_only:
        result = dict(state='process_context_only', native_started=False,
                      normal_user_context=context['integrity_rid'] >= 8192)
        code = 0 if result['normal_user_context'] else 2
    elif context['integrity_rid'] < 8192:
        result = dict(state='blocked_low_integrity_context', native_started=False,
                      next_action='Review process-context.json and run native_startup_clean_env.py '
                                  'with the base interpreter from a normal user terminal.')
        code = 2
    else:
        key = 'COMPLUS_LoadFromRemoteSources'
        previous = os.environ.get(key)
        os.environ[key] = '1'
        try:
            result = probe.run(folder/'attempt', startup_seconds=180, cleanup_seconds=15)
            code = 0 if result['state']=='passed' and not result['child_alive'] else 1
        finally:
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
    (folder/'result.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Evidence: '+str(folder), flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    label = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    parser.add_argument('--output-dir', type=Path, default=ROOT/
                        '.local/evidence/development/BASE-04'/('normal-session-'+label))
    parser.add_argument('--context-only', action='store_true', help='Record context without starting OpticStudio.')
    args = parser.parse_args()
    return run(args.output_dir, context_only=args.context_only)


if __name__ == '__main__':
    sys.exit(main())

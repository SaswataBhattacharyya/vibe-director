"""Opt-in native H1 security acceptance; synthetic sentinels, no account/model.

Run as a host process: an enclosing Codex sandbox masks the daemon directory,
so nested initialization intentionally fails before the tested command starts.
"""
import json
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

from story_builder.tests.harness_probe import configure

# Executed by the actual Codex Linux sandbox, never by the model/MCP gateway.
CHECKS = r'''
import errno,json,os,socket,subprocess,sys
from pathlib import Path
base=Path(sys.argv[1]); checks={}
def denied(name, action):
    try:
        action()
    except OSError as exc:
        checks[name]={'denied':True,'errno':exc.errno}
    else:
        checks[name]={'denied':False}
denied('foreign_read',lambda:(base/'foreign/secret').read_bytes())
denied('foreign_write',lambda:(base/'foreign/secret').write_bytes(b'changed'))
denied('workspace_write',lambda:(base/'workspace/new').write_bytes(b'changed'))
denied('auth_read',lambda:(base/'codex/auth.json').read_bytes())
denied('daemon_directory',lambda:list(Path('/tmp/codex-daemon-'+str(os.getuid())).iterdir()))
checks['allowed_read']=(base/'workspace/public').read_text()=='synthetic public'
def connect_tcp():
    with socket.socket() as s:
        s.settimeout(1);s.connect(('127.0.0.1',int(sys.argv[2])))
denied('host_loopback',connect_tcp)
def connect_external():
    with socket.socket() as s:
        s.settimeout(1);s.connect(('198.51.100.1',9))
denied('external_tcp',connect_external)
def send_udp():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.settimeout(1);s.sendto(b'H1 synthetic',('198.51.100.1',9))
denied('external_udp',send_udp)
def connect_unix():
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(1);s.connect(str(base/'foreign/listener.sock'))
denied('foreign_unix_socket',connect_unix)
child=subprocess.run(['/usr/bin/python3','-c',
    'import os,sys;from pathlib import Path; assert "VIBE_H1_PARENT_SECRET" not in os.environ; Path(sys.argv[1]).read_bytes()',
    str(base/'foreign/secret')],capture_output=True,text=True,timeout=5)
checks['subprocess_inherits_denial']=child.returncode!=0 and ('PermissionError' in child.stderr or 'FileNotFoundError' in child.stderr)
checks['secret_env_absent']='VIBE_H1_PARENT_SECRET' not in os.environ
checks['no_auth_env']=not any(k in os.environ for k in ('OPENAI_API_KEY','CODEX_API_KEY','VIBE_H1_PARENT_SECRET'))
status=Path('/proc/self/status').read_text()
checks['no_new_privs']='NoNewPrivs:\t1' in status
checks['zero_capabilities']='CapEff:\t0000000000000000' in status
checks['seccomp_filter']='Seccomp:\t2' in status
print(json.dumps(checks))
assert all(v.get('denied',False) if isinstance(v,dict) else v for v in checks.values()), checks
'''


def main():
    codex = shutil.which('codex')
    temp = tempfile.TemporaryDirectory(prefix='vibe-h1-os-')
    base = Path(temp.name)
    try:
        configure(base)
        (base / 'foreign').mkdir(mode=0o700)
        foreign = base / 'foreign/secret'
        foreign.write_text('synthetic secret; never owner data')
        (base / 'codex/auth.json').write_text('{"synthetic":"not a credential"}')
        (base / 'workspace/public').write_text('synthetic public')
        # Deliberately absent from the allowlisted environment passed to Codex.
        original = os.environ.get('VIBE_H1_PARENT_SECRET')
        os.environ['VIBE_H1_PARENT_SECRET'] = 'synthetic-inheritance-sentinel'
        try:
            env = {'PATH':'/usr/bin:/bin','HOME':str(base/'home'),
                   'CODEX_HOME':str(base/'codex'),'TMPDIR':str(base/'tmp'),'LANG':'C.UTF-8'}
            with socket.socket() as tcp, socket.socket(socket.AF_UNIX) as unix:
                tcp.bind(('127.0.0.1',0));tcp.listen()
                unix.bind(str(base/'foreign/listener.sock'));unix.listen()
                command = [codex,'sandbox','-P','vibe-h1','-C',str(base/'workspace'),'--',
                           '/usr/bin/python3','-c',CHECKS,str(base),str(tcp.getsockname()[1])]
                result = subprocess.run(command,env=env,cwd=base/'workspace',capture_output=True,text=True,timeout=25)
                print('EXIT', result.returncode)
                print(result.stdout.strip())
                if result.stderr: print(result.stderr[-3000:])
                assert result.returncode == 0, 'Native restrictions not verified'
                assert foreign.read_text() == 'synthetic secret; never owner data'
                assert not (base/'workspace/new').exists()
        finally:
            if original is None: os.environ.pop('VIBE_H1_PARENT_SECRET',None)
            else: os.environ['VIBE_H1_PARENT_SECRET'] = original
    finally:
        temp.cleanup()
        assert not base.exists()
        print('CLEANUP verified')


if __name__ == '__main__':
    main()

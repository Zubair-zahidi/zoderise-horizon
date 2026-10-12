"""Exercise the packaged server through its real websocket, with isolated data."""
import asyncio
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
from websockets.asyncio.client import connect
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'release/Zoderise-Horizon-Hub-8.2-Windows-x64.exe'

async def check_page():
    ws = await connect('ws://127.0.0.1:8519/_stcore/stream', origin='http://127.0.0.1:8519', subprotocols=['streamlit'], max_size=16*1024*1024)
    widget_ids = {}
    async def render(values=None):
        msg = BackMsg()
        msg.rerun_script.query_string = ''
        for key, value in (values or {}).items():
            widget = msg.rerun_script.widget_states.widgets.add()
            widget.id = widget_ids[key]
            if isinstance(value, bool): widget.trigger_value = value
            else: widget.string_value = value
        await ws.send(msg.SerializeToString())
        text = []
        while True:
            raw = await asyncio.wait_for(ws.recv(), 45)
            if raw is None: raise RuntimeError('Websocket closed before page rendered')
            forward = ForwardMsg(); forward.ParseFromString(raw)
            if forward.HasField('delta') and forward.delta.HasField('new_element'):
                element = forward.delta.new_element
                if element.HasField('exception'):
                    raise RuntimeError(str(element.exception))
                for field, content in element.ListFields():
                    if hasattr(content, 'id') and content.id.startswith('$$ID-'):
                        widget_ids[content.id.split('-', 2)[-1]] = content.id
                text.append(str(element))
            if forward.HasField('script_finished') and forward.script_finished == 0: break
        return '\n'.join(text)
    try:
        page = await render()
        assert 'Welcome to Zoderise' in page, 'Sign-in page did not render'
        print('PASS: frozen executable rendered the real sign-in page without exceptions')
        page = await render({'reg_name':'Desktop Test', 'reg_username':'desktop_test', 'reg_email':'desktop@example.com', 'reg_org':'Test school', 'reg_pw1':'Desktop-Check-843!', 'reg_pw2':'Desktop-Check-843!', 'auth_register':True})
        page = await render({'auth_identifier':'desktop@example.com', 'auth_password':'Desktop-Check-843!', 'auth_login':True})
        assert 'YOUR PERSONAL ATELIER' in page, 'New account could not reach the home page'
        print('PASS: first-run registration, sign-in, and dashboard rendered inside the EXE')
        page = await render({'nav_Appearance':True})
        assert 'Make this space yours' in page
        page = await render({'quick_preset_Forest studio':True})
        assert 'Forest' in page
        print('PASS: appearance page and preset workflow rendered inside the EXE')
    finally: await ws.close()

with tempfile.TemporaryDirectory(prefix='zoderise-exe-check-') as temp:
    env = os.environ.copy()
    env['LOCALAPPDATA'] = temp
    env.pop('PYTHONPATH',None)
    env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    env['PYTHONNOUSERSITE'] = '1'
    child = subprocess.Popen([str(EXE),'--desktop-server','8519'], cwd=temp, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(240):
            if child.poll() is not None: raise RuntimeError('Executable stopped: '+str(child.returncode))
            startup_log = Path(temp)/'ZoderiseHorizon/desktop-server.log'
            if startup_log.exists() and 'Traceback (most recent call last)' in startup_log.read_text(encoding='utf-8'):
                raise RuntimeError('Packaged server reported a startup exception')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8519/_stcore/health',timeout=1) as r:
                    if r.status == 200: break
            except Exception: time.sleep(.5)
        else: raise RuntimeError('Server startup timed out')
        with urllib.request.urlopen('http://127.0.0.1:8519/app/static/zoderise-hub.json',timeout=3) as identity:
            assert identity.read().decode('utf-8').strip() == '{"application":"zoderise-horizon","protocol":1}'
        print('PASS: frozen executable serves Zoderise Hub identity')
        asyncio.run(check_page())
        assert (Path(temp)/'ZoderiseHorizon/zoderise.db').exists()
        print('PASS: saved data uses the Windows profile, outside executable extraction')
    except Exception:
        log=Path(temp)/'ZoderiseHorizon/desktop-server.log'
        if log.exists(): print(log.read_text(encoding='utf-8')[-9000:])
        raise
    finally:
        import psutil
        try:
            descendants=psutil.Process(child.pid).children(recursive=True)
            for proc in descendants: proc.terminate()
            psutil.wait_procs(descendants,timeout=5)
        except psutil.NoSuchProcess: pass
        if child.poll() is None: child.terminate()
        child.wait(timeout=10)

    host = subprocess.Popen([str(EXE), '--desktop-server', '8521', '--hub'], cwd=temp, env=env,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(60):
            if host.poll() is not None: raise RuntimeError('Packaged Hub stopped: '+str(host.returncode))
            try:
                with urllib.request.urlopen('http://127.0.0.1:8521/app/static/zoderise-hub.json', timeout=1) as identity:
                    if identity.status == 200:
                        print('PASS: frozen executable hosts a Zoderise Hub with an approved local administrator')
                        break
            except Exception:
                time.sleep(.2)
        else: raise RuntimeError('Packaged Hub startup timed out')
    finally:
        import psutil
        try:
            descendants = psutil.Process(host.pid).children(recursive=True)
            for proc in descendants: proc.terminate()
            psutil.wait_procs(descendants, timeout=5)
        except psutil.NoSuchProcess: pass
        if host.poll() is None: host.terminate()
        host.wait(timeout=10)
        for proc in psutil.process_iter(['exe', 'cmdline']):
            try:
                args = proc.info['cmdline'] or []
                if (Path(proc.info['exe'] or '') == EXE and '--desktop-server' in args
                        and '8521' in args and '--hub' in args):
                    proc.terminate()
                    proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

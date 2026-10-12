"""Zoderise desktop window with an embedded, loopback-only Streamlit server."""
from pathlib import Path
import os
import sys
import socket
import subprocess
import time
import webbrowser
import urllib.request
import shutil
import threading
import json

from zoderise.hub import normalize_hub_url

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ZoderiseHorizon'
HUB_CONFIG = DATA / 'hub-client.json'
HOST_CONFIG = DATA / 'hub-host.json'


def load_hub_url():
    try:
        return normalize_hub_url(json.loads(HUB_CONFIG.read_text(encoding='utf-8')).get('url', ''))
    except Exception:
        return None


def save_hub_url(url):
    DATA.mkdir(parents=True, exist_ok=True)
    if url:
        HUB_CONFIG.write_text(json.dumps({'url': normalize_hub_url(url)}, indent=2), encoding='utf-8')
    elif HUB_CONFIG.exists():
        HUB_CONFIG.unlink()


def host_mode_enabled():
    try:
        return json.loads(HOST_CONFIG.read_text(encoding='utf-8')).get('enabled') is True
    except Exception:
        return False


def save_host_mode(enabled):
    DATA.mkdir(parents=True, exist_ok=True)
    HOST_CONFIG.write_text(json.dumps({'enabled': bool(enabled)}), encoding='utf-8')


def has_host_administrator():
    import sqlite3
    db_path = Path(os.environ['ZODERISE_DB'])
    if not db_path.is_file():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            return bool(conn.execute("SELECT 1 FROM users WHERE role='admin' AND is_active=1 AND approved=1 LIMIT 1").fetchone())
    except sqlite3.Error:
        return False


def hub_is_ready(url):
    try:
        with urllib.request.urlopen(url + '/_stcore/health', timeout=4) as response:
            if response.status != 200:
                return False
        with urllib.request.urlopen(url + '/app/static/zoderise-hub.json', timeout=4) as response:
            identity = json.load(response)
            return response.status == 200 and identity == {'application':'zoderise-horizon','protocol':1}
    except Exception:
        return False


def configure(hub=False):
    DATA.mkdir(parents=True, exist_ok=True)
    data_home = Path(os.environ.get('ZODERISE_DATA_HOME', str(DATA))).resolve()
    data_home.mkdir(parents=True, exist_ok=True)
    os.environ.update(ZODERISE_DB=str(data_home / 'zoderise.db'), ZODERISE_STORAGE=str(data_home / 'storage'),
                      STREAMLIT_GLOBAL_DEVELOPMENT_MODE='false', SERVER_HOST='0.0.0.0' if hub else '127.0.0.1',
                      ZODERISE_ADMIN_EMAIL='', ZODERISE_ADMIN_PASSWORD='',
                      ZODERISE_ENABLE_REGISTRATION='1', ZODERISE_REQUIRE_ADMIN_APPROVAL='1' if hub else '0')
    os.chdir(ROOT)


def server(port, hub=False):
    configure(hub)
    log = (DATA / 'desktop-server.log').open('a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log
    if hub and not has_host_administrator():
        raise RuntimeError('Create an administrator locally before enabling Hub mode.')
    os.environ['SERVER_PORT'] = str(port)
    from streamlit.web import bootstrap
    options = {'server.address':'0.0.0.0' if hub else '127.0.0.1', 'server.port':port, 'server.headless':True,
               'server.fileWatcherType':'none', 'browser.gatherUsageStats':False,
               'server.enableStaticServing':True, 'global.developmentMode':False}
    bootstrap.load_config_options(options)
    bootstrap.run(str(ROOT / 'app.py'), False, [], options)


def main():
    configure()
    if '--desktop-server' in sys.argv:
        server(int(sys.argv[sys.argv.index('--desktop-server')+1]), '--hub' in sys.argv)
        return
    import msvcrt
    import webview
    from webview.menu import Menu, MenuAction
    lock = (DATA / 'desktop.lock').open('a+b')
    lock.seek(0)
    if not lock.read(1):
        lock.write(b'0'); lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk(); root.withdraw()
        messagebox.showinfo('Zoderise is already open','Use the existing Zoderise Horizon application window.')
        root.destroy(); lock.close(); return
    port = None
    for candidate in range(8501,8521):
        with socket.socket() as sock:
            try: sock.bind(('127.0.0.1',candidate)); port=candidate; break
            except OSError: pass
    if port is None:
        lock.close(); raise RuntimeError('Local ports 8501–8520 are busy. Close another local app and retry.')
    local_url=f'http://127.0.0.1:{port}'
    host_mode=host_mode_enabled()
    if host_mode and not has_host_administrator():
        host_mode=False
        save_host_mode(False)
    splash='''<!doctype html><html><meta charset="utf-8"><style>body{margin:0;background:#0b1020;color:#edf1f7;font-family:Segoe UI,sans-serif;display:grid;place-items:center;height:100vh}.card{text-align:center;max-width:560px;padding:30px}small{color:#e8c48b;letter-spacing:.24em}h1{font:48px Georgia,serif}p{color:#b3c1d7;line-height:1.7}.orb{width:70px;height:70px;margin:35px auto;border:1px solid #e8c48b;border-radius:50%;box-shadow:0 0 40px #e8c48b22;animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{transform:scale(.85);opacity:.5}}@media(prefers-reduced-motion:reduce){.orb{animation:none}}</style><div class="card"><small>ZODERISE / HORIZON</small><div class="orb"></div><h1>Your workspace is opening.</h1><p>Preparing your private learning space.<br>The first launch may take a moment.</p></div></html>'''
    window=webview.create_window('Zoderise Horizon',html=splash,width=1400,height=900,min_size=(800,600),background_color='#0b1020',text_select=True)
    stopped=threading.Event()
    model_job=[None]
    model_busy=threading.Lock()
    log=(DATA/'desktop-launcher.log').open('a',encoding='utf-8',buffering=1)
    sys.stdout=sys.stderr=log
    args=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve())]
    def launch_child(hub):
        return subprocess.Popen(args+['--desktop-server',str(port)]+(['--hub'] if hub else []),stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    child=[launch_child(host_mode)]
    current_url=[local_url]
    def prepare_models():
        executable=shutil.which('ollama') or str(Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Ollama/ollama.exe')
        if not Path(executable).is_file():
            if window.create_confirmation_dialog('Install Ollama','Open the official Ollama download page? After installing and opening Ollama, choose AI → Set up models again.'):
                webbrowser.open('https://ollama.com/download/windows')
            return
        if not model_busy.acquire(blocking=False):
            window.create_confirmation_dialog('AI setup','Model setup is already running. Details are in model-setup.log.'); return
        try:
            if not window.create_confirmation_dialog('Set up AI models','Download the two large AI models? This uses several GB of disk space and can take a while. Progress is saved in model-setup.log.'):
                return
            with (DATA/'model-setup.log').open('a',encoding='utf-8') as model_log:
                for name,filename in [('zoderise:latest','Modelfile'),('zoderise-vision:latest','Modelfile-vision')]:
                    if stopped.is_set(): return
                    model_job[0]=subprocess.Popen([executable,'create',name,'-f',str(ROOT/filename)],stdout=model_log,stderr=model_log,creationflags=subprocess.CREATE_NO_WINDOW)
                    if model_job[0].wait()!=0:
                        window.create_confirmation_dialog('AI setup failed','Ensure Ollama is running. See model-setup.log in Workspace → Saved data and logs.'); return
            if not stopped.is_set(): window.create_confirmation_dialog('AI ready','Both models are installed. Use Refresh AI connection in your workspace.')
        finally: model_busy.release()
    def start_workspace():
        saved_hub=load_hub_url()
        if saved_hub:
            if hub_is_ready(saved_hub):
                current_url[0]=saved_hub
                window.load_url(saved_hub)
            else:
                current_url[0]=saved_hub
                window.load_html('<html><body style="background:#0b1020;color:white;font-family:Segoe UI;padding:60px"><h1>Hub unavailable</h1><p>The saved Zoderise Hub could not be reached or identified.</p><p>Check the host and network, then choose Workspace → Reload workspace. To open this computer’s separate local account, choose Workspace → Use this computer.</p></body></html>')
            return
        deadline=time.monotonic()+120
        while not stopped.is_set() and time.monotonic()<deadline:
            if child[0].poll() is not None: break
            try:
                with urllib.request.urlopen(local_url+'/_stcore/health',timeout=.5) as response:
                    if response.status==200:
                        current_url[0]=local_url
                        window.load_url(local_url)
                        return
            except Exception: pass
            stopped.wait(.5)
        if not stopped.is_set():
            window.load_html('<html><body style="background:#0b1020;color:white;font-family:Segoe UI;padding:60px"><h1>Unable to start Zoderise</h1><p>Open Workspace → Saved data and logs, then inspect desktop-server.log. Close this window and try again.</p></body></html>')
    def close_server():
        stopped.set()
        if model_job[0] is not None and model_job[0].poll() is None: model_job[0].terminate()
        if child[0].poll() is None:
            child[0].terminate()
            try: child[0].wait(timeout=5)
            except subprocess.TimeoutExpired: child[0].kill()
    window.events.closed += close_server
    def connect_to_hub():
        import tkinter as tk
        from tkinter import messagebox, simpledialog
        root=tk.Tk(); root.withdraw()
        if host_mode_enabled():
            messagebox.showinfo('Host mode is on','Disable Hub on this computer before connecting it to another Hub.',parent=root)
            root.destroy(); return
        entered=simpledialog.askstring('Connect to Zoderise Hub','Paste the Hub address shown on the host laptop:',initialvalue=load_hub_url() or '',parent=root)
        if entered:
            try:
                remote=normalize_hub_url(entered)
                if not hub_is_ready(remote):
                    raise ValueError('This address did not answer as a Zoderise Hub. Check the address, Wi-Fi/VPN, host app, and firewall.')
                save_hub_url(remote)
                current_url[0]=remote
                window.load_url(remote)
            except ValueError as exc:
                messagebox.showerror('Cannot connect',str(exc),parent=root)
        root.destroy()
    def use_local_workspace():
        save_hub_url(None)
        current_url[0]=local_url
        window.load_url(local_url)
    def switch_host(enabled):
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk(); root.withdraw()
        if enabled and not has_host_administrator():
            messagebox.showinfo('Set up Hub','First create an administrator in the local workspace. Then choose Enable Hub again.',parent=root)
            root.destroy(); return
        if enabled == host_mode_enabled():
            messagebox.showinfo('Hub mode','Hub mode is already '+('on.' if enabled else 'off.'),parent=root)
            root.destroy(); return
        close_server()
        stopped.clear()
        save_host_mode(enabled)
        save_hub_url(None)
        child[0]=launch_child(enabled)
        current_url[0]=local_url
        window.load_html(splash)
        threading.Thread(target=start_workspace,daemon=True).start()
        messagebox.showinfo('Hub mode','Hub is '+('on. Open Admin → Hub access for the QR code. Allow Private-network access in Windows Firewall.' if enabled else 'off. This workspace is local again.'),parent=root)
        root.destroy()
    menus=[Menu('Workspace',[MenuAction('Reload workspace',lambda:window.load_url(current_url[0])),MenuAction('Connect to Hub',connect_to_hub),MenuAction('Use this computer',use_local_workspace),MenuAction('Enable Hub on this computer',lambda:switch_host(True)),MenuAction('Disable Hub',lambda:switch_host(False)),MenuAction('Saved data and logs',lambda:os.startfile(str(DATA))),MenuAction('Exit',window.destroy)]),
           Menu('AI',[MenuAction('Set up models',lambda:threading.Thread(target=prepare_models,daemon=True).start()),MenuAction('Get Ollama',lambda:webbrowser.open('https://ollama.com/download/windows'))])]
    try:
        webview.start(start_workspace,gui='edgechromium',debug=False,private_mode=False,storage_path=str(DATA/'webview'),menu=menus,icon=str(ROOT/'assets/zoderise-icon.ico'))
    except Exception:
        import traceback
        traceback.print_exc(file=log)
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk(); root.withdraw()
        messagebox.showerror('Zoderise desktop startup','The desktop window could not start. Microsoft Edge WebView2 Runtime is required (included on most Windows 10/11 PCs). See desktop-launcher.log in '+str(DATA))
        root.destroy()
        raise
    finally:
        close_server(); lock.close(); log.close()


if __name__=='__main__':
    main()

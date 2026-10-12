from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata
root = Path(SPECPATH)
datas, binaries, hidden = collect_all('streamlit')
for package in ['altair', 'pydeck', 'webview', 'pythonnet', 'clr_loader']:
    d, b, h = collect_all(package)
    datas += d; binaries += b; hidden += h
for name in ['app.py', 'Modelfile', 'Modelfile-vision']:
    datas.append((str(root / name), '.'))
datas += [(str(root / '.streamlit' / 'config.toml'), '.streamlit')]
datas += [(str(root / 'static' / 'zoderise-hub.json'), 'static')]
for pattern in ['*.webp', '*.css', '*.ico', 'zoderise-icon.png']:
    datas += [(str(p), 'assets') for p in (root / 'assets').glob(pattern)]
hidden += [
    'zoderise.ai', 'zoderise.appearance', 'zoderise.backup', 'zoderise.chat_utils',
    'zoderise.classroom', 'zoderise.config', 'zoderise.database', 'zoderise.documents',
    'zoderise.domains', 'zoderise.hub', 'zoderise.identity', 'zoderise.inference_queue',
    'zoderise.local_tools', 'zoderise.security', 'zoderise.ui',
] + ['docx', 'fitz', 'pymupdf', 'PyPDF2', 'pytesseract', 'PIL.Image', 'PIL.ImageOps', 'psutil', 'dotenv', 'qrcode']
a = Analysis(['desktop_launcher.py'], pathex=[str(root)], binaries=binaries, datas=datas,
             hiddenimports=hidden, excludes=['torch','tensorflow','matplotlib','scipy','IPython','pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Zoderise-Horizon-Hub-8.2-Windows-x64',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          icon=str(root / 'assets' / 'zoderise-icon.ico'))

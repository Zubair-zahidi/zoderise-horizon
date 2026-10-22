"""Run portable suites in separate processes to isolate Streamlit and configuration."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITES = ('smoke_test.py', 'regression_test.py', 'ui_test.py', 'horizon_test.py',
          'customization_test.py', 'hub_test.py', 'hub_reliability_test.py')

def main():
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
    failed = []
    for suite in SUITES:
        print(f'Running {suite}', flush=True)
        result = subprocess.run([sys.executable, str(ROOT / 'tests' / suite)], cwd=ROOT, env=env)
        if result.returncode:
            failed.append(suite)
    print(f'{len(SUITES) - len(failed)}/{len(SUITES)} portable suites passed; Windows executable checks are separate.')
    if failed:
        print('Failed: ' + ', '.join(failed))
    return bool(failed)

if __name__ == '__main__':
    raise SystemExit(main())

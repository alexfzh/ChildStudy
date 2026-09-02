"""ChildStudy pre-commit gate check

聚合所有静态检查 + 测试：
- 后端 ruff check
- 后端 pytest（核心套件，跳过慢测试）
- 前端 audit:routes（路由 meta 校验）

用法：
  python scripts/check.py              # 全量
  python scripts/check.py --backend-only
  python scripts/check.py --frontend-only

退出码：0 = 全过；非 0 = 有失败。
"""
import argparse
import os
import subprocess
import sys
import time

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
BACKEND = os.path.join(REPO, 'backend')
FRONTEND = os.path.join(REPO, 'frontend')

ap = argparse.ArgumentParser()
ap.add_argument('--backend-only', action='store_true')
ap.add_argument('--frontend-only', action='store_true')
ap.add_argument('--skip-tests', action='store_true', help='跳过 pytest（仅 lint）')
args = ap.parse_args()

def run(name, cmd, cwd, timeout=300):
    print(f'\n=== {name} ===')
    print(f'$ {" ".join(cmd)}  (cwd: {os.path.relpath(cwd, REPO)})')
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    dt = time.time() - t0
    if r.stdout:
        print(r.stdout[-2000:])
    if r.stderr:
        print('STDERR:', r.stderr[-500:])
    status = '✓' if r.returncode == 0 else '✗'
    print(f'[{status}] {name} ({dt:.1f}s, rc={r.returncode})')
    return r.returncode

results = []

if not args.frontend_only:
    # 后端 ruff
    rc = run('backend:ruff',
             [os.path.join(BACKEND, '.venv', 'Scripts', 'python.exe'),
              '-m', 'ruff', 'check', '.'],
             cwd=BACKEND, timeout=60)
    results.append(('ruff', rc))

    # 后端 pytest
    if not args.skip_tests:
        rc = run('backend:pytest',
                 [os.path.join(BACKEND, '.venv', 'Scripts', 'python.exe'),
                  '-m', 'pytest', '--tb=line', '-q'],
                 cwd=BACKEND, timeout=300)
        results.append(('pytest', rc))

if not args.backend_only:
    # 前端 audit:routes
    rc = run('frontend:audit-routes',
             ['python', os.path.join(FRONTEND, 'scripts', 'audit-routes.py')],
             cwd=FRONTEND, timeout=30)
    results.append(('audit:routes', rc))

# 汇总
print('\n' + '=' * 50)
print('汇总：')
overall = 0
for name, rc in results:
    status = '✓' if rc == 0 else '✗'
    print(f'  [{status}] {name} (rc={rc})')
    if rc != 0:
        overall = rc

print(f'\n总评：{"全过" if overall == 0 else "有失败"}')
sys.exit(overall)
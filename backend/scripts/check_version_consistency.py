"""版本号一致性审计（防四处漂移）

扫描以下位置的版本号并断言全部相等，杜绝 audit 指出的
"system.py / main.py / package.json / VERSION 根文件 不同步"再次发生：

  1. backend/routers/system.py   ->  CURRENT_VERSION = "x.y.z"
  2. backend/main.py             ->  FastAPI  version="x.y.z"
  3. frontend/package.json       ->  "version": "x.y.z"
  4. 根目录 VERSION 文件          ->  x.y.z

用法：
  python scripts/check_version_consistency.py
退出码：0 = 全部一致；1 = 存在不一致（并把不一致明细打印到 stdout）。

注：不强制要求等于某个 git tag —— CI checkout 可能为浅克隆且打 tag 发生在 push 之后，
此处只保证"代码内四处版本口径一致"，tag 对齐由发布流程负责。
"""
import json
import os
import re
import sys

# backend/scripts/check_version_consistency.py -> 仓库根
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))


def read(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def extract(label: str, path: str, pattern: str) -> str | None:
    """用正则抓取版本号，抓不到返回 None。"""
    try:
        text = read(path)
    except FileNotFoundError:
        print(f'  [缺失] {label}: 文件不存在 {os.path.relpath(path, ROOT)}')
        return None
    m = re.search(pattern, text)
    if not m:
        print(f'  [解析失败] {label}: 未匹配到版本号模式 {pattern!r}')
        return None
    return m.group(1).strip()


def main() -> int:
    findings = {}
    findings['system.py CURRENT_VERSION'] = extract(
        'system.py CURRENT_VERSION',
        os.path.join(ROOT, 'backend', 'routers', 'system.py'),
        r'CURRENT_VERSION\s*=\s*"([^"]+)"',
    )
    findings['main.py FastAPI version'] = extract(
        'main.py FastAPI version',
        os.path.join(ROOT, 'backend', 'main.py'),
        r'version\s*=\s*"([^"]+)"',
    )
    pkg_path = os.path.join(ROOT, 'frontend', 'package.json')
    try:
        pkg = json.loads(read(pkg_path))
        findings['package.json version'] = str(pkg.get('version', '')).strip() or None
        if not findings['package.json version']:
            print('  [解析失败] package.json: 缺少 version 字段')
    except (FileNotFoundError, json.JSONDecodeError) as e:
        findings['package.json version'] = None
        print(f'  [缺失/非法] package.json: {e}')

    findings['根 VERSION 文件'] = extract(
        '根 VERSION 文件',
        os.path.join(ROOT, 'VERSION'),
        r'([0-9]+\.[0-9]+\.[0-9]+)',
    )

    print('=== 版本号一致性检查 ===')
    ok = True
    versions = set()
    for label, ver in findings.items():
        state = f'{ver}' if ver else '<None>'
        print(f'  {label:26s} -> {state}')
        if ver:
            versions.add(ver)
        else:
            ok = False

    if ok and len(versions) == 1:
        v = versions.pop()
        print(f'\n✅ 全部一致：{v}')
        return 0

    if len(versions) > 1:
        print(f'\n❌ 不一致：发现 {len(versions)} 个不同版本 {sorted(versions)}')
    else:
        print('\n❌ 存在解析失败/缺失的版本号，无法确认一致')
    return 1


if __name__ == '__main__':
    sys.exit(main())
